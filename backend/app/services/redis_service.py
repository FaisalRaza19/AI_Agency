import asyncio
import time
import uuid
from typing import Optional
from contextlib import asynccontextmanager
import redis.asyncio as aioredis
from app.config import settings

class RedisService:
    def __init__(self):
        # Configure the asynchronous redis client pool
        self.redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=5.0
        )
        self.is_offline = False

    async def get_cache(self, key: str) -> Optional[str]:
        """Fetch string value from Redis cache."""
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            print(f"Redis Cache Get Error for key '{key}': {e}")
            return None

    async def set_cache(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Store string value in Redis cache with optional expiration (in seconds)."""
        try:
            return await self.redis_client.set(key, value, ex=expire)
        except Exception as e:
            print(f"Redis Cache Set Error for key '{key}': {e}")
            return False

    async def delete_cache(self, key: str) -> bool:
        """Delete a key from Redis cache."""
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            print(f"Redis Cache Delete Error for key '{key}': {e}")
            return False

    async def acquire_lock(self, lock_name: str, token: str, lock_timeout: float = 30.0) -> bool:
        """
        Natively implements the single-instance Redlock algorithm.
        Acquires a lock by setting a unique token with NX (Not Exists) and PX (Milliseconds TTL).
        """
        try:
            px = int(lock_timeout * 1000)
            return await self.redis_client.set(
                f"lock:{lock_name}",
                token,
                px=px,
                nx=True
            )
        except Exception as e:
            print(f"Redis Lock Acquire Error for '{lock_name}': {e}")
            if "refused" in str(e).lower() or "connect" in str(e).lower() or "timeout" in str(e).lower() or "multiple exceptions" in str(e).lower():
                self.is_offline = True
            return False

    async def release_lock(self, lock_name: str, token: str) -> bool:
        """
        Releases a lock safely by executing a Lua script.
        Checks if the current value matches the token before deleting to prevent accidental release.
        """
        # Lua script ensures atomicity (GET and DELETE)
        release_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        try:
            result = await self.redis_client.eval(
                release_script,
                1,
                f"lock:{lock_name}",
                token
            )
            return result > 0
        except Exception as e:
            print(f"Redis Lock Release Error for '{lock_name}': {e}")
            return False

    @asynccontextmanager
    async def lock(self, lock_name: str, lock_timeout: float = 30.0, acquire_timeout: float = 10.0):
        """
        Async context manager providing a secure distributed lock wrapper (Redlock pattern).
        Yields control once the lock is acquired, and automatically releases it on exit/exception.
        """
        token = str(uuid.uuid4())
        end_time = time.time() + acquire_timeout
        acquired = False

        # Attempt to acquire the lock (blocking/polling loop)
        while time.time() < end_time:
            if self.is_offline:
                break
            if await self.acquire_lock(lock_name, token, lock_timeout):
                acquired = True
                break
            await asyncio.sleep(0.1)  # sleep 100ms before retrying

        if not acquired and not self.is_offline:
            raise TimeoutError(f"Could not acquire lock on '{lock_name}' within {acquire_timeout}s")

        try:
            yield
        finally:
            # Always guarantee release on block exit if acquired
            if acquired and not self.is_offline:
                await self.release_lock(lock_name, token)

# Instantiate global service client
redis_service = RedisService()
