from app.tasks.auction_tasks import _find_lowest_unique_bid


class _Bid:
    def __init__(self, amount: int, bidder_id: int = 1):
        self.amount = amount
        self.bidder_id = bidder_id


# ── _find_lowest_unique_bid unit tests ───────────────────────────────────────

def test_find_lowest_unique_bid_normal():
    """All bids unique — lowest wins."""
    bids = [_Bid(300), _Bid(100), _Bid(200)]
    result = _find_lowest_unique_bid(bids)
    assert result is not None
    assert result.amount == 100


def test_find_lowest_unique_bid_with_duplicates():
    """Duplicate bids are excluded; lowest unique wins."""
    bids = [_Bid(100), _Bid(100), _Bid(200), _Bid(300)]
    result = _find_lowest_unique_bid(bids)
    assert result is not None
    assert result.amount == 200


def test_find_lowest_unique_bid_all_duplicates():
    """All bids are duplicates — no winner."""
    bids = [_Bid(100), _Bid(100), _Bid(200), _Bid(200)]
    result = _find_lowest_unique_bid(bids)
    assert result is None


def test_find_lowest_unique_bid_empty():
    """No bids — no winner."""
    result = _find_lowest_unique_bid([])
    assert result is None


def test_find_lowest_unique_bid_single_bid():
    """Single bid is always unique — wins."""
    bids = [_Bid(500, bidder_id=7)]
    result = _find_lowest_unique_bid(bids)
    assert result is not None
    assert result.amount == 500
    assert result.bidder_id == 7


def test_find_lowest_unique_bid_one_unique_among_duplicates():
    """Only one unique bid among many duplicates."""
    bids = [_Bid(50), _Bid(50), _Bid(75), _Bid(75), _Bid(99)]
    result = _find_lowest_unique_bid(bids)
    assert result is not None
    assert result.amount == 99


# ── Celery task smoke tests ───────────────────────────────────────────────────

def test_run_price_decay_smoke(monkeypatch):
    """run_price_decay executes apply_price_decay and returns the count."""
    from app.tasks import price_decay as pd_module

    calls = []

    async def fake_apply_price_decay(session):
        calls.append(True)
        return 3

    monkeypatch.setattr(pd_module, "apply_price_decay", fake_apply_price_decay)

    result = pd_module.run_price_decay.apply()
    assert result.result == {"updated": 3}
    assert calls


def test_run_price_decay_error_path(monkeypatch):
    """run_price_decay propagates exceptions (triggers retry logic)."""
    from app.tasks import price_decay as pd_module
    async def broken_apply(_):
        raise RuntimeError("DB unavailable")

    monkeypatch.setattr(pd_module, "apply_price_decay", broken_apply)

    result = pd_module.run_price_decay.apply(throw=False)
    assert result.failed()
