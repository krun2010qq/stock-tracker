from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Stock Tracker"
    app_url: str = "http://49.51.195.205"
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    access_token_expire_minutes: int = 60 * 24 * 7

    database_url: str = "postgresql+psycopg2://stocktracker:stocktracker@127.0.0.1:5432/stocktracker"


settings = Settings()
