from __future__ import annotations
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


class TTSProvider:
    name = "base"
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
    def available(self) -> bool:
        return False
    def synthesize_to_file(self, text: str, out_path: Path) -> Optional[Path]:
        return None
    def speak(self, text: str) -> bool:
        """Best-effort speak/play. Returns True if handled."""
        return False


class ConsoleTTS(TTSProvider):
    name = "console"
    def available(self) -> bool:
        return True
    def speak(self, text: str) -> bool:
        # no audio, but "handled" for CLI feedback
        return False


class SystemTTS(TTSProvider):
    name = "system"
    def available(self) -> bool:
        return any(shutil.which(c) for c in ("espeak-ng", "espeak", "spd-say", "say", "termux-tts-speak"))

    def speak(self, text: str) -> bool:
        text = (text or "").strip()
        if not text:
            return False
        # try common commands
        for cmd in (['termux-tts-speak', text],
                    ['spd-say', text],
                    ['espeak-ng', '-v', 'ru', text],
                    ['espeak', '-v', 'ru', text],
                    ['say', text]):
            if shutil.which(cmd[0]):
                try:
                    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                    return True
                except Exception:
                    continue
        return False


class SherpaOnnxTTS(TTSProvider):
    name = "sherpa"
    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(cfg)
        self.tts_cfg = cfg.get('tts', {}).get('sherpa', {})
    def available(self) -> bool:
        # requires native libs + model dir configured and present
        model_dir = self.tts_cfg.get('model_dir')
        return bool(model_dir and Path(model_dir).exists())
    def speak(self, text: str) -> bool:
        # Generation to WAV possible if integrated; playback depends on environment.
        # Placeholder: report configured but not auto-played in this minimal runtime.
        return False
    def synthesize_to_file(self, text: str, out_path: Path) -> Optional[Path]:
        # To implement: use sherpa-onnx-node via node bridge or sherpa-onnx python if installed.
        return None


def get_tts_provider(cfg: Dict[str, Any]) -> TTSProvider:
    pref = (cfg.get('tts', {}).get('provider') or 'auto').lower()
    providers = [SystemTTS(cfg), SherpaOnnxTTS(cfg), ConsoleTTS(cfg)]
    if pref != 'auto':
        for p in providers:
            if p.name == pref and p.available():
                return p
    for p in providers:
        if p.available():
            return p
    return ConsoleTTS(cfg)
