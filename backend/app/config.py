"""Configuración por variables de entorno. Nunca hardcodear secretos.

Los valores por defecto apuntan a un Supabase LOCAL (supabase start). Para conectar
un proyecto de desarrollo remoto, setear DATABASE_URL en un `.env` NO versionado
(ver .env.example). Las claves privilegiadas sólo viven en el backend.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Base de datos (Supabase Postgres) ---
    # Default: puerto de Postgres de `supabase start` (local).
    database_url: str = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    app_env: str = "local"

    # --- Supabase Auth (panel autenticado) ---
    # URL del proyecto (no es secreto). Local: `supabase start`. Los JWT se verifican con
    # las claves públicas del JWKS de este proyecto.
    supabase_url: str = "http://127.0.0.1:54321"

    # Empresa por defecto del simulador (Empresa A sintética del seed).
    demo_default_tenant: str = "0000000a-0000-0000-0000-00000000000a"

    # --- LLM (intercambiable). "mock" (reglas) | "ollama" (local, gratis) | "openai" (API). ---
    llm_provider: str = "mock"
    llm_model: str = "gpt-6-luna"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout_s: float = 60.0
    llm_max_output_tokens: int = 500
    # Ollama (local sin key, o Ollama Cloud con key en OLLAMA_API_KEY/LLM_API_KEY)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ollama_api_key: str | None = None

    @property
    def supabase_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_issuer}/.well-known/jwks.json"

    @property
    def llm_is_live(self) -> bool:
        if self.llm_provider == "ollama":
            return True
        return self.llm_provider == "openai" and bool(self.llm_api_key)

    @property
    def llm_mode_label(self) -> str:
        return "live" if self.llm_is_live else "mock"

    @property
    def llm_model_label(self) -> str:
        if self.llm_provider == "ollama":
            return f"{self.ollama_model} (ollama)"
        if self.llm_is_live:
            return self.llm_model
        return "mock-rules-v1"


settings = Settings()
