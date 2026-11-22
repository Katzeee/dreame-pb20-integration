# Dreame PB20 for Home Assistant

追觅 Air Purifier PB20 的 Home Assistant 自定义集成，支持型号 **`dreame.airp.u2605`**。

## 功能

- 净化器开关：开机、待机。
- 三种模式：AI Purify、Sleep、Custom。
- 自定义风速：1–10 档，对应 HA 的 10%–100%；已开机且处于自定义模式时只调整风速，其他模式下调整风速会切入自定义模式。
- 温度、湿度、PM2.5、PM10、甲醛、空气质量、追觅 AQ 指数、滤芯余量及剩余天数。
- UVC、童锁、关机后持续监测；更换滤芯后的寿命重置按钮默认禁用，按需启用。
- 中文和英文配置界面，支持账号重新认证。
- 默认每 30 秒通过追觅云服务更新，可在集成选项中调整为 15–300 秒。

需要 Home Assistant **2026.11.0 或更新版本**，以及已经在追觅 App 中绑定 PB20 的追觅账号。
当前集成使用云端通信，需要联网；没有其他追觅集成的依赖。

## 安装

### Marketplace（HACS）

Home Assistant 2026.11 起，HACS 以 Marketplace 的形式内置。在
**设置 → Marketplace** 中连接 GitHub，并添加自定义存储库：

```text
https://github.com/Katzeee/dreame-pb20-integration
```

类别选择 **Integration**，下载 **Dreame PB20**，然后重启 Home Assistant。
这是自定义存储库安装方式，不代表已被默认目录收录。无需安装旧版 HACS。

### 手动安装

将仓库中的 `custom_components/dreame_pb20` 目录复制到 HA 配置目录的
`custom_components/dreame_pb20`，然后重启 Home Assistant。

## 配置

1. 打开 **设置 → 设备与服务 → 添加集成 → Dreame PB20**。
2. 输入追觅账号和密码。大陆账号选择 **中国大陆**，其他账号选择设备所在地区。
3. 选择 PB20。每台设备建立一个配置条目。

独立登录适用于所有用户，没有其他集成的前置要求。若 HA 中已经配置另一个 PB20
或使用 Dreamehome 账号的 Dreame Vacuum 集成，配置流程还会显示可选的“导入已配置的追觅账号”。
导入是一次性复制账号、密码和地区；此后各自认证、刷新令牌和更新密码。
删除来源集成不会影响 PB20，不会共享其他集成的令牌或内部对象。

账号和密码由 HA 配置条目保存在本机；集成不会将它们写入日志。
云端令牌保存在运行内存中。请按 HA 自身的访问控制和备份方式管理配置目录。

## 使用

主要实体是一个 `fan`，同时提供开关、模式选择和风速控制。
例如，使用自己的实体 ID 设置第 3 档：

```yaml
action: fan.set_percentage
target:
  entity_id: fan.air_purifier_pb20
data:
  percentage: 30
```

AI 和睡眠模式的风速由设备管理，HA 的手动风速值显示为未知；调整滑块会切换到自定义模式。
待机且未开启持续监测时，空气测量传感器显示为不可用；开启持续监测后继续显示。
滤芯余量和剩余天数仍可读取。缺失读数不会被当作 0。
设备没有完整返回操作结果时，HA 会提示失败并重新读取实际状态。

滤芯重置按钮只在更换滤芯后使用，默认禁用，需要在实体设置中启用。
时区、城市、设备分享、网络配置和固件升级留在追觅 App 管理；定时、历史曲线及天气
使用 HA 的自动化、历史记录和天气功能。

## 结构

```text
custom_components/dreame_pb20/
├── api/
│   ├── protocol.py     # 云端报文和 PB20 属性地址
│   ├── client.py       # 异步 HTTP、登录、令牌刷新和响应校验
│   └── device.py       # 状态解码、模式和风速语义、设备锁
├── coordinator.py     # 轮询、操作后的状态刷新、HA 错误处理
├── config_flow.py     # 登录、设备选择和选项
├── entity.py          # 共享设备标识
├── fan.py             # 净化器控制
├── sensor.py          # 传感器
├── switch.py          # UVC、童锁和持续监测
└── button.py          # 滤芯维护
```

协议定义与实机验证范围见 [docs/protocol.md](docs/protocol.md)。
本项目不包含自动化测试；CI 运行 Ruff、HA 的 hassfest 和完整 HACS 仓库校验。

```shell
uvx ruff check .
uvx ruff format --check .
```

## 许可证与品牌

代码采用 [MIT 许可证](LICENSE)。
`brand` 目录中的追觅图标取自 [Home Assistant 品牌资源](https://github.com/home-assistant/brands/tree/master/custom_integrations/dreame_vacuum)，
仅用于标识兼容设备，品牌图像和商标权归其各自权利人所有。本集成为社区项目，与追觅官方无隶属关系。
