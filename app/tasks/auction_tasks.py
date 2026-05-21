import asyncio
from collections import Counter
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@celery_app.task(name="app.tasks.auction_tasks.process_expired_auctions")
def process_expired_auctions():
    """End all auctions whose ends_at has passed and determine winners."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_process())
    finally:
        loop.close()


async def _process():
    from sqlmodel import select
    from app.database import AsyncSessionLocal
    from app.models.auction import Auction, AuctionBid, AuctionStatus

    async with AsyncSessionLocal() as session:
        now = _utcnow()
        result = await session.execute(
            select(Auction).where(
                Auction.status == AuctionStatus.ACTIVE,
                Auction.ends_at <= now,
            )
        )
        auctions = result.scalars().all()

        for auction in auctions:
            bids_r = await session.execute(
                select(AuctionBid).where(AuctionBid.auction_id == auction.id)
            )
            bids = bids_r.scalars().all()

            winner_bid = _find_lowest_unique_bid(bids)

            auction.status = AuctionStatus.ENDED
            auction.updated_at = now

            if winner_bid:
                auction.winner_user_id = winner_bid.bidder_id
                auction.winning_bid_amount = winner_bid.amount

                from app.models.user import User
                ur = await session.execute(
                    select(User).where(User.id == winner_bid.bidder_id)
                )
                winner_user = ur.scalars().first()
                if winner_user:
                    from app.tasks.email_tasks import send_auction_won_email
                    send_auction_won_email.delay(
                        winner_user.email,
                        auction.id,
                        winner_bid.amount,
                    )

        await session.commit()


def _find_lowest_unique_bid(bids: list):
    counts = Counter(b.amount for b in bids)
    unique_bids = [b for b in bids if counts[b.amount] == 1]
    if not unique_bids:
        return None
    return min(unique_bids, key=lambda b: b.amount)
