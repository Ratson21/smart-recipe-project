from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "smart_recipe_db"
    jwt_secret: str = "change-me"
    jwt_expire_days: int = 7
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    backend_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
