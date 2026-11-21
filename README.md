# Dreame PB20 for Home Assistant

追觅 Air Purifier PB20 的 Home Assistant 自定义集成，支持型号 **`dreame.airp.u2605`**。

## 功能

- 净化器开关：开机、待机。
- 三种模式：AI Purify、Sleep、Custom。
- 自定义风速：1–10 档，对应 HA 的 10%–100%；调整风速会进入自定义模式。
- 温度、湿度、PM2.5、PM10、甲醛、空气质量、滤芯余量。
- 中文和英文配置界面，支持账号重新认证。
- 默认每 30 秒通过追觅云服务更新，可在集成选项中调整为 15–300 秒。

需要 Home Assistant **2026.11.0 或更新版本**，以及已经在追觅 App 中绑定 PB20 的追觅账号。
当前集成使用云端通信，需要联网；没有其他追觅集成的依赖。

## 安装

### HACS

在 HACS 的自定义存储库中添加：

```text
https://github.com/Katzeee/dreame-pb20-integration
```

类别选择 **Integration**，下载 **Dreame PB20**，然后重启 Home Assistant。
这是 HACS 自定义存储库安装方式，不代表已被 HACS 默认目录收录。

### 手动安装

将仓库中的 `custom_components/dreame_pb20` 目录复制到 HA 配置目录的
`custom_components/dreame_pb20`，然后重启 Home Assistant。

## 配置

1. 打开 **设置 → 设备与服务 → 添加集成 → Dreame PB20**。
2. 输入追觅账号和密码。大陆账号选择 **中国大陆**，其他账号选择设备所在地区。
3. 选择 PB20。每台设备建立一个配置条目。

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
待机时空气测量传感器显示为不可用，滤芯余量仍可读取。缺失读数不会被当作 0。
设备没有完整返回操作结果时，HA 会提示失败并重新读取实际状态。

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
└── sensor.py          # 传感器
```

协议定义与实机验证范围见 [docs/protocol.md](docs/protocol.md)。
本项目不包含自动化测试；CI 运行 Ruff 和 HA 的 hassfest 规范检查。

```shell
uvx ruff check .
uvx ruff format --check .
```
