from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "config.json"


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | os.PathLike | None = None) -> Dict[str, Any]:
    cfg_path = Path(path) if path else DEFAULT_CONFIG
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # local override
    local = ROOT / "config" / "config.local.json"
    if local.exists():
        try:
            with open(local, "r", encoding="utf-8") as f:
                cfg = deep_merge(cfg, json.load(f))
        except Exception:
            pass
    # env overrides
    server = cfg.setdefault("server", {})
    app = cfg.setdefault("app", {})
    if os.getenv("ASSISTANT_HOST"):
        server["host"] = os.getenv("ASSISTANT_HOST")
    if os.getenv("ASSISTANT_PORT"):
        try:
            server["port"] = int(os.getenv("ASSISTANT_PORT", "0"))
        except ValueError:
            pass
    if os.getenv("ASSISTANT_LANG"):
        app["language"] = os.getenv("ASSISTANT_LANG")
    if os.getenv("ASSISTANT_LOG_LEVEL"):
        app["log_level"] = os.getenv("ASSISTANT_LOG_LEVEL")

    ha = cfg.setdefault("home_assistant", {})
    if os.getenv("HASS_URL") or os.getenv("HOME_ASSISTANT_URL"):
        ha["url"] = os.getenv("HASS_URL") or os.getenv("HOME_ASSISTANT_URL")
    if os.getenv("HASS_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN"):
        ha["token"] = os.getenv("HASS_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
    if os.getenv("HOMELAB_SECRETS_FILE"):
        ha["secrets_file"] = os.getenv("HOMELAB_SECRETS_FILE")

    llm = cfg.setdefault("llm", {})
    if os.getenv("LLM_PROVIDER"):
        llm["provider"] = os.getenv("LLM_PROVIDER")
    oc = llm.setdefault("openai_compat", {})
    if os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL"):
        oc["base_url"] = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    if os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL"):
        oc["model"] = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL")
    if os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"):
        oc["api_key"] = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    return cfg


def data_path(cfg: Dict[str, Any], *parts: str) -> Path:
    base = cfg.get("app", {}).get("data_dir", "data")
    p = Path(base)
    if not p.is_absolute():
        p = ROOT / p
    if parts:
        p = p.joinpath(*parts)
    return p
