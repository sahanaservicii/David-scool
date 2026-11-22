from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional


class STTProvider:
    name = "base"
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
    def available(self) -> bool:
        return False
    def transcribe_file(self, audio_path: Path) -> Optional[str]:
        return None


class BrowserSTT(STTProvider):
    """Client-side Web Speech API marker - actual recognition happens in browser UI."""
    name = "browser"
    def available(self) -> bool:
        return True


class SherpaOnnxSTT(STTProvider):
    name = "sherpa"
    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(cfg)
        self.stt_cfg = cfg.get('stt', {}).get('sherpa', {})
    def available(self) -> bool:
        model_dir = self.stt_cfg.get('model_dir')
        return bool(model_dir and Path(model_dir).exists())
    def transcribe_file(self, audio_path: Path) -> Optional[str]:
        # Integration point: call sherpa-onnx via node/python if model+runtime present.
        return None


def get_stt_provider(cfg: Dict[str, Any]) -> STTProvider:
    pref = (cfg.get('stt', {}).get('provider') or 'auto').lower()
    providers = [SherpaOnnxSTT(cfg), BrowserSTT(cfg)]
    if pref != 'auto':
        for p in providers:
            if p.name == pref and p.available():
                return p
    for p in providers:
        if p.available():
            return p
    return BrowserSTT(cfg)
