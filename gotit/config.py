"""Application configuration via Pydantic Settings.

All settings can be overridden via environment variables with the GOTIT_ prefix.
Nested configs use __ as delimiter, e.g. GOTIT_LLM__PROVIDER=ollama
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class STTConfig(BaseModel):
    engine: str = "whisper_cpp"
    model_path: str = "models/ggml-base.bin"
    language: str = "zh"


class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = ""
    fallback_models: list[str] = []
    api_key: str = ""
    base_url: str = ""
    system_prompt: str = ""
    extra_headers: dict[str, str] = {}


class SearchConfig(BaseModel):
    everything_path: str = "es.exe"
    max_results: int = 20


class AudioConfig(BaseModel):
    device_index: int | None = None
    sample_rate: int = 16000
    channels: int = 1


class UIConfig(BaseModel):
    auto_close_delay: int = 3
    global_hotkey: str = "Ctrl+Shift+G"


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GOTIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    stt: STTConfig = STTConfig()
    llm: LLMConfig = LLMConfig()
    search: SearchConfig = SearchConfig()
    audio: AudioConfig = AudioConfig()
    ui: UIConfig = UIConfig()
    server: ServerConfig = ServerConfig()
    debug: bool = False
