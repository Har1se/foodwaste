from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "rescuebite",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.beat_schedule = {
    # Price decay: every 72 hours (at midnight every 3 days)
    "price-decay-every-72h": {
        "task": "app.tasks.price_decay.run_price_decay",
        "schedule": crontab(hour=0, minute=0, day_of_month="*/3"),
    },
    # Expire listings every hour
    "expire-listings-hourly": {
        "task": "app.tasks.price_decay.run_price_decay",
        "schedule": crontab(minute=0),
    },
}

celery_app.conf.timezone = "Asia/Almaty"
