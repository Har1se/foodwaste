"""
Create demo data for local development.

Run:
    docker compose exec api python seed.py
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlmodel import select

from app.core.security import hash_password
from app.database import AsyncSessionLocal
from app.models.listing import Listing, ListingAllergen, ListingStatus
from app.models.user import User, UserRole
from app.models.vendor import Vendor


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_or_create_user(session, email, password, role, full_name):
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user:
        user.password_hash = hash_password(password)
        user.role = role
        user.full_name = full_name
        user.email_verified = True
        user.is_active = True
        session.add(user)
        await session.flush()
        return user
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        full_name=full_name,
        email_verified=True,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def seed():
    async with AsyncSessionLocal() as session:
        await get_or_create_user(session, "admin@test.kz", "Secure123!", UserRole.ADMIN, "Demo Admin")
        vendor_user = await get_or_create_user(session, "vendor@test.kz", "Secure123!", UserRole.VENDOR, "Green Cafe")
        await get_or_create_user(session, "customer@test.kz", "Secure123!", UserRole.CUSTOMER, "Demo Customer")

        result = await session.execute(select(Vendor).where(Vendor.user_id == vendor_user.id))
        vendor = result.scalars().first()
        if not vendor:
            vendor = Vendor(
                user_id=vendor_user.id,
                business_name="Green Cafe",
                bin_number="123456789012",
                address="Алматы, ул. Абая 1",
                latitude=43.238,
                longitude=76.945,
                is_approved=True,
            )
            session.add(vendor)
            await session.flush()
        else:
            vendor.business_name = "Green Cafe"
            vendor.is_approved = True
            session.add(vendor)
            await session.flush()

        existing = await session.execute(select(Listing).where(Listing.vendor_id == vendor.id))
        for listing in existing.scalars().all():
            allergens_q = await session.execute(
                select(ListingAllergen).where(ListingAllergen.listing_id == listing.id)
            )
            for item in allergens_q.scalars().all():
                await session.delete(item)
            await session.delete(listing)
        await session.flush()

        now = utcnow()
        # Realistic same-day pickup windows for a food marketplace
        # Food must be picked up the same day — not in 365 days!
        def _window(start_hours: float, duration_hours: float):
            """start_hours from now, window lasts duration_hours."""
            return (
                now + timedelta(hours=start_hours),
                now + timedelta(hours=start_hours + duration_hours),
            )

        products = [
            # ── Японская кухня ──────────────────────────────────────────────────
            {
                "title": "Суши-сет с лососем",
                "description": "24 ролла: Филадельфия, Калифорния, Спайси. Приготовлено сегодня утром.",
                "original_price": 6500, "current_price": 3900, "discount_percentage": 40,
                "quantity": 4, "window": _window(0.5, 5),
                "allergens": ["fish", "gluten", "sesame"],
                "photo_url": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?auto=format&fit=crop&w=900&q=80",
            },
            # quantity = реальные порции; window = (start, end) — тот же день
            {"title": "Рамен Тонкоцу",
             "description": "Насыщенный бульон из свиных костей, яйцо пашот, ростки бамбука, нори.",
             "original_price": 4200, "current_price": 2100, "discount_percentage": 50,
             "quantity": 5, "window": _window(0.5, 6),
             "allergens": ["gluten", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?auto=format&fit=crop&w=900&q=80"},
            {"title": "Гёдза на пару (12 шт)",
             "description": "Свинина с капустой, имбирь, чеснок. Соус: соевый с кунжутным маслом.",
             "original_price": 2800, "current_price": 1120, "discount_percentage": 60,
             "quantity": 8, "window": _window(0.5, 5),
             "allergens": ["gluten", "soy"],
             "photo_url": "https://images.unsplash.com/photo-1563245372-f21724e3856d?auto=format&fit=crop&w=900&q=80"},
            # ── Итальянская кухня ────────────────────────────────────────────────
            {"title": "Пицца Маргарита",
             "description": "Томатный соус Сан-Марцано, моцарелла буффало, свежий базилик. 32 см.",
             "original_price": 3800, "current_price": 1900, "discount_percentage": 50,
             "quantity": 3, "window": _window(1, 5),
             "allergens": ["gluten", "dairy"],
             "photo_url": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=900&q=80"},
            {"title": "Паста Карбонара",
             "description": "Спагетти, хрустящая панчетта, пармезан, сливочно-яичный соус.",
             "original_price": 3600, "current_price": 1800, "discount_percentage": 50,
             "quantity": 5, "window": _window(1, 5),
             "allergens": ["gluten", "dairy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1612874742237-6526221588e3?auto=format&fit=crop&w=900&q=80"},
            {"title": "Лазанья Болоньезе",
             "description": "Слои пасты, мясного рагу и бешамель. Порция 400 г, горячая.",
             "original_price": 4000, "current_price": 2000, "discount_percentage": 50,
             "quantity": 4, "window": _window(1, 5),
             "allergens": ["gluten", "dairy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1574894709920-11b28e7367e3?auto=format&fit=crop&w=900&q=80"},
            # ── Казахская кухня ──────────────────────────────────────────────────
            {"title": "Плов по-казахски",
             "description": "Баранина, рис девзира, морковь, нут, изюм, барбарис. Традиционный казан.",
             "original_price": 3200, "current_price": 1920, "discount_percentage": 40,
             "quantity": 6, "window": _window(0.5, 6),
             "allergens": ["none"],
             "photo_url": "https://images.unsplash.com/photo-1596797882870-8c33c55c473b?auto=format&fit=crop&w=900&q=80"},
            {"title": "Манты с говядиной (8 шт)",
             "description": "Паровые, говядина с луком, подаются со сметаной и зеленью.",
             "original_price": 2500, "current_price": 1500, "discount_percentage": 40,
             "quantity": 7, "window": _window(0.5, 5),
             "allergens": ["gluten", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1625220194771-7ebdea0b70b9?auto=format&fit=crop&w=900&q=80"},
            {"title": "Лагман",
             "description": "Тянутая лапша с говядиной и овощами в ароматном бульоне.",
             "original_price": 2900, "current_price": 1740, "discount_percentage": 40,
             "quantity": 5, "window": _window(0.5, 5),
             "allergens": ["gluten"],
             "photo_url": "https://images.unsplash.com/photo-1569050467447-ce54b3bbc37d?auto=format&fit=crop&w=900&q=80"},
            # ── Американская кухня ───────────────────────────────────────────────
            {"title": "Двойной чизбургер",
             "description": "Говяжья котлета 200 г, двойной чеддер, карамелизованный лук, бриошь.",
             "original_price": 4200, "current_price": 2520, "discount_percentage": 40,
             "quantity": 6, "window": _window(1, 5),
             "allergens": ["gluten", "dairy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=80"},
            {"title": "Клубный сэндвич",
             "description": "Тройной сэндвич с курицей, беконом, авокадо и томатом.",
             "original_price": 2800, "current_price": 1400, "discount_percentage": 50,
             "quantity": 8, "window": _window(0.5, 4),
             "allergens": ["gluten", "dairy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=900&q=80"},
            {"title": "Буррито с курицей",
             "description": "Лепёшка, рис, чёрные бобы, гуакамоле, сыр, сальса.",
             "original_price": 3400, "current_price": 1700, "discount_percentage": 50,
             "quantity": 6, "window": _window(1, 5),
             "allergens": ["gluten", "dairy"],
             "photo_url": "https://images.unsplash.com/photo-1561043433-aaf687c4cf04?auto=format&fit=crop&w=900&q=80"},
            # ── Ближневосточная кухня ────────────────────────────────────────────
            {"title": "Шаурма с курицей",
             "description": "Лаваш, сочная курица на гриле, овощи, чесночный соус.",
             "original_price": 2200, "current_price": 1100, "discount_percentage": 50,
             "quantity": 10, "window": _window(0.5, 4),
             "allergens": ["gluten", "dairy"],
             "photo_url": "https://images.unsplash.com/photo-1529006557810-274b9b2fc783?auto=format&fit=crop&w=900&q=80"},
            {"title": "Фалафель-тарелка",
             "description": "6 шариков фалафеля, хумус, питта, салат табуле, тахини.",
             "original_price": 2600, "current_price": 1560, "discount_percentage": 40,
             "quantity": 5, "window": _window(1, 4),
             "allergens": ["gluten", "sesame"],
             "photo_url": "https://images.unsplash.com/photo-1499488112611-3df45cc95ef0?auto=format&fit=crop&w=900&q=80"},
            # ── Здоровое питание ─────────────────────────────────────────────────
            {"title": "Поке с лососем",
             "description": "Рис, лосось, авокадо, манго, огурец, эдамаме, соус понзу.",
             "original_price": 4500, "current_price": 2700, "discount_percentage": 40,
             "quantity": 5, "window": _window(0.5, 5),
             "allergens": ["fish", "soy", "sesame"],
             "photo_url": "https://images.unsplash.com/photo-1546069901-d5bfd2cbfb1f?auto=format&fit=crop&w=900&q=80"},
            {"title": "Боул с нутом",
             "description": "Шпинат, нут, томаты черри, авокадо, кедровые орешки.",
             "original_price": 3000, "current_price": 1800, "discount_percentage": 40,
             "quantity": 6, "window": _window(1, 5),
             "allergens": ["nuts", "sesame"],
             "photo_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80"},
            {"title": "Смузи-пак (4 бутылки)",
             "description": "Манго-банан, ягодный, зелёный, тропический. Охлаждённые.",
             "original_price": 2400, "current_price": 1200, "discount_percentage": 50,
             "quantity": 6, "window": _window(0.5, 6),
             "allergens": ["none"],
             "photo_url": "https://images.unsplash.com/photo-1505252585461-04db1eb84625?auto=format&fit=crop&w=900&q=80"},
            # ── Выпечка и десерты ────────────────────────────────────────────────
            {"title": "Корзинка выпечки",
             "description": "Круассан, синнабон, маффин черника, слойка. Утренняя выпечка.",
             "original_price": 2800, "current_price": 1400, "discount_percentage": 50,
             "quantity": 7, "window": _window(0.5, 4),
             "allergens": ["gluten", "dairy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=900&q=80"},
            {"title": "Шоколадный торт (2 куска)",
             "description": "Тройной шоколад, ганаш, малиновое кули.",
             "original_price": 1800, "current_price": 900, "discount_percentage": 50,
             "quantity": 4, "window": _window(1, 5),
             "allergens": ["gluten", "dairy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=900&q=80"},
            {"title": "Чизкейк Нью-Йорк",
             "description": "Классический нью-йоркский чизкейк, ягодный соус. Порция 180 г.",
             "original_price": 1600, "current_price": 800, "discount_percentage": 50,
             "quantity": 5, "window": _window(1, 5),
             "allergens": ["gluten", "dairy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1508737027454-e6454ef45afd?auto=format&fit=crop&w=900&q=80"},
            {"title": "Панкейки с кленовым сиропом",
             "description": "Стек из 4 пышных панкейков, масло, кленовый сироп, ягоды.",
             "original_price": 2200, "current_price": 1100, "discount_percentage": 50,
             "quantity": 6, "window": _window(0.5, 3),
             "allergens": ["gluten", "dairy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?auto=format&fit=crop&w=900&q=80"},
            {"title": "Пончики ассорти (6 шт)",
             "description": "Глазурованные, с клубникой, шоколадные и с посыпкой.",
             "original_price": 1400, "current_price": 700, "discount_percentage": 50,
             "quantity": 8, "window": _window(0.5, 4),
             "allergens": ["gluten", "dairy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1551024601-bec78aea704b?auto=format&fit=crop&w=900&q=80"},
            # ── Горячие блюда ────────────────────────────────────────────────────
            {"title": "Стейк Рибай 250 г",
             "description": "Мраморная говядина Medium Rare, запечённые овощи-гриль, соус беарнез.",
             "original_price": 8500, "current_price": 5100, "discount_percentage": 40,
             "quantity": 3, "window": _window(1, 5),
             "allergens": ["dairy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=900&q=80"},
            {"title": "Рыба с картошкой-фри",
             "description": "Хрустящий батер, треска, картофель фри, соус тартар.",
             "original_price": 3800, "current_price": 2280, "discount_percentage": 40,
             "quantity": 5, "window": _window(1, 4),
             "allergens": ["fish", "gluten", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=900&q=80"},
            {"title": "Жаркое из курицы",
             "description": "Рис, жареная курица по-азиатски, кунжут, соус терияки.",
             "original_price": 3200, "current_price": 1920, "discount_percentage": 40,
             "quantity": 7, "window": _window(0.5, 5),
             "allergens": ["gluten", "soy", "sesame"],
             "photo_url": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=900&q=80"},
            {"title": "Грибной крем-суп",
             "description": "Белые грибы, трюфельное масло, сливки, гренки.",
             "original_price": 2400, "current_price": 1440, "discount_percentage": 40,
             "quantity": 6, "window": _window(0.5, 4),
             "allergens": ["dairy", "gluten"],
             "photo_url": "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=900&q=80"},
            # ── Ланч-боксы ───────────────────────────────────────────────────────
            {"title": "Ланч-бокс Детокс",
             "description": "Лосось, киноа, брокколи, морковь, авокадо. Чистое питание.",
             "original_price": 5200, "current_price": 3120, "discount_percentage": 40,
             "quantity": 4, "window": _window(0.5, 5),
             "allergens": ["fish"],
             "photo_url": "https://images.unsplash.com/photo-1543353071-10c8ba85a904?auto=format&fit=crop&w=900&q=80"},
            {"title": "Бизнес-ланч",
             "description": "Суп дня + горячее + салат + напиток. Меняется ежедневно.",
             "original_price": 3500, "current_price": 1750, "discount_percentage": 50,
             "quantity": 10, "window": _window(0.5, 4),
             "allergens": ["gluten", "dairy"],
             "photo_url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=900&q=80"},
            {"title": "Веганский бокс",
             "description": "Темпе, фалафель, хумус, табуле, питта. Без животных продуктов.",
             "original_price": 4000, "current_price": 2000, "discount_percentage": 50,
             "quantity": 3, "window": _window(1, 5),
             "allergens": ["gluten", "sesame", "soy"],
             "photo_url": "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=900&q=80"},
            {"title": "Сырная тарелка",
             "description": "5 видов сыра, крекеры, виноград, мёд, грецкие орехи.",
             "original_price": 5500, "current_price": 2750, "discount_percentage": 50,
             "quantity": 3, "window": _window(1, 5),
             "allergens": ["dairy", "gluten", "nuts"],
             "photo_url": "https://images.unsplash.com/photo-1464500422302-6188776dcbf7?auto=format&fit=crop&w=900&q=80"},
            {"title": "Мороженое Джелато (3 шарика)",
             "description": "Фисташка, шоколад, клубника. Свежеприготовленное.",
             "original_price": 1200, "current_price": 600, "discount_percentage": 50,
             "quantity": 8, "window": _window(0.5, 4),
             "allergens": ["dairy", "nuts"],
             "photo_url": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?auto=format&fit=crop&w=900&q=80"},
            # ── Тайская кухня ────────────────────────────────────────────────────
            {"title": "Пад Тай с креветками",
             "description": "Рисовая лапша, тигровые креветки, яйцо, ростки фасоли, арахис, лайм.",
             "original_price": 4800, "current_price": 2400, "discount_percentage": 50,
             "quantity": 5, "window": _window(1, 5),
             "allergens": ["fish", "gluten", "eggs", "nuts"],
             "photo_url": "https://images.unsplash.com/photo-1559314809-0d155014e29e?auto=format&fit=crop&w=900&q=80"},
            {"title": "Зелёное карри с курицей",
             "description": "Кокосовое молоко, зелёная паста карри, баклажаны, рис жасмин.",
             "original_price": 4200, "current_price": 2100, "discount_percentage": 50,
             "quantity": 4, "window": _window(1, 5),
             "allergens": ["none"],
             "photo_url": "https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?auto=format&fit=crop&w=900&q=80"},
            {"title": "Том Ям с грибами",
             "description": "Кисло-острый суп, кокосовые сливки, грибы шиитаке, лемонграсс.",
             "original_price": 3500, "current_price": 1750, "discount_percentage": 50,
             "quantity": 5, "window": _window(0.5, 4),
             "allergens": ["none"],
             "photo_url": "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=900&q=80"},
            # ── Индийская кухня ──────────────────────────────────────────────────
            {"title": "Баттер Чикен с рисом",
             "description": "Нежная курица в томатно-сливочном соусе масала, басмати, нан.",
             "original_price": 4500, "current_price": 2700, "discount_percentage": 40,
             "quantity": 4, "window": _window(1, 5),
             "allergens": ["dairy", "gluten"],
             "photo_url": "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?auto=format&fit=crop&w=900&q=80"},
            {"title": "Самоса ассорти (6 шт)",
             "description": "Хрустящие пирожки с картофелем и горохом, чатни манго и мятный соус.",
             "original_price": 2000, "current_price": 800, "discount_percentage": 60,
             "quantity": 8, "window": _window(0.5, 4),
             "allergens": ["gluten"],
             "photo_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=900&q=80"},
            {"title": "Бирьяни с бараниной",
             "description": "Ароматный рис со специями, нежная баранина, жареный лук, йогурт.",
             "original_price": 5800, "current_price": 2900, "discount_percentage": 50,
             "quantity": 3, "window": _window(1, 5),
             "allergens": ["dairy"],
             "photo_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=900&q=80"},
            # ── Корейская кухня ──────────────────────────────────────────────────
            {"title": "Корейский BBQ Боул",
             "description": "Маринованная говядина пулькоги, рис, кимчи, яйцо, соус гочуджан.",
             "original_price": 4800, "current_price": 2880, "discount_percentage": 40,
             "quantity": 4, "window": _window(1, 5),
             "allergens": ["gluten", "soy", "eggs", "sesame"],
             "photo_url": "https://images.unsplash.com/photo-1590301157890-4810ed352733?auto=format&fit=crop&w=900&q=80"},
            {"title": "Кимчи-Рамен",
             "description": "Острый бульон, свинина, кимчи, рисовые пирожки, варёное яйцо.",
             "original_price": 3800, "current_price": 1900, "discount_percentage": 50,
             "quantity": 5, "window": _window(0.5, 5),
             "allergens": ["gluten", "soy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1583032015879-e5022cb87c3b?auto=format&fit=crop&w=900&q=80"},
            # ── Грузинская кухня ─────────────────────────────────────────────────
            {"title": "Хачапури по-аджарски",
             "description": "Лодочка из теста, сулугуни, сливочное масло, яйцо. Горячее.",
             "original_price": 3200, "current_price": 1600, "discount_percentage": 50,
             "quantity": 5, "window": _window(0.5, 5),
             "allergens": ["gluten", "dairy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1590947132387-155cc02f3212?auto=format&fit=crop&w=900&q=80"},
            {"title": "Хинкали (8 шт)",
             "description": "Сочные грузинские пельмени с говядиной и свининой, бульон внутри.",
             "original_price": 2800, "current_price": 1120, "discount_percentage": 60,
             "quantity": 6, "window": _window(0.5, 4),
             "allergens": ["gluten"],
             "photo_url": "https://images.unsplash.com/photo-1625944525535-b01a9e3df655?auto=format&fit=crop&w=900&q=80"},
            # ── Мексиканская кухня ───────────────────────────────────────────────
            {"title": "Тако-сет (4 шт)",
             "description": "Тортилья, говядина карнитас, гуакамоле, пико де гальо, лайм.",
             "original_price": 3600, "current_price": 1800, "discount_percentage": 50,
             "quantity": 6, "window": _window(1, 5),
             "allergens": ["gluten", "dairy"],
             "photo_url": "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?auto=format&fit=crop&w=900&q=80"},
            {"title": "Нахос с гуакамоле",
             "description": "Чипсы начос, гуакамоле, сальса, сметана, халапеньо, чеддер.",
             "original_price": 2400, "current_price": 960, "discount_percentage": 60,
             "quantity": 7, "window": _window(0.5, 4),
             "allergens": ["gluten", "dairy"],
             "photo_url": "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=900&q=80"},
            # ── Завтраки ─────────────────────────────────────────────────────────
            {"title": "Авокадо-тост с яйцом",
             "description": "Тост brioche, крем-авокадо, яйцо пашот, микрозелень, чили-хлопья.",
             "original_price": 2600, "current_price": 1040, "discount_percentage": 60,
             "quantity": 6, "window": _window(0.5, 3),
             "allergens": ["gluten", "eggs", "dairy"],
             "photo_url": "https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=900&q=80"},
            {"title": "Яйца Бенедикт с лососем",
             "description": "Английский маффин, лосось, яйца пашот, соус голландез.",
             "original_price": 3400, "current_price": 1700, "discount_percentage": 50,
             "quantity": 5, "window": _window(0.5, 3),
             "allergens": ["gluten", "eggs", "fish", "dairy"],
             "photo_url": "https://images.unsplash.com/photo-1608039829572-78524f79c4c7?auto=format&fit=crop&w=900&q=80"},
            {"title": "Гранола с йогуртом",
             "description": "Домашняя гранола, греческий йогурт, мёд, свежие ягоды.",
             "original_price": 1800, "current_price": 720, "discount_percentage": 60,
             "quantity": 8, "window": _window(0.5, 3),
             "allergens": ["dairy", "gluten", "nuts"],
             "photo_url": "https://images.unsplash.com/photo-1511690743698-d9d85f2fbf38?auto=format&fit=crop&w=900&q=80"},
            # ── Напитки ──────────────────────────────────────────────────────────
            {"title": "Кофе-пак (4 стакана)",
             "description": "Латте, капучино, флэт уайт, раф — свежезаваренный арабика.",
             "original_price": 3200, "current_price": 1280, "discount_percentage": 60,
             "quantity": 8, "window": _window(0.5, 5),
             "allergens": ["dairy"],
             "photo_url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=900&q=80"},
            {"title": "Домашний лимонад (1 л)",
             "description": "Клубника-базилик, маракуйя или классический. Без консервантов.",
             "original_price": 1800, "current_price": 900, "discount_percentage": 50,
             "quantity": 7, "window": _window(0.5, 6),
             "allergens": ["none"],
             "photo_url": "https://images.unsplash.com/photo-1523677011781-c91d1bbe2f9e?auto=format&fit=crop&w=900&q=80"},
            # ── Большие скидки — конец дня ────────────────────────────────────────
            {"title": "Пицца Пепперони (целая, 40 см)",
             "description": "Острая пепперони, моцарелла, орегано. Большая пицца, конец дня.",
             "original_price": 5500, "current_price": 1650, "discount_percentage": 70,
             "quantity": 2, "window": _window(0.5, 3),
             "allergens": ["gluten", "dairy"],
             "photo_url": "https://images.unsplash.com/photo-1628840042765-356cda07504e?auto=format&fit=crop&w=900&q=80",
             "status": ListingStatus.DISCOUNTED},
            {"title": "Суши-бокс Делюкс (48 шт)",
             "description": "Большой набор: 8 видов роллов. Готовы, забирать прямо сейчас!",
             "original_price": 12000, "current_price": 3600, "discount_percentage": 70,
             "quantity": 2, "window": _window(0.5, 2),
             "allergens": ["fish", "gluten", "sesame", "soy"],
             "photo_url": "https://images.unsplash.com/photo-1617196034183-421b4040ed20?auto=format&fit=crop&w=900&q=80",
             "status": ListingStatus.DISCOUNTED},
            {"title": "Ассорти десертов (8 шт)",
             "description": "Эклер, макарон, тарталетка, брауни, трюфель. Вечерняя распродажа.",
             "original_price": 4800, "current_price": 1440, "discount_percentage": 70,
             "quantity": 3, "window": _window(0.5, 3),
             "allergens": ["gluten", "dairy", "eggs", "nuts"],
             "photo_url": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=900&q=80",
             "status": ListingStatus.DISCOUNTED},
            # ── Бесплатно — срочно ────────────────────────────────────────────────
            {"title": "Хлеб на закваске (буханка)",
             "description": "Свежий хлеб утренней выпечки — остался. Забирайте бесплатно!",
             "original_price": 1200, "current_price": 0, "discount_percentage": 90,
             "quantity": 2, "window": _window(0, 2),
             "allergens": ["gluten"],
             "photo_url": "https://images.unsplash.com/photo-1586444248902-2f64eddc13df?auto=format&fit=crop&w=900&q=80",
             "status": ListingStatus.FREE},
            {"title": "Фруктовая тарелка",
             "description": "Нарезка: арбуз, дыня, виноград, клубника. Осталась после мероприятия.",
             "original_price": 2000, "current_price": 0, "discount_percentage": 90,
             "quantity": 2, "window": _window(0, 2),
             "allergens": ["none"],
             "photo_url": "https://images.unsplash.com/photo-1490474418585-ba9bad8fd0ea?auto=format&fit=crop&w=900&q=80",
             "status": ListingStatus.FREE},
            {"title": "Печенье домашнее (10 шт)",
             "description": "Овсяное, шоколадное и с изюмом. Испекли слишком много — берите!",
             "original_price": 900, "current_price": 0, "discount_percentage": 90,
             "quantity": 3, "window": _window(0, 2),
             "allergens": ["gluten", "dairy", "eggs"],
             "photo_url": "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?auto=format&fit=crop&w=900&q=80",
             "status": ListingStatus.FREE},
        ]

        # Координаты разных районов Алматы для реалистичного геораспределения
        almaty_coords = [
            (43.238, 76.945), (43.252, 76.933), (43.261, 76.951), (43.244, 76.968),
            (43.229, 76.912), (43.275, 76.944), (43.248, 76.978), (43.233, 76.958),
            (43.265, 76.921), (43.241, 76.934), (43.257, 76.963), (43.270, 76.952),
        ]

        for index, data in enumerate(products):
            allergens = data.pop("allergens")
            status = data.pop("status", ListingStatus.ACTIVE)
            quantity = data.pop("quantity", 5)
            p_start, p_end = data.pop("window")
            lat, lng = almaty_coords[index % len(almaty_coords)]
            listing = Listing(
                vendor_id=vendor.id,
                quantity_total=quantity,
                quantity_available=quantity,
                status=status,
                pickup_window_start=p_start,
                pickup_window_end=p_end,
                days_active=0,
                latitude=lat,
                longitude=lng,
                **data,
            )
            session.add(listing)
            await session.flush()
            for code in allergens:
                session.add(ListingAllergen(listing_id=listing.id, allergen_code=code))

        await session.commit()

    print(f"✓ Seeded {len(products)} listings with realistic quantities and same-day pickup windows")
    print("Accounts: admin@test.kz | vendor@test.kz | customer@test.kz  (password: Secure123!)")


if __name__ == "__main__":
    asyncio.run(seed())
