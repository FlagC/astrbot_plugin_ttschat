from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
import astrbot.api.message_components as Comp
from astrbot.api import logger, AstrBotConfig
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from pathlib import Path

from .tts_client import TTSClient


class TtsChatPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config


    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        output_dir = (Path(get_astrbot_data_path()) / "plugin_data" / self.name)
        self.tts_client = TTSClient(self.config, output_dir)

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("chat_test")
    async def tts_chat(self, event: AstrMessageEvent):
        """通过手动发送文本让插件调用tts回复"""
        Message_str = event.message_str
        voice_msg = Message_str.removeprefix("chat_test ")
        wav_path = await self.tts_client.generate_voice(voice_msg)
        chain = [
            Comp.Plain(voice_msg),
            Comp.Record(file=wav_path, url=wav_path),
        ]
        yield event.chain_result(chain)
    
    @filter.llm_tool(name="send_japanese_voice")
    async def send_japanese_voice(
        self,
        event: AstrMessageEvent,
        text: str,
    ) -> str:
        """使用当前配置的角色音色，向当前聊天发送日语语音。

        Args:
            text(string): 需要朗读的日文台词，只包含口语内容，不含动作描写或Markdown，保留台词内的正常标点符号，如果需要模拟角色语句的停顿，采用适当长度的空格,
        """
        text = text.strip()
        if not text:
            return "未发送语音：日文台词为空。"

        try:
            wav_path = await self.tts_client.generate_voice(text)

            await event.send(
                event.chain_result([
                    Comp.Record(file=wav_path, url=wav_path)
                ])
            )
        except Exception:
            logger.exception("日语语音生成或发送失败")
            return "语音生成或发送未能确认成功，请用中文回复，不要声称语音已发送，也不要自动重复调用。"

        return (
            "语音发送接口已成功返回。"
            "接下来仅将本次工具参数 text 中的日文台词完整翻译成中文作为最终回复。"
            "不得新增情节、台词、解释或补充，不得再次调用工具。"
        )



    
    @filter.command("get_config")
    async def show_config(self, event: AstrMessageEvent):
        yield event.plain_result(f"config:\n{self.config}")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
