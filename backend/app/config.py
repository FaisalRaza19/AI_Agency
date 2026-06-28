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
            keys = [k.strip() for k in self.GEMINI_API_KEY.split(",") if k.strip()]
        return keys
    
    ENCRYPTION_KEY: str = Field(
        "32_bytes_base64_encoded_encryption_key_placeholder=", 
        validation_alias="ENCRYPTION_KEY"
    )
    CONFIG_ENCRYPTION_KEY: str = Field(
        "32_bytes_base64_encoded_encryption_key_placeholder=", 
        validation_alias="CONFIG_ENCRYPTION_KEY"
    )

    MILLIONVERIFIER_API_KEY: str = Field("", validation_alias="MILLIONVERIFIER_API_KEY")
    RESEND_API_KEY: str = Field("", validation_alias="RESEND_API_KEY")
    RESEND_WEBHOOK_SIGNING_SECRET: str = Field("", validation_alias="RESEND_WEBHOOK_SIGNING_SECRET")
    STRIPE_API_KEY: str = Field("", validation_alias="STRIPE_API_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field("", validation_alias="STRIPE_WEBHOOK_SECRET")
    TAVILY_API_KEY: str = Field("", validation_alias="TAVILY_API_KEY")
    FIRECRAWL_API_KEY: str = Field("", validation_alias="FIRECRAWL_API_KEY")

    # Configuration for loading via .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate global settings
settings = Settings()

# Dynamic Configuration Resolver with Fernet Encryption & Cache-Aside Pattern
from cryptography.fernet import Fernet

class DynamicConfigResolver:
    def __init__(self):
        self._cache = {}
        self._fernet = None

    def _get_fernet(self) -> Fernet:
        if self._fernet is None:
            key = settings.CONFIG_ENCRYPTION_KEY
            try:
                self._fernet = Fernet(key.encode("utf-8"))
            except Exception:
                import base64
                fallback_key = base64.urlsafe_b64encode(b"dynamic_config_key_padding_32b_2")
                self._fernet = Fernet(fallback_key)
        return self._fernet

    def get_cached(self, key: str) -> str:
        return self._cache.get(key)

    def set_cache(self, key: str, value: str):
        self._cache[key] = value

    def clear_cache(self):
        self._cache.clear()

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        return self._get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        try:
            return self._get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except Exception as e:
            print(f"[CONFIG] Decryption error: {e}")
            return ciphertext

config_resolver = DynamicConfigResolver()

async def get_config_value(key: str, default: str = None) -> str:
    """Returns decrypted config value using Cache-Aside database reads."""
    cached = config_resolver.get_cached(key)
    if cached is not None:
        return cached

    # Import locally to prevent circular import locks
    from app.database import async_session_maker
    from app.models import SystemConfig
    from sqlalchemy import select

    async with async_session_maker() as session:
        try:
            result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
            db_config = result.scalar_one_or_none()
            if db_config:
                decrypted = config_resolver.decrypt(db_config.value)
                config_resolver.set_cache(key, decrypted)
                return decrypted
        except Exception as e:
            print(f"[CONFIG] DB read failed for key '{key}': {e}")

    return default

async def set_config_value(key: str, value: str, description: str = None):
    """Encrypts and writes configuration parameter value to database and updates cache."""
    encrypted = config_resolver.encrypt(value)

    from app.database import async_session_maker
    from app.models import SystemConfig
    from sqlalchemy import select

    async with async_session_maker() as session:
        try:
            result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
            db_config = result.scalar_one_or_none()
            if db_config:
                db_config.value = encrypted
                if description:
                    db_config.description = description
            else:
                db_config = SystemConfig(key=key, value=encrypted, description=description)
                session.add(db_config)
            await session.commit()
        except Exception as e:
            print(f"[CONFIG] DB write failed for key '{key}': {e}")
            raise e

    config_resolver.set_cache(key, value)

