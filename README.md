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

- HassBox 生成的 `.storage/state_grid.config`。
- 青龙脚本通过 MQTT 发布的数据，主题格式为 `nodejs/state-grid/<户号>`。

集成自己的合并数据保存在 Home Assistant 配置目录的 `state_grid_info_<户号>.json`。本优化版不会删除原有日、月、年历史数据。

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
