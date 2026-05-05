import asyncio
from app.tasks.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.services.listing_service import apply_price_decay


@celery_app.task(name="app.tasks.price_decay.run_price_decay", bind=True, max_retries=3)
def run_price_decay(self):
    """
    RESCUEBITE CORE: Celery Beat task — runs every 72h.
    Applies price decay state machine: Active → Discounted → Free → Compost
    """
    async def _run():
        async with AsyncSessionLocal() as session:
            updated = await apply_price_decay(session)
            return updated

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        updated = loop.run_until_complete(_run())
        loop.close()
        print(f"[PriceDecay] Updated {updated} listings")
        return {"updated": updated}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
