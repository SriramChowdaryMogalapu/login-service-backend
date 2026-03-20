from flask import current_app
from flask_mail import Message

from app.extensions import mail


def _render_email_template(title: str, intro: str, body_html: str, cta_label: str = "", cta_url: str = "") -> str:
    brand_name = current_app.config.get("EMAIL_BRAND_NAME", "Login Service")
    primary_color = current_app.config.get("EMAIL_PRIMARY_COLOR", "#0F766E")

    cta_html = ""
    if cta_label and cta_url:
        cta_html = (
            f'<p style="margin:24px 0;">'
            f'<a href="{cta_url}" '
            f'style="background:{primary_color};color:#FFFFFF;text-decoration:none;padding:12px 20px;'
            f'border-radius:8px;display:inline-block;font-weight:600;">{cta_label}</a></p>'
        )

    return f"""
    <div style="margin:0;padding:0;background:#F4F7FB;font-family:Segoe UI,Roboto,Arial,sans-serif;color:#102A43;">
      <div style="max-width:620px;margin:24px auto;padding:0 12px;">
        <div style="background:{primary_color};color:#FFFFFF;padding:18px 22px;border-radius:12px 12px 0 0;">
          <h1 style="margin:0;font-size:20px;line-height:1.35;">{brand_name}</h1>
        </div>
        <div style="background:#FFFFFF;padding:24px 22px;border-radius:0 0 12px 12px;border:1px solid #D9E2EC;border-top:none;">
          <h2 style="margin:0 0 12px;font-size:22px;color:#102A43;">{title}</h2>
          <p style="margin:0 0 14px;font-size:15px;line-height:1.6;color:#243B53;">{intro}</p>
          <div style="font-size:15px;line-height:1.65;color:#334E68;">{body_html}</div>
          {cta_html}
          <p style="margin:24px 0 0;font-size:12px;color:#627D98;">This is an automated message from {brand_name}. Please do not reply directly to this email.</p>
        </div>
      </div>
    </div>
    """


def _send_html_email(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    msg = Message(
        subject=subject,
        recipients=[to_email],
        body=text_body,
        html=html_body,
        sender=(
            current_app.config.get("FROM_NAME", "Login Service"),
            current_app.config["FROM_EMAIL"],
        ),
    )
    mail.send(msg)


def send_password_reset_email(email: str, reset_url: str) -> None:
    brand_name = current_app.config.get("EMAIL_BRAND_NAME", "Login Service")
    html_body = _render_email_template(
        title="Reset Your Password",
        intro="We received a request to reset your password.",
        body_html="<p>If you requested this, use the button below. This link expires in 1 hour.</p>",
        cta_label="Reset Password",
        cta_url=reset_url,
    )

    _send_html_email(
        to_email=email,
        subject=f"{brand_name}: Password Reset",
        html_body=html_body,
        text_body=f"Reset your password using this link (expires in 1 hour): {reset_url}",
    )


def send_signup_email(email: str) -> None:
    brand_name = current_app.config.get("EMAIL_BRAND_NAME", "Login Service")
    html_body = _render_email_template(
        title="Welcome",
        intro="Your account has been created successfully.",
        body_html="<p>You can now sign in securely and continue your verification flow.</p>",
    )

    _send_html_email(
        to_email=email,
        subject=f"Welcome to {brand_name}",
        html_body=html_body,
        text_body=f"Welcome to {brand_name}. Your account has been created successfully.",
    )


def send_password_changed_email(email: str) -> None:
    brand_name = current_app.config.get("EMAIL_BRAND_NAME", "Login Service")
    html_body = _render_email_template(
        title="Password Changed",
        intro="Your password was changed successfully.",
        body_html="<p>If this was not performed by you, contact support immediately and secure your account.</p>",
    )

    _send_html_email(
        to_email=email,
        subject=f"{brand_name}: Password Changed",
        html_body=html_body,
        text_body="Your password has been changed successfully. If this was not you, contact support immediately.",
    )
