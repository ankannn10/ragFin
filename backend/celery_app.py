from celery import Celery
from app.config import settings

celery_app = Celery(
    "ragFin",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

# NEW – automatically import any module that contains @celery_app.task
celery_app.autodiscover_tasks(["workers"])

import workers.ingestion
