# 国家电网辅助信息（优化版）

本项目复刻自 [xiaoshi930/state_grid_info](https://github.com/xiaoshi930/state_grid_info)，保持原有实体 ID、配置项、HassBox 数据源、青龙 MQTT 数据源和电费计算功能兼容。

## 本版本的优化

- 删除原项目额外创建的每 5 分钟刷新任务，避免与协调器定时器重复运行。
- 默认刷新间隔调整为 60 分钟，可在集成“配置”页面设置为 10–1440 分钟。
- 使用 Home Assistant `CoordinatorEntity`，实体不再自行轮询。
- 协调器启用相同数据抑制，余额和属性没有变化时不通知实体写入新状态。
- 持久化数据没有变化时不再重写 JSON 文件，减少磁盘和闪存写入。
- 持久化文件改为临时文件写入后原子替换，降低异常断电造成文件损坏的概率。
- MQTT 回调通过 Home Assistant 事件循环安全地更新实体。
- 保留现有实体 ID，例如 `sensor.state_grid_3750036609763`，替换后无需修改仪表盘和自动化。

## HACS 安装和升级

1. 进入 HACS。
2. 打开右上角菜单，选择“自定义存储库”。
3. 添加 `https://github.com/wpf382301/state_grid_info`，类别选择“集成”。
4. 下载或重新下载“国家电网辅助信息”。
5. 重启 Home Assistant。

如果之前安装的是原仓库，请将 HACS 自定义仓库地址改为本仓库。已有配置和持久化文件会继续使用。

## 手动安装

将 `custom_components/state_grid_info` 复制到 Home Assistant 配置目录下的 `custom_components`，然后重启 Home Assistant。

目录结构：

```text
config/
└── custom_components/
    └── state_grid_info/
        ├── __init__.py
        ├── config_flow.py
        ├── const.py
        ├── manifest.json
        ├── sensor.py
        ├── storage.py
        ├── strings.json
        └── translations/
```

## 数据来源

- **国网 App 集成**：安装并登录 `stevenjoezhang/hass-state-grid`，在辅助信息“配置 → 数据来源”选择“国家电网 App 集成（stevenjoezhang）”，按完整户号绑定。App 登录使用手机号，不使用旧网页版邮箱账号。
- HassBox 生成的 `.storage/state_grid.config`。
- 青龙脚本通过 MQTT 发布的数据，主题格式为 `nodejs/state-grid/<户号>`。

App 数据源使用 Home Assistant 原生 Store，历史文件为 `/config/.storage/state_grid_info.history_<户号>`，保存日、月、年记录、数据日期和费用来源。第一次启用会完整导入 `/config/state_grid_info_<户号>.json`；确认导入后，旧 JSON 可以移出运行目录并归档。旧数据源继续使用原 JSON。

App 实体更新时自动合并；另有定时检查。正式月账单覆盖估算，缺失字段不覆盖已有有效记录。按配置的阶梯、峰谷价格估算未结算日费用；缺少峰谷电量、完整计费周期基数时保留待同步。年度汇总区分 `settled_cost` / `settled_usage` 和包含未结算估算的总额，按账期去重。`estimated` 表示估算；`source_updated_at` 是采集时间，`data_until` 是最新电量日期。采集不可用时保留历史并设置 `source_available: false`。

推荐搭配 `ha-utility-cost-card` 1.4.0。历史不依赖 Recorder 的保留天数，辅助实体的完整数组无需反复写入 Recorder；可让 Recorder 保存新采集器的数值传感器。代码、账单历史和登录凭据分开存放，历史文件及 `.storage` 不应进入 Git。

新旧采集器都使用 `state_grid` 域，配置版本和认证格式不同。不能在 HACS 中直接覆盖旧版本并沿用旧配置；应备份、验证新接口登录和取数，再迁移配置/实体。旧 `state_grid.config` 仅在所有辅助信息已切换且历史导入确认后清理。

## 刷新策略

默认每 60 分钟检查一次 HassBox 数据。即使执行检查，只要余额、日/月/年数据和属性没有变化，就不会生成新的 HA 状态记录，也不会重写持久化文件。

MQTT 数据仍为消息到达时立即更新；相同消息不会重复写入实体状态。

## 配套前端卡片

原作者已将配套卡片迁移至 [xiaoshi930/xiaoshi](https://github.com/xiaoshi930/xiaoshi)。

```yaml
type: custom:xiaoshi-state-grid-info
entities:
  - entity_id: sensor.state_grid_3750036609763
width: 100%
color_num: '#0fccc3'
color_cost: '#804aff'
```
