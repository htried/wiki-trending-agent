from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "wiki-trending-agent"
    database_url: str = "sqlite+pysqlite:///./wiki_trending_agent.db"
    serper_api_key: str = ""
    wikimedia_enterprise_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"


settings = Settings()
