from celery import Celery
from app.config import settings

# Initialize the Celery application bound to our Redis instance
celery_app = Celery(
    "uabe_task_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery operational behavior
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,  # Ensure fair task distribution among agents
    # Discover background task wrappers from the core tasks module
    imports=("app.core.tasks",)
)

if __name__ == "__main__":
    celery_app.start()
