from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from fastapi import HTTPException, status

from app.core.config import settings


class SMTPEmailService:
    async def send_password_reset_email(self, recipient_email: str, reset_token: str) -> None:
        reset_url = f"{settings.password_reset_url_base.rstrip('/')}?token={reset_token}"
        subject = "Recuperacao de senha - CRM Backend"
        text_body = (
            "Recebemos uma solicitacao para redefinir sua senha.\n\n"
            f"Use o link abaixo para continuar:\n{reset_url}\n\n"
            f"Token de recuperacao: {reset_token}\n\n"
            "Se voce nao solicitou esta alteracao, ignore este email."
        )
        html_body = f"""
        <html>
          <body>
            <p>Recebemos uma solicitacao para redefinir sua senha.</p>
            <p><a href="{reset_url}">Clique aqui para redefinir sua senha</a></p>
            <p>Token de recuperacao: <strong>{reset_token}</strong></p>
            <p>Se voce nao solicitou esta alteracao, ignore este email.</p>
          </body>
        </html>
        """
        await self.send_email(
            recipient_email=recipient_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

    async def send_email(
        self,
        *,
        recipient_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._from_header()
        message["To"] = recipient_email
        message.set_content(text_body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        try:
            await asyncio.to_thread(self._send_via_smtp, message)
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Falha ao enviar email de recuperacao",
            ) from exc

    def _send_via_smtp(self, message: EmailMessage) -> None:
        with smtplib.SMTP(settings.mail_server, settings.mail_port, timeout=10) as smtp:
            smtp.ehlo()
            if settings.mail_use_tls:
                smtp.starttls()
                smtp.ehlo()
            if settings.mail_username:
                smtp.login(settings.mail_username, settings.mail_password)
            smtp.send_message(message)

    def _from_header(self) -> str:
        if settings.mail_from_name:
            return f"{settings.mail_from_name} <{settings.mail_from_email}>"
        return settings.mail_from_email
