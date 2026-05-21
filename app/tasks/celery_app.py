from celery import Celery
from datetime import timedelta
from app.config import settings

celery_app = Celery(
    "rescuebite",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.price_decay",
        "app.tasks.auction_tasks",
        "app.tasks.email_tasks",
    ],
)

celery_app.conf.beat_schedule = {
    # Price decay: every 15 minutes
    "price-decay-every-15min": {
        "task": "app.tasks.price_decay.run_price_decay",
        "schedule": timedelta(minutes=15),
    },
    # Process expired auctions every 5 minutes
    "process-expired-auctions": {
        "task": "app.tasks.auction_tasks.process_expired_auctions",
        "schedule": timedelta(minutes=5),
    },
}

celery_app.conf.timezone = "Asia/Almaty"
