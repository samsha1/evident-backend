from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    KV_URL: str
    TYPESENSE_API_KEY: str
    TYPESENSE_HOST: str
    TYPESENSE_PORT: int = 443
    TYPESENSE_PROTOCOL: str = "https"
    
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""
    
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    YOUTUBE_API_KEY: str = ""
    
    PREFECT_API_URL: str = ""
    PREFECT_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
