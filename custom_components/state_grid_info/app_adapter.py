"""Pure App history mapping and conservative billing estimates."""
from calendar import monthrange
from copy import deepcopy
from datetime import date, timedelta
from math import isfinite

BANDS = {'tip': 'TPq', 'peak': 'PPq', 'flat': 'NPq', 'valley': 'VPq'}


def number(value):
    try:
        parsed = float(value)
        return parsed if isfinite(parsed) else None
    except (ValueError, TypeError):
        return None


def month_end(month):
    year, mon = map(int, month.split('-'))
    return date(year, mon, monthrange(year, mon)[1]).isoformat()


def bill_bounds(row):
    return row.get('start_date') or row['month']+'-01', row.get('end_date') or month_end(row['month'])


def usage_between(start, end, days, months):
    """Sum an inclusive interval, using whole bills or complete daily coverage."""
    cursor, last = date.fromisoformat(start), date.fromisoformat(end)
    total = 0.0
    while cursor <= last:
        key = cursor.isoformat()
        bill = next((m for m in months.values()
            if m.get('cost_source') in ('official', 'historical')
            and bill_bounds(m)[0] == key and bill_bounds(m)[1] <= end
            and number(m.get('monthEleNum')) is not None), None)
        if bill:
            total += bill['monthEleNum']
            cursor = date.fromisoformat(bill_bounds(bill)[1]) + timedelta(days=1)
            continue
        value = number(days.get(key, {}).get('dayEleNum'))
        if value is None:
            return None
        total += value
        cursor += timedelta(days=1)
    return round(total, 6)


def estimate_day(row, days, months, config):
    usage = number(row.get('dayEleNum'))
    if usage is None or usage < 0:
        return None
    if usage == 0:
        return 0.0
    standard = config.get('billing_standard', '')
    if standard == 'other_average':
        price = number(config.get('average_price'))
        return round(usage * price, 2) if price is not None else None
    day = date.fromisoformat(row['day'])
    if standard.startswith('year_ladder'):
        start = config.get('year_ladder_start', '0101')
        try:
            cycle = date(day.year, int(start[:2]), int(start[2:]))
            if day < cycle:
                cycle = cycle.replace(year=cycle.year-1)
        except (TypeError, ValueError):
            return None
    elif standard.startswith('month_ladder'):
        cycle = day.replace(day=1)
    else:
        return None
    before = usage_between(cycle.isoformat(), (day-timedelta(days=1)).isoformat(), days, months)
    limits = [number(config.get('ladder_level_1')), number(config.get('ladder_level_2'))]
    if before is None or None in limits or not 0 < limits[0] < limits[1]:
        return None
    # Preserve the configured thresholds; tariff settings remain user-owned.
    portions = [max(0,min(usage,limits[0]-before)),
                max(0,min(before+usage,limits[1])-max(before,limits[0])),
                max(0,before+usage-max(before,limits[1]))]
    if 'fpg' in standard:
        amounts = {band:number(row.get('day'+suffix)) for band,suffix in BANDS.items()}
        if any(v is None for v in amounts.values()) or abs(sum(amounts.values())-usage)>0.05:
            return None
    else:
        amounts = {'flat':usage}
    cost = 0.0
    for tier, portion in enumerate(portions, 1):
        if not portion:
            continue
        for band, amount in amounts.items():
            key = f'ladder_price_{tier}_price_{band}' if 'fpg' in standard else f'ladder_price_{tier}'
            if standard == 'month_ladder_fpg_variable' and band == 'valley':
                key = f'month_{day.month:02d}_ladder_{tier}_valley'
            price = number(config.get(key))
            if price is None and amount:
                return None
            cost += amount * (price or 0) * portion / usage
    return round(cost, 2)


def _sum(rows, key):
    values = [number(row.get(key)) for row in rows]
    return round(sum(values), 2) if values and all(v is not None for v in values) else None


def merge_app_history(previous, snapshot, config):
    """Archive by period; never delete history or convert missing readings to zero."""
    result = deepcopy(previous)
    days = {r['day']:deepcopy(r) for r in previous.get('dayList', [])}
    months = {r['month']:deepcopy(r) for r in previous.get('monthList', [])}
    legacy_month = str(previous.get('date',''))[:7]
    for row in days.values():
        row.setdefault('cost_source','estimated' if number(row.get('dayEleCost')) is not None else 'pending')
        row['estimated'] = row['cost_source'] == 'estimated'
    for row in months.values():
        row.setdefault('cost_source','estimated' if row['month'] == legacy_month else 'historical')
        row['estimated'] = row['cost_source'] == 'estimated'
    for item in snapshot.get('monthly_bill_history', []):
        month = item['month'][:7]
        row = months.setdefault(month, {'month':month})
        for src,dst in [('usage','monthEleNum'),('charge','monthEleCost')]:
            value = number(item.get(src))
            if value is not None:
                row[dst] = value
        if number(item.get('charge')) is not None:
            row.update(cost_source='official',estimated=False)
        row['settled'] = True
        row['complete'] = True
        for key in ('start_date','end_date'):
            if item.get(key): row[key] = item[key]
    touched = set()
    for item in snapshot.get('daily_history', []):
        if number(item.get('usage')) is None:
            continue
        key = item['day']
        row = days.setdefault(key, {'day':key})
        touched.add(key)
        row['dayEleNum'] = number(item['usage'])
        for band,suffix in BANDS.items():
            value = number(item.get(band))
            if value is not None:
                row['day'+suffix] = value
        cost = number(item.get('charge'))
        if cost is not None:
            row.update(dayEleCost=cost,cost_source='official',estimated=False)
    for key in sorted(days):
        row = days[key]
        if row.get('cost_source') == 'official':
            continue
        cost = estimate_day(row,days,months,config)
        # Preserve historical estimates when a limited new window lacks a baseline.
        if cost is not None or key in touched and number(row.get('dayEleCost')) is None:
            row.update(dayEleCost=cost,cost_source='estimated' if cost is not None else 'pending',estimated=cost is not None)
    settled = [r for r in months.values() if r.get('settled')]
    def covered(day, own_month):
        return any(r['month'] != own_month and bill_bounds(r)[0] <= day <= bill_bounds(r)[1] for r in settled)
    for month in sorted({key[:7] for key in days}):
        existing = months.get(month, {})
        rows = [row for key,row in sorted(days.items()) if key.startswith(month) and not covered(key,month)]
        if not rows:
            continue
        if existing.get('settled') or existing.get('cost_source') == 'historical':
            # Keep the settlement total, which can differ from rounded daily totals.
            for suffix in BANDS.values(): existing['month'+suffix] = _sum(rows,'day'+suffix)
            continue
        last = rows[-1]['day']
        expected = {f'{month}-{n:02d}' for n in range(1,int(last[-2:])+1) if not covered(f'{month}-{n:02d}',month)}
        complete = {r['day'] for r in rows} == expected
        cost = _sum(rows,'dayEleCost') if complete else None
        months[month] = {'month':month,'monthEleNum':_sum(rows,'dayEleNum'),'monthEleCost':cost,
            'complete':complete,'data_until':last,'estimated':cost is not None and any(r.get('estimated') for r in rows),
            'cost_source':'pending' if cost is None else 'estimated' if any(r.get('estimated') for r in rows) else 'official',
            **{'month'+suffix:_sum(rows,'day'+suffix) for suffix in BANDS.values()}}
    period = snapshot.get('current_month')
    total = number(snapshot.get('current_month_usage'))
    if period and total is not None and not months.get(period,{}).get('settled'):
        row = months.setdefault(period, {'month':period,'monthEleCost':None,'cost_source':'pending','estimated':False,'complete':False})
        if number(row.get('monthEleNum')) is not None and abs(row['monthEleNum']-total)>0.05:
            row.update(monthEleCost=None,cost_source='pending',estimated=False,complete=False)
        row['monthEleNum'] = total
    years = {r['year']:deepcopy(r) for r in previous.get('yearList',[])}
    for year in {m[:4] for m in months}:
        rows = [r for m,r in months.items() if m.startswith(year)]
        settled_rows = [r for r in rows if r.get('settled') or r.get('cost_source')=='historical']
        years[year] = {'year':year,'yearEleNum':_sum(rows,'monthEleNum'),'yearEleCost':_sum(rows,'monthEleCost'),
            'estimated':any(r.get('estimated') for r in rows),'settled_cost':_sum(settled_rows,'monthEleCost'),
            'settled_usage':_sum(settled_rows,'monthEleNum'),
            **{'year'+suffix:_sum(rows,'month'+suffix) for suffix in BANDS.values()}}
    result.update(dayList=sorted(days.values(),key=lambda r:r['day'],reverse=True),
        monthList=sorted(months.values(),key=lambda r:r['month'],reverse=True),
        yearList=sorted(years.values(),key=lambda r:r['year'],reverse=True),data_source='state_grid_app')
    for key in ('date','balance','balance_date','amount_due','account_type','consumer_name'):
        if snapshot.get(key) is not None: result[key] = snapshot[key]
    result['source_updated_at'] = result.get('date','')
    result['data_until'] = max(days,default='')
    result['source_available'] = True
    if days:
        last = date.fromisoformat(max(days))
        cycle = config.get('year_ladder_start','0101')
        try:
            start = date(last.year,int(cycle[:2]),int(cycle[2:]))
            if last < start: start=start.replace(year=start.year-1)
            result['ladder_usage'] = usage_between(start.isoformat(),last.isoformat(),days,months)
        except (ValueError,TypeError): result['ladder_usage'] = None
    return result
