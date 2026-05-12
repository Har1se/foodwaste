import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str) -> None:
    """Send an HTML email via SMTP. Silently skips if SMTP is not configured."""
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning("SMTP not configured — skipping email to %s", to)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to, msg.as_string())

    logger.info("Email sent to %s — %s", to, subject)


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
