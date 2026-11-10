from astrbot.api import AstrBotConfig
from astrbot.api import logger

from typing import Dict
from pathlib import Path
from uuid import uuid4
import httpx

class TTSClient:
    def __init__(self, cfg: AstrBotConfig, output_dir: Path):
        self.host = cfg.host
        self.port = cfg.port
        self.tone = cfg.tone

        self.lora_path = Path(cfg.lora_path)
        self.output_dir = Path(output_dir / "output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_tone(self) -> Dict:
        """生成voice的lora参考字典"""
        tone = self.tone + "_lora"
        tone_dir = Path(self.lora_path) / tone
        adapter = str(tone_dir / "small")

        ref_wavs = [
            (tone_dir / "reference" / f"reference_{i:02d}.wav").as_posix()
            for i in range(1, 5)
        ]

        return {
            "lora_adapter": adapter,
            "ref_wavs": ref_wavs,
        }
    
    async def generate_voice(self, input_char: str) -> str:
        """连接到TTS服务器生成wav文件，保存到数据目录并提供文件路径"""
        tts_URL = f"http://{self.host}:{self.port}/v1/audio/speech"
        # logger.info(tts_URL)
        

        payload = {
            "model": "irodori-tts",
            "input": input_char,
            "response_format": "wav",
            "irodori": self._get_tone(),
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(tts_URL, json=payload)
            response.raise_for_status()
            audio_bytes = response.content

        audio_path = self.output_dir / f"{uuid4().hex}.wav"
        audio_path.write_bytes(audio_bytes)

        return str(audio_path)