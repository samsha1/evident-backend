from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Database ──
    DATABASE_URL: str = "postgresql+asyncpg://evident:evident_password@localhost:5432/evident_db"

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth (Google OAuth) ──
    GOOGLE_CLIENT_ID: str = "placeholder-client-id"
    GOOGLE_CLIENT_SECRET: str = "placeholder-client-secret"
    JWT_SECRET_KEY: str = "dev-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 72

    # ── Crawlers ──
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "evident/0.1.0"
    YOUTUBE_API_KEY: str = ""

    # ── Sentiment ──
    SENTIMENT_MODEL_NAME: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    SENTIMENT_FALLBACK_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""

    # ── Rate Limiting ──
    DEFAULT_DAILY_LIMIT: int = 10

    # ── Prefect ──
    PREFECT_API_URL: str = ""

    # ── Server ──
    APP_ENV: str = "development"
    APP_DOMAIN: str = "v0.app.agenco.io"
    CORS_ORIGINS: str = "chrome-extension://*,http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
