from app.tasks.celery_app import celery_app
from app.services.email_service import (
    send_email,
    build_verification_email,
    build_password_reset_email,
    build_order_confirmation_email,
    build_vendor_approved_email,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="app.tasks.email_tasks.send_verification_email")
def send_verification_email(self, email: str, otp_code: str):
    try:
        subject, html = build_verification_email(otp_code)
        send_email(email, subject, html)
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="app.tasks.email_tasks.send_password_reset_email")
def send_password_reset_email(self, email: str, reset_token: str):
    try:
        subject, html = build_password_reset_email(reset_token)
        send_email(email, subject, html)
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="app.tasks.email_tasks.send_order_confirmation_email")
def send_order_confirmation_email(self, email: str, order_id: int, pickup_token: str, total_amount: float):
    try:
        subject, html = build_order_confirmation_email(order_id, pickup_token, total_amount)
        send_email(email, subject, html)
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="app.tasks.email_tasks.send_vendor_approved_email")
def send_vendor_approved_email(self, email: str, business_name: str):
    try:
        subject, html = build_vendor_approved_email(business_name)
        send_email(email, subject, html)
    except Exception as exc:
        raise self.retry(exc=exc)
