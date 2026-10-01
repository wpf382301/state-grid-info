# 国家电网辅助信息

为 Home Assistant 的国家电网采集器提供持久历史、阶梯电费估算和费用卡片数据。由 [wpf382301](https://github.com/wpf382301) 在本仓库独立维护。

推荐数据链路：

**[国家电网 App 采集器](https://github.com/stevenjoezhang/hass-state-grid) → 国家电网辅助信息 → [公用事业费用卡片](https://github.com/wpf382301/ha-utility-cost-card)**

采集器负责登录和获取官方电量、账单；本集成按完整户号匹配采集实体，合并历史并估算尚未结算的费用。费用卡片负责显示电费和燃气费。

## HACS 安装

1. 在 HACS 的“自定义存储库”中添加 `https://github.com/wpf382301/state-grid-info`，类别选择“集成”。
2. 下载“国家电网辅助信息”，重启 Home Assistant。
3. 前往“设置 → 设备与服务 → 添加集成 → 国家电网辅助信息”。
4. 数据来源选择“国家电网 App 集成（stevenjoezhang）”，填写完整户号及当地计费规则。

须先安装并登录 `stevenjoezhang/hass-state-grid`。App 登录使用手机号，首次设备验证可能需要短信验证码。

已配置辅助信息的用户无需删除配置项；替换安装后继续使用原有实体、计费规则和历史。迁移 HACS 来源时先移除旧仓库登记，再下载本仓库，避免两个仓库管理同一组件目录。

新旧国网采集器都使用 `state_grid` 域，配置和认证格式不同。迁移采集器须先备份并验证新接口，不能直接沿用旧配置。完成迁移后不要再卸载旧来源，以免删除新采集器共用的目录。

## 数据与费用

- App 实体更新后自动合并数据，另有定时检查；相同数据不会重复写入。
- 正式月账单覆盖估算费用，缺失字段不会覆盖已保存的有效记录。
- 按配置的阶梯和峰谷价格估算未结算费用；缺少所需电量或计费周期基数时显示待同步。
- 年度总额按账期去重，分别提供已结算金额和包含估算的金额。
- 采集暂时不可用时保留历史，并将 `source_available` 设为 `false`。
- `data_until` 表示最新电量日期，`source_updated_at` 表示采集时间，`estimated` 标记估算。

推荐使用公用事业费用卡片 1.4.0 或更高版本。已有辅助实体 ID 保持兼容，无需调整仪表盘和自动化。

## 历史保存

App 数据源使用 Home Assistant 原生 Store，历史保存在：

```text
/config/.storage/state_grid_info.history_<户号>
```

包含日、月、年记录、数据日期和费用来源，不受 Recorder 的保留天数影响。首次启用时会导入旧的 `/config/state_grid_info_<户号>.json`；确认迁移成功后可归档旧文件。备份时请同时保留 `.storage`，历史和登录凭据不应上传 Git。

本集成仍兼容 HassBox 的 `.storage/state_grid.config` 和青龙 MQTT 的 `nodejs/state-grid/<户号>` 数据。兼容数据源继续使用原 JSON 历史，MQTT 在收到消息时立即处理。

## 手动安装

将本仓库的 `custom_components/state_grid_info` 复制到 Home Assistant 的 `custom_components` 目录，重启后添加集成。

## 维护与来源

问题反馈及更新以[本仓库](https://github.com/wpf382301/state-grid-info/issues)为准。历史兼容实现源于 [xiaoshi930/state_grid_info](https://github.com/xiaoshi930/state_grid_info)，保留此处来源致谢；当前 App 适配、历史归档及费用卡片协作在本仓库维护。
