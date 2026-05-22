"""
Auto-seed demo data on first startup when the DB is empty.
Called from app/main.py lifespan — safe to run multiple times (idempotent).
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import hash_password
from app.models.listing import Listing, ListingAllergen, ListingStatus
from app.models.user import User, UserRole
from app.models.vendor import Vendor


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _get_or_create_user(
    session: AsyncSession, email: str, password: str, role: UserRole, full_name: str
) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user:
        user.email_verified = True
        user.is_active = True
        user.password_hash = hash_password(password)
        user.role = role
        user.full_name = full_name
        session.add(user)
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


PRODUCTS = [
    # ── Суши / Японская ────────────────────────────────────────────────────────
    {
        "title": "Суши-сет «Лосось» 24 шт",
        "description": "Филадельфия, Калифорния, Спайси маки. Свежий лосось, нори, рис. Готово утром.",
        "original_price": 6500, "current_price": 3900, "quantity": 4,
        "allergens": ["fish", "gluten", "sesame"], "category": "sushi",
        "photo_url": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Ролл Дракон",
        "description": "Угорь, авокадо, огурец, икра тобико, соус унаги. 8 кусочков.",
        "original_price": 4800, "current_price": 2400, "quantity": 6,
        "allergens": ["fish", "gluten", "sesame", "soy"], "category": "sushi",
        "photo_url": "https://images.unsplash.com/photo-1617196034183-421b4040ed20?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Рамен Тонкоцу",
        "description": "Бульон 12 ч из свиных костей, яйцо пашот, ростки бамбука, нори, менма.",
        "original_price": 4200, "current_price": 2100, "quantity": 5,
        "allergens": ["gluten", "eggs", "soy"], "category": "sushi",
        "photo_url": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Гёдза на пару (12 шт)",
        "description": "Свинина с капустой, имбирь, чеснок. Соус: соевый с кунжутным маслом.",
        "original_price": 2800, "current_price": 1120, "quantity": 8,
        "allergens": ["gluten", "soy"], "category": "sushi",
        "photo_url": "https://images.unsplash.com/photo-1563245372-f21724e3856d?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.DISCOUNTED,
    },
    {
        "title": "Поке с лососем",
        "description": "Рис, лосось, авокадо, манго, эдамаме, огурец, соус понзу, кунжут.",
        "original_price": 4500, "current_price": 2700, "quantity": 5,
        "allergens": ["fish", "soy", "sesame"], "category": "sushi",
        "photo_url": "https://images.unsplash.com/photo-1546069901-d5bfd2cbfb1f?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Суши-бокс Делюкс (48 шт)",
        "description": "8 видов роллов — готовы прямо сейчас. Забирать до закрытия. Скидка 70%.",
        "original_price": 12000, "current_price": 3600, "quantity": 2,
        "allergens": ["fish", "gluten", "sesame", "soy"], "category": "sushi",
        "photo_url": "https://images.unsplash.com/photo-1611143669185-af224c5e3252?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.DISCOUNTED,
    },
    # ── Горячее ────────────────────────────────────────────────────────────────
    {
        "title": "Стейк Рибай 250 г",
        "description": "Мраморная говядина Medium Rare, запечённые овощи-гриль, соус беарнез.",
        "original_price": 8500, "current_price": 5100, "quantity": 3,
        "allergens": ["dairy", "eggs"], "category": "hot",
        "photo_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Лазанья Болоньезе",
        "description": "Слои пасты, говяжье рагу, бешамель, пармезан. Порция 400 г, горячая.",
        "original_price": 4000, "current_price": 2000, "quantity": 4,
        "allergens": ["gluten", "dairy", "eggs"], "category": "hot",
        "photo_url": "https://images.unsplash.com/photo-1574894709920-11b28e7367e3?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Плов по-казахски",
        "description": "Баранина, рис девзира, морковь, нут, изюм, барбарис. Традиционный казан.",
        "original_price": 3200, "current_price": 1920, "quantity": 6,
        "allergens": ["none"], "category": "hot",
        "photo_url": "https://images.unsplash.com/photo-1596797882870-8c33c55c473b?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Манты с говядиной (8 шт)",
        "description": "Паровые, говядина с луком, подаются со сметаной и зеленью.",
        "original_price": 2500, "current_price": 1500, "quantity": 7,
        "allergens": ["gluten", "eggs"], "category": "hot",
        "photo_url": "https://images.unsplash.com/photo-1625220194771-7ebdea0b70b9?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Лагман по-узбекски",
        "description": "Тянутая лапша, говядина, болгарский перец, томат, пряный бульон.",
        "original_price": 2900, "current_price": 1450, "quantity": 5,
        "allergens": ["gluten"], "category": "hot",
        "photo_url": "https://images.unsplash.com/photo-1569050467447-ce54b3bbc37d?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Жаркое из курицы с рисом",
        "description": "Курица терияки, жасминовый рис, пак-чой, кунжут, перья лука.",
        "original_price": 3200, "current_price": 1280, "quantity": 6,
        "allergens": ["gluten", "soy", "sesame"], "category": "hot",
        "photo_url": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.DISCOUNTED,
    },
    {
        "title": "Рыба с картошкой фри",
        "description": "Треска в пивном кляре, хрустящий фри, соус тартар, лимон.",
        "original_price": 3800, "current_price": 2280, "quantity": 5,
        "allergens": ["fish", "gluten", "eggs"], "category": "hot",
        "photo_url": "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Грибной крем-суп",
        "description": "Белые грибы, трюфельное масло, сливки 33%, гренки из бриоши.",
        "original_price": 2400, "current_price": 1440, "quantity": 8,
        "allergens": ["dairy", "gluten"], "category": "hot",
        "photo_url": "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Хачапури по-аджарски",
        "description": "Лодочка из теста, тянущийся сулугуни, сливочное масло, яйцо — горячее.",
        "original_price": 3200, "current_price": 1600, "quantity": 4,
        "allergens": ["gluten", "dairy", "eggs"], "category": "hot",
        "photo_url": "https://images.unsplash.com/photo-1590947132387-155cc02f3212?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Хинкали (8 шт)",
        "description": "Грузинские пельмени с говядиной и свининой, пряный бульон внутри.",
        "original_price": 2800, "current_price": 1120, "quantity": 6,
        "allergens": ["gluten"], "category": "hot",
        "photo_url": "https://images.unsplash.com/photo-1625944525535-b01a9e3df655?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.DISCOUNTED,
    },
    # ── Бургеры ────────────────────────────────────────────────────────────────
    {
        "title": "Двойной чизбургер",
        "description": "200 г говяжьей котлеты, двойной чеддер, карамелизованный лук, бриошь.",
        "original_price": 4200, "current_price": 2520, "quantity": 5,
        "allergens": ["gluten", "dairy", "eggs"], "category": "burger",
        "photo_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Клубный сэндвич",
        "description": "Тройной: курица-гриль, бекон, авокадо, томат, айоли. Бриошь-тост.",
        "original_price": 2800, "current_price": 1400, "quantity": 4,
        "allergens": ["gluten", "dairy", "eggs"], "category": "burger",
        "photo_url": "https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Буррито с курицей",
        "description": "Тортилья, рис, чёрные бобы, гуакамоле, чеддер, сальса, сметана.",
        "original_price": 3400, "current_price": 1700, "quantity": 5,
        "allergens": ["gluten", "dairy"], "category": "burger",
        "photo_url": "https://images.unsplash.com/photo-1561043433-aaf687c4cf04?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Нахос с гуакамоле",
        "description": "Чипсы начос, гуакамоле, сальса, сметана, халапеньо, расплавленный чеддер.",
        "original_price": 2400, "current_price": 960, "quantity": 7,
        "allergens": ["gluten", "dairy"], "category": "burger",
        "photo_url": "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.DISCOUNTED,
    },
    {
        "title": "Тако-сет (4 шт)",
        "description": "Тортилья, карнитас из говядины, гуакамоле, пико де гальо, кинза, лайм.",
        "original_price": 3600, "current_price": 1800, "quantity": 6,
        "allergens": ["gluten", "dairy"], "category": "burger",
        "photo_url": "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Шаурма с курицей",
        "description": "Лаваш, курица на гриле, овощи, чесночный соус, маринованные огурцы.",
        "original_price": 2200, "current_price": 1100, "quantity": 8,
        "allergens": ["gluten", "dairy"], "category": "burger",
        "photo_url": "https://images.unsplash.com/photo-1529006557810-274b9b2fc783?auto=format&fit=crop&w=900&q=80",
    },
    # ── Азия (Thai / Indian / Korean) ──────────────────────────────────────────
    {
        "title": "Пад Тай с креветками",
        "description": "Рисовая лапша, тигровые креветки, яйцо, ростки фасоли, арахис, лайм.",
        "original_price": 4800, "current_price": 2400, "quantity": 4,
        "allergens": ["fish", "gluten", "eggs", "nuts"], "category": "asian",
        "photo_url": "https://images.unsplash.com/photo-1559314809-0d155014e29e?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Зелёное карри с курицей",
        "description": "Кокосовое молоко, зелёная паста карри, баклажаны, рис жасмин, тайский базилик.",
        "original_price": 4200, "current_price": 2100, "quantity": 5,
        "allergens": ["none"], "category": "asian",
        "photo_url": "https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Том Ям с грибами",
        "description": "Кисло-острый суп на кокосовых сливках, шиитаке, лемонграсс, галангал, лайм.",
        "original_price": 3500, "current_price": 1750, "quantity": 6,
        "allergens": ["none"], "category": "asian",
        "photo_url": "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Баттер Чикен с рисом",
        "description": "Курица в томатно-сливочном соусе масала, басмати, нан, мятный чатни.",
        "original_price": 4500, "current_price": 2250, "quantity": 5,
        "allergens": ["dairy", "gluten"], "category": "asian",
        "photo_url": "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Самоса ассорти (6 шт)",
        "description": "Хрустящие пирожки с картофелем и горохом, чатни манго и мятный соус.",
        "original_price": 2000, "current_price": 800, "quantity": 10,
        "allergens": ["gluten"], "category": "asian",
        "photo_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.DISCOUNTED,
    },
    {
        "title": "Корейский BBQ Боул",
        "description": "Говядина пулькоги, рис, кимчи, маринованные овощи, яйцо, соус гочуджан.",
        "original_price": 4800, "current_price": 2880, "quantity": 4,
        "allergens": ["gluten", "soy", "eggs", "sesame"], "category": "asian",
        "photo_url": "https://images.unsplash.com/photo-1590301157890-4810ed352733?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Бирьяни с бараниной",
        "description": "Ароматный рис с набором специй, нежная баранина, жареный лук, йогурт раита.",
        "original_price": 5800, "current_price": 2900, "quantity": 3,
        "allergens": ["dairy"], "category": "asian",
        "photo_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=900&q=80",
    },
    # ── Выпечка ────────────────────────────────────────────────────────────────
    {
        "title": "Корзинка выпечки",
        "description": "Круассан масляный, синнабон, маффин черника, слойка с заварным кремом.",
        "original_price": 2800, "current_price": 1400, "quantity": 6,
        "allergens": ["gluten", "dairy", "eggs"], "category": "bakery",
        "photo_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Авокадо-тост с яйцом",
        "description": "Тост brioche, крем-авокадо, яйцо пашот, микрозелень, чили-хлопья, лимон.",
        "original_price": 2600, "current_price": 1040, "quantity": 5,
        "allergens": ["gluten", "eggs", "dairy"], "category": "bakery",
        "photo_url": "https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.DISCOUNTED,
    },
    {
        "title": "Яйца Бенедикт с лососем",
        "description": "Английский маффин, копчёный лосось, яйца пашот, голландский соус.",
        "original_price": 3400, "current_price": 1700, "quantity": 4,
        "allergens": ["gluten", "eggs", "fish", "dairy"], "category": "bakery",
        "photo_url": "https://images.unsplash.com/photo-1608039829572-78524f79c4c7?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Панкейки с кленовым сиропом",
        "description": "Стек из 4 пышных панкейков, сливочное масло, кленовый сироп, свежие ягоды.",
        "original_price": 2200, "current_price": 1100, "quantity": 6,
        "allergens": ["gluten", "dairy", "eggs"], "category": "bakery",
        "photo_url": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Пончики ассорти (6 шт)",
        "description": "Глазурованные, шоколадные, с клубничной глазурью, посыпка. Свежие.",
        "original_price": 1400, "current_price": 700, "quantity": 8,
        "allergens": ["gluten", "dairy", "eggs"], "category": "bakery",
        "photo_url": "https://images.unsplash.com/photo-1551024601-bec78aea704b?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Пицца Пепперони (целая)",
        "description": "Острая пепперони, тянущаяся моцарелла, томатный соус, орегано. 40 см.",
        "original_price": 5500, "current_price": 1650, "quantity": 3,
        "allergens": ["gluten", "dairy"], "category": "bakery",
        "photo_url": "https://images.unsplash.com/photo-1628840042765-356cda07504e?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.DISCOUNTED,
    },
    # ── Десерты ────────────────────────────────────────────────────────────────
    {
        "title": "Шоколадный торт (2 куска)",
        "description": "Тройной шоколад, ганаш из 70% какао, малиновое кули.",
        "original_price": 1800, "current_price": 900, "quantity": 5,
        "allergens": ["gluten", "dairy", "eggs"], "category": "dessert",
        "photo_url": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Чизкейк Нью-Йорк",
        "description": "Классический нью-йоркский чизкейк на основе из крекера, ягодный соус.",
        "original_price": 1600, "current_price": 800, "quantity": 6,
        "allergens": ["gluten", "dairy", "eggs"], "category": "dessert",
        "photo_url": "https://images.unsplash.com/photo-1508737027454-e6454ef45afd?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Ассорти десертов (8 шт)",
        "description": "Эклер, макарон, тарталетка с ягодами, брауни, шоколадный трюфель.",
        "original_price": 4800, "current_price": 1440, "quantity": 4,
        "allergens": ["gluten", "dairy", "eggs", "nuts"], "category": "dessert",
        "photo_url": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.DISCOUNTED,
    },
    {
        "title": "Мороженое Джелато (3 шарика)",
        "description": "Фисташка, бельгийский шоколад, клубника. Свежеприготовленное сегодня.",
        "original_price": 1200, "current_price": 600, "quantity": 7,
        "allergens": ["dairy", "nuts"], "category": "dessert",
        "photo_url": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Гранола с йогуртом",
        "description": "Домашняя гранола с орехами, греческий йогурт, мёд, свежие ягоды.",
        "original_price": 1800, "current_price": 720, "quantity": 5,
        "allergens": ["dairy", "gluten", "nuts"], "category": "dessert",
        "photo_url": "https://images.unsplash.com/photo-1511690743698-d9d85f2fbf38?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.DISCOUNTED,
    },
    {
        "title": "Сырная тарелка",
        "description": "5 видов сыра: камамбер, пармезан, чеддер, горгонзола, бри. Виноград, мёд.",
        "original_price": 5500, "current_price": 2750, "quantity": 3,
        "allergens": ["dairy", "gluten", "nuts"], "category": "dessert",
        "photo_url": "https://images.unsplash.com/photo-1464500422302-6188776dcbf7?auto=format&fit=crop&w=900&q=80",
    },
    # ── Боулы / Салаты ─────────────────────────────────────────────────────────
    {
        "title": "Боул с нутом и авокадо",
        "description": "Шпинат, нут, черри, авокадо, кедровые орешки, дрессинг тахини-лимон.",
        "original_price": 3000, "current_price": 1800, "quantity": 5,
        "allergens": ["nuts", "sesame"], "category": "salad",
        "photo_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Фалафель-тарелка",
        "description": "6 шариков фалафеля, хумус, питта, табуле, тахини, маринованные овощи.",
        "original_price": 2600, "current_price": 1300, "quantity": 6,
        "allergens": ["gluten", "sesame"], "category": "salad",
        "photo_url": "https://images.unsplash.com/photo-1499488112611-3df45cc95ef0?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Ланч-бокс Детокс",
        "description": "Лосось 100 г, киноа, брокколи на пару, морковь, авокадо. Без глютена.",
        "original_price": 5200, "current_price": 3120, "quantity": 4,
        "allergens": ["fish"], "category": "salad",
        "photo_url": "https://images.unsplash.com/photo-1543353071-10c8ba85a904?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Веганский бокс",
        "description": "Темпе на гриле, фалафель, хумус, табуле, питта. Полностью растительный.",
        "original_price": 4000, "current_price": 2000, "quantity": 3,
        "allergens": ["gluten", "sesame", "soy"], "category": "salad",
        "photo_url": "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Бизнес-ланч",
        "description": "Суп дня + основное блюдо + салат + напиток. Меню обновляется ежедневно.",
        "original_price": 3500, "current_price": 1750, "quantity": 10,
        "allergens": ["gluten", "dairy"], "category": "salad",
        "photo_url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=900&q=80",
    },
    # ── Напитки ────────────────────────────────────────────────────────────────
    {
        "title": "Кофе-пак (4 стакана)",
        "description": "Латте, капучино, флэт уайт, американо — свежезаваренная арабика 100%.",
        "original_price": 3200, "current_price": 1280, "quantity": 8,
        "allergens": ["dairy"], "category": "drinks",
        "photo_url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.DISCOUNTED,
    },
    {
        "title": "Смузи-пак (4 бутылки)",
        "description": "Манго-банан, малиновый, зелёный (шпинат-яблоко), тропический. Охлаждённые.",
        "original_price": 2400, "current_price": 1200, "quantity": 6,
        "allergens": ["none"], "category": "drinks",
        "photo_url": "https://images.unsplash.com/photo-1505252585461-04db1eb84625?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Домашний лимонад (1 л)",
        "description": "Клубника-базилик, маракуйя или классический лимонный. Без консервантов.",
        "original_price": 1800, "current_price": 900, "quantity": 7,
        "allergens": ["none"], "category": "drinks",
        "photo_url": "https://images.unsplash.com/photo-1523677011781-c91d1bbe2f9e?auto=format&fit=crop&w=900&q=80",
    },
    # ── Бесплатно (FREE) ───────────────────────────────────────────────────────
    {
        "title": "Хлеб на закваске (буханка)",
        "description": "Свежий хлеб утренней выпечки — остался. Забирайте бесплатно, не пропадать!",
        "original_price": 1200, "current_price": 0, "quantity": 2,
        "allergens": ["gluten"], "category": "free",
        "photo_url": "https://images.unsplash.com/photo-1586444248902-2f64eddc13df?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.FREE,
    },
    {
        "title": "Фруктовая нарезка",
        "description": "Арбуз, дыня, виноград, клубника, киви. Осталась после корпоратива.",
        "original_price": 2000, "current_price": 0, "quantity": 2,
        "allergens": ["none"], "category": "free",
        "photo_url": "https://images.unsplash.com/photo-1490474418585-ba9bad8fd0ea?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.FREE,
    },
    {
        "title": "Печенье домашнее (10 шт)",
        "description": "Овсяное, шоколадное с чипсами, изюмное — испекли слишком много. Берите!",
        "original_price": 900, "current_price": 0, "quantity": 3,
        "allergens": ["gluten", "dairy", "eggs"], "category": "free",
        "photo_url": "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?auto=format&fit=crop&w=900&q=80",
        "status": ListingStatus.FREE,
    },
    {
        "title": "Паста Карбонара",
        "description": "Спагетти, панчетта, пармезан, яичный соус. Приготовлено 2 часа назад.",
        "original_price": 3600, "current_price": 1800, "quantity": 5,
        "allergens": ["gluten", "dairy", "eggs"], "category": "hot",
        "photo_url": "https://images.unsplash.com/photo-1612874742237-6526221588e3?auto=format&fit=crop&w=900&q=80",
    },
    {
        "title": "Пицца Маргарита",
        "description": "Томатный соус Сан-Марцано, моцарелла буффало, свежий базилик. 32 см.",
        "original_price": 3800, "current_price": 1900, "quantity": 3,
        "allergens": ["gluten", "dairy"], "category": "bakery",
        "photo_url": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=900&q=80",
    },
]


# Разные районы Алматы для реалистичного геораспределения
_ALMATY_COORDS = [
    (43.238, 76.945), (43.252, 76.933), (43.261, 76.951), (43.244, 76.968),
    (43.229, 76.912), (43.275, 76.944), (43.248, 76.978), (43.233, 76.958),
    (43.265, 76.921), (43.241, 76.934), (43.257, 76.963), (43.270, 76.952),
]


async def auto_seed(session: AsyncSession) -> int:
    """Seed demo users (always) and listings (only if DB is empty). Returns count of new listings."""
    from sqlmodel import func as sqlfunc

    # Always ensure demo accounts exist with correct credentials
    await _get_or_create_user(
        session, "admin@test.kz", "Secure123!", UserRole.ADMIN, "Demo Admin"
    )
    vendor_user = await _get_or_create_user(
        session, "vendor@test.kz", "Secure123!", UserRole.VENDOR, "Green Cafe"
    )
    await _get_or_create_user(
        session, "customer@test.kz", "Secure123!", UserRole.CUSTOMER, "Demo Customer"
    )

    # Skip listing creation if listings already exist
    existing_count = await session.scalar(
        select(sqlfunc.count()).select_from(Listing)
    )
    if existing_count and existing_count > 0:
        await session.commit()
        return 0

    now = _utcnow()

    result = await session.execute(select(Vendor).where(Vendor.user_id == vendor_user.id))
    vendor = result.scalars().first()
    if not vendor:
        vendor = Vendor(
            user_id=vendor_user.id,
            business_name="Green Cafe",
            bin_number="123456789011",
            address="Алматы, ул. Абая 1",
            latitude=43.238,
            longitude=76.945,
            is_approved=True,
        )
        session.add(vendor)
        await session.flush()

    # 7-day pickup window ensures demo listings stay valid throughout the demo
    p_start = now
    p_end = now + timedelta(days=7)

    for i, raw in enumerate(PRODUCTS):
        data = dict(raw)  # shallow copy — never mutate the module-level constant
        allergens = data.pop("allergens")
        status = data.pop("status", ListingStatus.ACTIVE)
        quantity = data.pop("quantity", 5)
        orig = data.get("original_price", 0)
        curr = data.get("current_price", 0)
        computed_disc = round((1 - curr / orig) * 100) if orig > 0 else 50
        data.setdefault("discount_percentage", max(1, min(90, computed_disc)))
        lat, lng = _ALMATY_COORDS[i % len(_ALMATY_COORDS)]
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
    return len(PRODUCTS)
