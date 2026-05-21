from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.dependencies import get_current_user
from app.core.pagination import CursorPage, PaginationMeta, encode_cursor, decode_cursor
from app.database import get_session
from app.models.auction import Auction, AuctionBid, AuctionStatus
from app.models.listing import Listing, ListingStatus
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.auction import AuctionCreate, AuctionResponse, BidCreate, BidResponse

router = APIRouter(prefix="/auctions", tags=["Auctions"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _find_lowest_unique_bid(bids: list):
    """Return the bid with the lowest amount that only one bidder placed."""
    counts = Counter(b.amount for b in bids)
    unique_bids = [b for b in bids if counts[b.amount] == 1]
    if not unique_bids:
        return None
    return min(unique_bids, key=lambda b: b.amount)


def _to_response(auction: Auction, bid_count: int = 0) -> AuctionResponse:
    return AuctionResponse(
        id=auction.id,
        listing_id=auction.listing_id,
        vendor_id=auction.vendor_id,
        start_price=auction.start_price,
        reserve_price=auction.reserve_price,
        ends_at=auction.ends_at,
        status=auction.status,
        winner_user_id=auction.winner_user_id,
        winning_bid_amount=auction.winning_bid_amount,
        bid_count=bid_count,
        created_at=auction.created_at,
        updated_at=auction.updated_at,
    )


@router.post("", response_model=AuctionResponse, status_code=201)
async def create_auction(
    data: AuctionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a reverse auction for a listing (lowest unique bid wins)."""
    listing_r = await session.execute(select(Listing).where(Listing.id == data.listing_id))
    listing = listing_r.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.status not in (ListingStatus.ACTIVE, ListingStatus.DISCOUNTED, ListingStatus.FREE):
        raise HTTPException(status_code=409, detail="Listing must be active to auction")
    if data.reserve_price > data.start_price:
        raise HTTPException(status_code=422, detail="reserve_price must be <= start_price")
    if data.ends_at <= _utcnow():
        raise HTTPException(status_code=422, detail="ends_at must be in the future")

    vendor_r = await session.execute(select(Vendor).where(Vendor.user_id == current_user.id))
    vendor = vendor_r.scalars().first()
    if not vendor and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Vendor account required")
    if vendor and listing.vendor_id != vendor.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your listing")

    auction = Auction(
        listing_id=data.listing_id,
        vendor_id=vendor.id if vendor else listing.vendor_id,
        start_price=data.start_price,
        reserve_price=data.reserve_price,
        ends_at=data.ends_at,
        status=AuctionStatus.ACTIVE,
    )
    session.add(auction)
    await session.commit()
    await session.refresh(auction)
    return _to_response(auction, 0)


@router.get("", response_model=CursorPage[AuctionResponse])
async def list_auctions(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = True,
    session: AsyncSession = Depends(get_session),
):
    """List auctions with cursor-based pagination."""
    cursor_id = None
    if cursor:
        decoded = decode_cursor(cursor)
        cursor_id = decoded.get("id") if decoded else None

    q = select(Auction)
    if active_only:
        q = q.where(Auction.status == AuctionStatus.ACTIVE)
    if cursor_id:
        q = q.where(Auction.id > cursor_id)
    q = q.order_by(Auction.id).limit(limit + 1)

    result = await session.execute(q)
    auctions = list(result.scalars().all())

    next_id = None
    if len(auctions) > limit:
        auctions = auctions[:limit]
        next_id = auctions[-1].id

    if not auctions:
        return CursorPage(data=[], pagination=PaginationMeta(limit=limit, next_cursor=None))

    auction_ids = [a.id for a in auctions]
    counts_result = await session.execute(
        select(AuctionBid.auction_id, func.count(AuctionBid.id).label("cnt"))
        .where(AuctionBid.auction_id.in_(auction_ids))
        .group_by(AuctionBid.auction_id)
    )
    bid_counts: dict[int, int] = {row.auction_id: row.cnt for row in counts_result}

    return CursorPage(
        data=[_to_response(a, bid_counts.get(a.id, 0)) for a in auctions],
        pagination=PaginationMeta(
            limit=limit,
            next_cursor=encode_cursor({"id": next_id}) if next_id else None,
        ),
    )


@router.get("/{auction_id}", response_model=AuctionResponse)
async def get_auction(
    auction_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Auction).where(Auction.id == auction_id))
    auction = result.scalars().first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    bid_r = await session.execute(
        select(func.count(AuctionBid.id)).where(AuctionBid.auction_id == auction_id)
    )
    bid_count = bid_r.scalar() or 0
    return _to_response(auction, bid_count)


@router.post("/{auction_id}/bid", response_model=BidResponse, status_code=201)
async def place_bid(
    auction_id: int,
    data: BidCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Place or update a bid. Lowest unique bid at auction end wins."""
    result = await session.execute(select(Auction).where(Auction.id == auction_id))
    auction = result.scalars().first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    if auction.status != AuctionStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Auction is not active")
    if auction.ends_at <= _utcnow():
        raise HTTPException(status_code=409, detail="Auction has expired")
    if data.amount < auction.reserve_price:
        raise HTTPException(
            status_code=422,
            detail=f"Bid must be at least {auction.reserve_price} KZT (reserve price)",
        )
    if data.amount > auction.start_price:
        raise HTTPException(
            status_code=422,
            detail=f"Bid must not exceed {auction.start_price} KZT (start price)",
        )

    existing_r = await session.execute(
        select(AuctionBid).where(
            AuctionBid.auction_id == auction_id,
            AuctionBid.bidder_id == current_user.id,
        )
    )
    existing_bid = existing_r.scalars().first()
    if existing_bid:
        existing_bid.amount = data.amount
        existing_bid.created_at = _utcnow()
        bid = existing_bid
    else:
        bid = AuctionBid(auction_id=auction_id, bidder_id=current_user.id, amount=data.amount)
        session.add(bid)

    await session.commit()
    await session.refresh(bid)
    return bid


@router.post("/{auction_id}/end", response_model=AuctionResponse)
async def end_auction(
    auction_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Manually end an auction and determine winner (lowest unique bid)."""
    result = await session.execute(select(Auction).where(Auction.id == auction_id))
    auction = result.scalars().first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    if auction.status != AuctionStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Auction is not active")

    # FIX: old code did `if vendor and vendor.user_id != ...` which silently
    # passed when vendor=None, letting ANY authenticated user end any auction.
    # Now we require vendor to exist OR the user to be admin.
    if current_user.role != "admin":
        vendor_r = await session.execute(select(Vendor).where(Vendor.id == auction.vendor_id))
        vendor = vendor_r.scalars().first()
        if not vendor or vendor.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your auction")

    bids_r = await session.execute(select(AuctionBid).where(AuctionBid.auction_id == auction_id))
    bids = bids_r.scalars().all()

    winner_bid = _find_lowest_unique_bid(bids)
    auction.status = AuctionStatus.ENDED
    auction.updated_at = _utcnow()

    if winner_bid:
        auction.winner_user_id = winner_bid.bidder_id
        auction.winning_bid_amount = winner_bid.amount
        winner_r = await session.execute(select(User).where(User.id == winner_bid.bidder_id))
        winner_user = winner_r.scalars().first()
        if winner_user:
            from app.services.email_service import async_send_auction_won_email
            await async_send_auction_won_email(winner_user.email, auction_id, winner_bid.amount)

    await session.commit()
    await session.refresh(auction)
    return _to_response(auction, len(bids))


@router.post("/process-expired", status_code=200)
async def process_expired_auctions(
    current_user: User = Depends(get_current_user),
):
    """Admin endpoint: queue Celery task to process all expired auctions."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    from app.tasks.auction_tasks import process_expired_auctions as celery_task
    celery_task.delay()
    return {"detail": "Processing queued"}
