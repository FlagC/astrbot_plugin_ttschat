# TTS 日语语音回复

一个用于 AstrBot 的本地 TTS 适配插件，通过 HTTP 调用宿主机上的 Irodori TTS Server，生成日语音频，并通过 QQ 官方机器人发送语音。支持手动指令以及由大模型调用工具发送语音、随后回复对应中文。

## 功能

- 调用 `/v1/audio/speech`，接收 WAV 音频并保存到插件数据目录。
- 通过 AstrBot 的 `Record` 组件发送语音，QQ 所需的格式转换和上传由平台适配器处理。
- 提供 `send_japanese_voice` 工具，由聊天模型传入日文台词并触发生成。
- 通过配置选择 `saki`、`kotone`、`lilja`、`misuzu` 四种音色，自动拼接 LoRA 和参考音频路径。
- 提供 `/chat_test` 指令，独立测试语音生成和发送。

插件作为 HTTP 客户端运行，不加载模型，不需要在 AstrBot 容器中安装 Torch 或存放模型权重。

## 前置条件

需要同时部署并运行以下服务：

1. [AstrBot](https://github.com/AstrBotDevs/AstrBot)，并配置 QQ 官方机器人。
2. [Irodori-TTS-Server](https://github.com/Aratako/Irodori-TTS-Server)，按其文档准备 [Irodori-TTS](https://github.com/Aratako/Irodori-TTS) 的运行环境、模型及 LoRA。
3. 支持工具调用的聊天模型，并在 AstrBot 中配置对应模型 API。

当前主要使用场景为 **Windows 宿主机运行 TTS Server，Docker 容器运行 AstrBot**。TTS Server 必须保持运行并且能够被容器访问；不要求公网 TTS 地址。

当前通过 QQ 官方机器人测试。其他平台是否可用取决于其 AstrBot 适配器对语音的支持。

## 安装

将插件放到 AstrBot 的 `data/plugins/astrbot_plugin_ttschat/` 目录，随后通过管理面板重载插件或重启 AstrBot。

例如，宿主机的 `E:/AI-Bot/AstrBot/data` 挂载到容器的 `/AstrBot/data` 时，插件应放在：

```text
E:/AI-Bot/AstrBot/data/plugins/astrbot_plugin_ttschat/
```

插件使用 `httpx` 发起异步请求，AstrBot 环境需要安装该依赖。

## Docker 访问宿主机

在插件设置中填写：

```json
{
  "host": "host.docker.internal",
  "port": "8088",
  "tone": "saki",
  "lora_path": "E:/IrodoriTTS"
}
```

TTS Server 需监听 `0.0.0.0:8088`。容器内的 `localhost` 指向容器自身，不能用于访问 Windows 上的 TTS。

如果容器无法解析 `host.docker.internal`，在 AstrBot 的 Compose 服务配置中补充：

```yaml
services:
  astrbot:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

保留原有服务配置，在 Compose 文件所在目录执行 `docker compose up -d astrbot` 应用变更。

可使用以下命令检查连通性：

```powershell
docker exec astrbot python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:8088/health', timeout=10).read().decode())"
```

## 配置与音色文件

| 配置项 | 含义 | 默认值 |
| --- | --- | --- |
| `host` | TTS 主机名或 IP，不含协议和端口 | `host.docker.internal` |
| `port` | TTS HTTP 端口 | `8088` |
| `tone` | 当前音色 | `saki` |
| `lora_path` | TTS Server 所在机器上的角色目录根路径 | `E:/IrodoriTTS` |

在 AstrBot 插件设置中修改并保存，必要时重新加载插件。

当前代码按固定规则生成路径：

```text
<lora_path>/
├── saki_lora/
├── kotone_lora/
├── lilja_lora/
└── misuzu_lora/
    ├── small/                 # Small 模型对应的 LoRA 适配器目录
    └── reference/
        ├── reference_01.wav
        ├── reference_02.wav
        ├── reference_03.wav
        └── reference_04.wav
```

每个角色目录都使用上述 `small` 和 `reference` 结构。当前固定引用前四个 WAV，必须准备齐全；额外文件不会自动加入请求。基础模型应与对应 LoRA 匹配。

这些路径由 **TTS Server** 读取，所以填写宿主机路径即可，不需要把 LoRA 或参考音频挂载到 AstrBot 容器。

## 使用方法

### 手动测试

发送：

```text
/chat_test おはよう！今日は一緒に楽しい一日にしようね。
```

插件使用当前音色生成并发送语音，同时发送输入文本。另有 `/get_config` 指令用于查看当前插件配置。

### 大模型调用

插件注册的工具为：

```text
send_japanese_voice(text: string)
```

`text` 是需要朗读的日文台词。音色由插件配置决定，模型无需传入 LoRA 路径。

在 AstrBot 中确认当前人格允许使用该工具，并使用支持工具调用的模型。可在当前人格的系统提示词中追加：

```text
【回复语言与语音】
每轮先确定完整的回复内容，再将全部台词写为自然、符合人设的日语，
调用 send_japanese_voice。

工具参数 text 必须包含本轮完整台词，不得只提供摘要、开头或节选。
不包含动作描写、Markdown、表情符号或工具说明。

工具成功后，最终中文回复只能是本次 text 的完整中文翻译。
不得继续扩写，也不得增加日文台词中没有的信息。
中日文要求信息一致，不要求字数相同。

每轮最多调用一次。失败或超时后用中文回复，不自动重试。
用户明确要求只发文字时，不调用工具。
```

执行流程为：

```text
QQ 用户消息 → AstrBot 内置 LLM 对话 → 调用 send_japanese_voice
→ 插件请求宿主机 TTS → 保存 WAV → QQ 发送语音
→ 工具结果返回 LLM → 输出对应中文回复
```

调用时机及台词由模型决定，提示词不能保证每轮必定调用，也不能严格保证两种语言的语义完全一致。

## 音频保存及注意事项

- 音频保存在 `data/plugin_data/<插件注册名>/output/`。当前注册名为 `astrbot_plugin_ttschar`，与插件文件夹名称不同；代码使用 `self.name` 定位数据目录。
- 音频使用随机文件名保存，目前没有自动清理机制，可按需清理历史文件，保留正在发送的文件。
- HTTP 请求超时目前为 180 秒。首次请求可能需要加载模型，AstrBot 的工具超时应留出相应余量。
- 当前请求固定使用模型名 `irodori-tts`、WAV 输出及角色目录下的 `small` 适配器。
- 当前没有音色切换指令；音色通过插件配置修改。
- 测试中出现过电脑 QQ 无法播放、手机 QQ 可正常播放同一条长语音的情况，排查时应对比客户端表现，不要仅凭电脑端现象判断生成失败。

## 相关文档

- [AstrBot：LLM 工具开发](https://docs.astrbot.app/dev/star/guides/ai.html)
- [AstrBot：发送消息与 Record](https://docs.astrbot.app/dev/star/guides/send-message.html)
- [Docker Compose：主机名映射](https://docs.docker.com/compose/how-tos/networking/#custom-dns-with-extra_hosts)
