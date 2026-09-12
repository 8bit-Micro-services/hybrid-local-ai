from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    line_channel_secret: str = ""
    line_channel_access_token: str = ""
    allowed_line_user_ids: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4-64k"
    obsidian_vault_path: str = "./data/vault"
    max_message_length: int = 4000
    rate_limit_per_minute: int = 10

    @property
    def allowed_users(self) -> frozenset[str]:
        return frozenset(
            user_id.strip()
            for user_id in self.allowed_line_user_ids.split(",")
            if user_id.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
