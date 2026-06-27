import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Core settings
    ENVIRONMENT: str = Field("development", validation_alias="ENVIRONMENT")
    SECRET_KEY: str = Field("super_secret_cryptographic_signing_key_change_me_in_prod", validation_alias="SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database settings
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/uabe",
        validation_alias="DATABASE_URL"
    )
    
    # Redis settings
    REDIS_URL: str = Field("redis://localhost:6379/0", validation_alias="REDIS_URL")

    # API keys & integration secrets
    GEMINI_API_KEY: str = Field("", validation_alias="GEMINI_API_KEY")
    GEMINI_API_KEYS: str = Field("", validation_alias="GEMINI_API_KEYS") # Comma-separated list for load balancing
    ANTHROPIC_API_KEY: str = Field("", validation_alias="ANTHROPIC_API_KEY")
    
    # Twilio / WhatsApp settings
    TWILIO_ACCOUNT_SID: str = Field("", validation_alias="TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: str = Field("", validation_alias="TWILIO_AUTH_TOKEN")
    TWILIO_FROM_NUMBER: str = Field("", validation_alias="TWILIO_FROM_NUMBER")
    
    TELEGRAM_BOT_TOKEN: str = Field("", validation_alias="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = Field("", validation_alias="TELEGRAM_CHAT_ID")

    @property
    def gemini_keys_list(self) -> list[str]:
        keys = []
        if self.GEMINI_API_KEYS:
            keys = [k.strip() for k in self.GEMINI_API_KEYS.split(",") if k.strip()]
        if not keys and self.GEMINI_API_KEY:
            keys = [self.GEMINI_API_KEY.strip()]
        return keys
    
    ENCRYPTION_KEY: str = Field(
        "32_bytes_base64_encoded_encryption_key_placeholder=", 
        validation_alias="ENCRYPTION_KEY"
    )

    MILLIONVERIFIER_API_KEY: str = Field("", validation_alias="MILLIONVERIFIER_API_KEY")
    RESEND_API_KEY: str = Field("", validation_alias="RESEND_API_KEY")
    RESEND_WEBHOOK_SIGNING_SECRET: str = Field("", validation_alias="RESEND_WEBHOOK_SIGNING_SECRET")
    STRIPE_API_KEY: str = Field("", validation_alias="STRIPE_API_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field("", validation_alias="STRIPE_WEBHOOK_SECRET")

    # Configuration for loading via .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate global settings
settings = Settings()
