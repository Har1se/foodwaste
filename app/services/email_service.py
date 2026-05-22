import asyncio
import json as _json
import logging
import smtplib
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def _send_via_resend_api(to: str, subject: str, html_body: str, api_key: str) -> None:
    """Send email via Resend HTTP API — works on Render free tier (SMTP is blocked)."""
    from_addr = settings.SMTP_FROM or "onboarding@resend.dev"
    payload = _json.dumps({
        "from": f"RescueBite <{from_addr}>",
        "to": [to],
        "subject": subject,
        "html": html_body,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
        logger.info("Resend API: email sent to %s id=%s", to, result.get("id"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error("Resend API error %s for %s: %s", exc.code, to, body)
        raise


def send_email(to: str, subject: str, html_body: str) -> None:
    """Send an HTML email — uses Resend HTTP API if key detected, else SMTP."""
    if not settings.SMTP_PASSWORD:
        logger.warning("SMTP not configured — skipping email to %s", to)
        return

    if settings.SMTP_PASSWORD.startswith("re_"):
        _send_via_resend_api(to, subject, html_body, settings.SMTP_PASSWORD)
        return

    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning("SMTP not configured — skipping email to %s", to)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"RescueBite <{settings.SMTP_USER}>"
    msg["To"] = to
    msg["Reply-To"] = settings.SMTP_USER
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, [to], msg.as_string())
        logger.info("Email sent to %s — %s", to, subject)
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP auth failed — check SMTP_USER / SMTP_PASSWORD in .env")
        raise
    except smtplib.SMTPException as exc:
        logger.error("SMTP error sending to %s: %s", to, exc)
        raise


# ── Email templates ───────────────────────────────────────────────────────────

def build_verification_email(otp_code: str) -> tuple[str, str]:
    subject = "RescueBite — Подтвердите ваш email"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto">
      <h2 style="color:#2d7a4f">Добро пожаловать в RescueBite!</h2>
      <p>Ваш код подтверждения:</p>
      <div style="font-size:32px;font-weight:bold;letter-spacing:8px;color:#2d7a4f;margin:20px 0">{otp_code}</div>
      <p>Код действителен <strong>15 минут</strong>.</p>
      <p style="color:#888;font-size:12px">Если вы не регистрировались — проигнорируйте это письмо.</p>
    </div>
    """
    return subject, html


def build_password_reset_email(reset_token: str) -> tuple[str, str]:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    subject = "RescueBite — Сброс пароля"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto">
      <h2 style="color:#2d7a4f">Сброс пароля</h2>
      <p>Нажмите кнопку ниже, чтобы установить новый пароль:</p>
      <a href="{reset_url}" style="display:inline-block;padding:12px 24px;background:#2d7a4f;color:#fff;text-decoration:none;border-radius:6px;margin:16px 0">Сбросить пароль</a>
      <p>Ссылка действительна <strong>30 минут</strong>.</p>
      <p style="color:#888;font-size:12px">Если вы не запрашивали сброс — проигнорируйте это письмо.</p>
    </div>
    """
    return subject, html


def build_order_confirmation_email(order_id: int, pickup_token: str, total_amount: float) -> tuple[str, str]:
    subject = f"RescueBite — Заказ #{order_id} подтверждён"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto">
      <h2 style="color:#2d7a4f">Заказ подтверждён!</h2>
      <p>Ваш заказ <strong>#{order_id}</strong> успешно оформлен.</p>
      <table style="width:100%;border-collapse:collapse;margin:16px 0">
        <tr><td style="padding:8px;color:#555">Сумма:</td><td style="padding:8px;font-weight:bold">{total_amount:,.0f} ₸</td></tr>
        <tr style="background:#f9f9f9"><td style="padding:8px;color:#555">Токен получения:</td><td style="padding:8px;font-family:monospace;font-size:18px;font-weight:bold;color:#2d7a4f">{pickup_token}</td></tr>
      </table>
      <p>Покажите токен продавцу при получении заказа.</p>
      <p style="color:#888;font-size:12px">Спасибо, что помогаете бороться с пищевыми отходами!</p>
    </div>
    """
    return subject, html


def build_auction_won_email(auction_id: int, winning_amount: int) -> tuple[str, str]:
    subject = f"RescueBite — Вы выиграли аукцион #{auction_id}!"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto">
      <h2 style="color:#2d7a4f">Поздравляем! Вы выиграли аукцион!</h2>
      <p>Ваша ставка на аукционе <strong>#{auction_id}</strong> оказалась самой низкой уникальной.</p>
      <table style="width:100%;border-collapse:collapse;margin:16px 0">
        <tr><td style="padding:8px;color:#555">Выигрышная ставка:</td><td style="padding:8px;font-weight:bold;color:#2d7a4f">{winning_amount:,.0f} ₸</td></tr>
      </table>
      <p>Перейдите в приложение, чтобы оформить заказ по этой цене.</p>
      <a href="{settings.FRONTEND_URL}/auctions/{auction_id}" style="display:inline-block;padding:12px 24px;background:#2d7a4f;color:#fff;text-decoration:none;border-radius:6px;margin:16px 0">Перейти к аукциону</a>
      <p style="color:#888;font-size:12px">Спасибо, что помогаете бороться с пищевыми отходами!</p>
    </div>
    """
    return subject, html


def build_new_listing_email(
    title: str,
    current_price: int,
    vendor_name: str,
    category: str | None,
) -> tuple[str, str]:
    subject = f"RescueBite — Новое предложение: {title}"
    cat_label = category.capitalize() if category else "Еда"
    price_label = "Бесплатно!" if current_price == 0 else f"{current_price:,.0f} ₸"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto">
      <h2 style="color:#2d7a4f">🍱 Новое предложение на RescueBite!</h2>
      <table style="width:100%;border-collapse:collapse;margin:16px 0">
        <tr><td style="padding:8px;color:#555">Блюдо:</td><td style="padding:8px;font-weight:bold">{title}</td></tr>
        <tr style="background:#f9f9f9"><td style="padding:8px;color:#555">Категория:</td><td style="padding:8px">{cat_label}</td></tr>
        <tr><td style="padding:8px;color:#555">Цена:</td><td style="padding:8px;font-weight:bold;color:#2d7a4f">{price_label}</td></tr>
        <tr style="background:#f9f9f9"><td style="padding:8px;color:#555">От:</td><td style="padding:8px">{vendor_name}</td></tr>
      </table>
      <a href="{settings.FRONTEND_URL}" style="display:inline-block;padding:12px 24px;background:#2d7a4f;color:#fff;text-decoration:none;border-radius:6px;margin:16px 0">Смотреть предложение →</a>
      <p style="color:#888;font-size:12px">Спасаем еду вместе — спасибо, что с нами!</p>
    </div>
    """
    return subject, html


def build_driver_assignment_email(
    order_id: int,
    vendor_name: str,
    vendor_address: str,
    distance_km: float,
) -> tuple[str, str]:
    subject = f"RescueBite — Новый заказ #{order_id} назначен вам"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto">
      <h2 style="color:#2d7a4f">🚴 Новый заказ для доставки!</h2>
      <p>Вам назначен заказ <strong>#{order_id}</strong>. Пожалуйста, заберите его как можно скорее.</p>
      <table style="width:100%;border-collapse:collapse;margin:16px 0">
        <tr><td style="padding:8px;color:#555">Заказ №:</td><td style="padding:8px;font-weight:bold">#{order_id}</td></tr>
        <tr style="background:#f9f9f9"><td style="padding:8px;color:#555">Точка самовывоза:</td><td style="padding:8px">{vendor_name}</td></tr>
        <tr><td style="padding:8px;color:#555">Адрес:</td><td style="padding:8px">{vendor_address}</td></tr>
        <tr style="background:#f9f9f9"><td style="padding:8px;color:#555">Расстояние:</td><td style="padding:8px;color:#2d7a4f;font-weight:bold">{distance_km:.1f} км</td></tr>
      </table>
      <a href="{settings.FRONTEND_URL}/drivers" style="display:inline-block;padding:12px 24px;background:#2d7a4f;color:#fff;text-decoration:none;border-radius:6px;margin:16px 0">Открыть маршрут →</a>
      <p style="color:#888;font-size:12px">Спасибо, что помогаете доставлять еду!</p>
    </div>
    """
    return subject, html


def build_auction_lost_email(auction_id: int) -> tuple[str, str]:
    subject = f"RescueBite — Аукцион #{auction_id} завершён"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto">
      <h2 style="color:#d97706">Аукцион завершён</h2>
      <p>Аукцион <strong>#{auction_id}</strong> завершён. На этот раз победила другая ставка.</p>
      <p>Не расстраивайтесь — на платформе появляются новые лоты каждый день!</p>
      <a href="{settings.FRONTEND_URL}/auctions" style="display:inline-block;padding:12px 24px;background:#2d7a4f;color:#fff;text-decoration:none;border-radius:6px;margin:16px 0">Смотреть другие аукционы →</a>
      <p style="color:#888;font-size:12px">Спасибо за участие в борьбе с пищевыми отходами!</p>
    </div>
    """
    return subject, html


async def _fire(coro):
    """Run a coroutine as a background task, logging any errors."""
    try:
        await coro
    except Exception as exc:
        logger.error("Background email failed: %s", exc)


async def _send(to: str, subject: str, html: str) -> None:
    await asyncio.to_thread(send_email, to, subject, html)


async def async_send_verification_email(email: str, otp_code: str) -> None:
    subject, html = build_verification_email(otp_code)
    asyncio.create_task(_fire(_send(email, subject, html)))


async def async_send_password_reset_email(email: str, reset_token: str) -> None:
    subject, html = build_password_reset_email(reset_token)
    asyncio.create_task(_fire(_send(email, subject, html)))


async def async_send_order_confirmation_email(email: str, order_id: int, pickup_token: str, total_amount: float) -> None:
    subject, html = build_order_confirmation_email(order_id, pickup_token, total_amount)
    asyncio.create_task(_fire(_send(email, subject, html)))


async def async_send_vendor_approved_email(email: str, business_name: str) -> None:
    subject, html = build_vendor_approved_email(business_name)
    asyncio.create_task(_fire(_send(email, subject, html)))


async def async_send_new_listing_email(email: str, title: str, current_price: int, vendor_name: str, category) -> None:
    subject, html = build_new_listing_email(title, current_price, vendor_name, category)
    asyncio.create_task(_fire(_send(email, subject, html)))


async def async_send_auction_won_email(email: str, auction_id: int, winning_amount: int) -> None:
    subject, html = build_auction_won_email(auction_id, winning_amount)
    asyncio.create_task(_fire(_send(email, subject, html)))


async def async_send_driver_assignment_email(email: str, order_id: int, vendor_name: str, vendor_address: str, distance_km: float) -> None:
    subject, html = build_driver_assignment_email(order_id, vendor_name, vendor_address, distance_km)
    asyncio.create_task(_fire(_send(email, subject, html)))


def build_vendor_approved_email(business_name: str) -> tuple[str, str]:
    subject = "RescueBite — Ваш аккаунт продавца одобрен!"
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto">
      <h2 style="color:#2d7a4f">Поздравляем, {business_name}!</h2>
      <p>Ваш аккаунт продавца на платформе RescueBite <strong>успешно одобрен</strong>.</p>
      <p>Теперь вы можете создавать листинги еды и принимать заказы.</p>
      <a href="{settings.FRONTEND_URL}/vendor/dashboard" style="display:inline-block;padding:12px 24px;background:#2d7a4f;color:#fff;text-decoration:none;border-radius:6px;margin:16px 0">Перейти в кабинет</a>
      <p style="color:#888;font-size:12px">Вместе спасаем еду — спасибо, что с нами!</p>
    </div>
    """
    return subject, html
