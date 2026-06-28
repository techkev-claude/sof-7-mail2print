import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from logger import get_logger
from config import config

log = get_logger("mailer")

_MIME_FRIENDLY = {
    "application/pdf": "PDF (.pdf)",
    "image/jpeg": "JPEG (.jpg, .jpeg)",
    "image/png": "PNG (.png)",
    "image/tiff": "TIFF (.tif, .tiff)",
}


def _smtp_enabled() -> bool:
    return bool(config.SMTP_HOST and config.SMTP_USER and config.SMTP_FROM)


def _send(to: list[str], subject: str, body: str, cc: list[str] | None = None) -> None:
    msg = MIMEMultipart()
    msg["From"] = config.SMTP_FROM
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    recipients = to + (cc or [])

    try:
        if config.SMTP_USE_STARTTLS:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT)

        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.sendmail(config.SMTP_FROM, recipients, msg.as_string())
        server.quit()
        log.info("E-Mail gesendet", to=to, cc=cc, subject=subject)
    except Exception as e:
        log.error("E-Mail konnte nicht gesendet werden", error=str(e), to=to)


def send_print_error_notification(
    mail_sender: str, subject: str, filename: str, error_info: str
) -> None:
    if not _smtp_enabled() or not config.ADMIN_EMAIL:
        log.debug("SMTP/ADMIN_EMAIL nicht konfiguriert — Fehlerbenachrichtigung übersprungen")
        return

    body = f"""Hallo,

ein Druckauftrag ist fehlgeschlagen und konnte nicht verarbeitet werden.

Details:
  Absender:  {mail_sender}
  Betreff:   {subject}
  Datei:     {filename}
  Fehler:    {error_info}

Die E-Mail wurde als gelesen markiert. Bitte prüfe den Drucker und versuche es ggf. manuell.

Mail2Print
"""
    _send(
        to=[config.ADMIN_EMAIL],
        subject=f"[Mail2Print] Druckfehler: {filename}",
        body=body,
    )


def send_unsupported_format_notification(
    mail_sender: str, subject: str, filenames: list[str]
) -> None:
    if not _smtp_enabled():
        log.debug("SMTP nicht konfiguriert — Format-Benachrichtigung übersprungen")
        return

    allowed = "\n  ".join(
        _MIME_FRIENDLY.get(t, t) for t in config.ALLOWED_MIME_TYPES
    )
    files_list = "\n".join(f"  - {f}" for f in filenames)

    body = f"""Hallo,

vielen Dank für deine E-Mail! Leider konnten folgende Anhänge nicht gedruckt werden, \
da das Dateiformat nicht unterstützt wird:

{files_list}

Unterstützte Formate:
  {allowed}

Bitte sende die Datei(en) in einem der oben genannten Formate erneut, dann wird sie \
automatisch gedruckt.

Viele Grüße,
Mail2Print
"""
    cc = [config.ADMIN_EMAIL] if config.ADMIN_EMAIL else []
    _send(
        to=[mail_sender],
        subject=f"Re: {subject}",
        body=body,
        cc=cc or None,
    )
