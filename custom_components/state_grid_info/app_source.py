"""Read the App integration's public entities using full household identity."""
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from .app_adapter import number

KEYS = ('latest_daily_usage','latest_month_usage','current_month_usage',
        'current_year_usage','current_year_charge','account_balance','amount_due')


def app_households(hass):
    return {d.serial_number:d.name for d in dr.async_get(hass).devices.values()
            if d.serial_number and any(domain=='state_grid' for domain,_ in d.identifiers)}


def app_entities(hass, household):
    device_ids = {d.id for d in dr.async_get(hass).devices.values()
                  if d.serial_number == household and any(domain=='state_grid' for domain,_ in d.identifiers)}
    result = {}
    for entity in er.async_get(hass).entities.values():
        if entity.platform != 'state_grid' or entity.device_id not in device_ids or entity.disabled_by:
            continue
        for key in KEYS:
            if entity.unique_id.endswith('_'+key):
                result[key] = entity.entity_id
                break
    return result


def read_app_snapshot(hass, household):
    entities = app_entities(hass, household)
    states = {key:hass.states.get(entity) for key,entity in entities.items()}
    daily = states.get('latest_daily_usage')
    if daily is None or daily.state == 'unavailable':
        return None
    history = daily.attributes.get('daily_history')
    if not isinstance(history,list):
        return None
    updated = dt_util.as_local(daily.last_reported).isoformat()
    snapshot = {'date':updated,'daily_history':history,'current_month':updated[:7]}
    monthly = states.get('latest_month_usage')
    if monthly and monthly.state != 'unavailable':
        snapshot['monthly_bill_history'] = monthly.attributes.get('monthly_bill_history',[])
    for key,dst in [('account_balance','balance'),('amount_due','amount_due'),('current_month_usage','current_month_usage')]:
        state = states.get(key)
        if state and state.state != 'unavailable':
            snapshot[dst] = number(state.state)
    balance = states.get('account_balance')
    if balance and balance.state != 'unavailable':
        snapshot.update({k:balance.attributes.get(k) for k in ('balance_date','account_type')})
    return snapshot
