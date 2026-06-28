import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise ValueError(f"Pflichtfeld fehlt in .env: {key}")
    return val


def _optional(key: str, default=None):
    return os.getenv(key, default)


class Config:
    # IMAP
    IMAP_HOST: str = _require("IMAP_HOST")
    IMAP_PORT: int = int(_optional("IMAP_PORT", "993"))
    IMAP_USER: str = _require("IMAP_USER")
    IMAP_PASSWORD: str = _require("IMAP_PASSWORD")
    IMAP_FOLDER: str = _optional("IMAP_FOLDER", "INBOX")
    IMAP_USE_SSL: bool = _optional("IMAP_USE_SSL", "true").lower() == "true"
    IMAP_TRASH_FOLDER: str = _optional("IMAP_TRASH_FOLDER", "Trash")
    POLL_INTERVAL_SECONDS: int = int(_optional("POLL_INTERVAL_SECONDS", "60"))

    # Absender-Whitelist (kommagetrennt, leer = alle erlaubt)
    ALLOWED_SENDERS: list[str] = [
        s.strip().lower()
        for s in _optional("ALLOWED_SENDERS", "").split(",")
        if s.strip()
    ]

    # Drucker
    PRINTER_NAME: str = _optional("PRINTER_NAME", "mail2print")
    PRINTER_HOST: str = _require("PRINTER_HOST")
    PRINTER_PORT: int = int(_optional("PRINTER_PORT", "9100"))
    PRINT_OPTIONS: str = _optional("PRINT_OPTIONS", "")

    # Erlaubte Anhang-Typen (kommagetrennt)
    ALLOWED_MIME_TYPES: list[str] = [
        s.strip().lower()
        for s in _optional(
            "ALLOWED_MIME_TYPES",
            "application/pdf,image/jpeg,image/png,image/tiff",
        ).split(",")
        if s.strip()
    ]

    # SMTP (für Benachrichtigungen)
    SMTP_HOST: str = _optional("SMTP_HOST", "")
    SMTP_PORT: int = int(_optional("SMTP_PORT", "587"))
    SMTP_USER: str = _optional("SMTP_USER", "")
    SMTP_PASSWORD: str = _optional("SMTP_PASSWORD", "")
    SMTP_USE_STARTTLS: bool = _optional("SMTP_USE_STARTTLS", "true").lower() == "true"
    SMTP_FROM: str = _optional("SMTP_FROM", "")
    ADMIN_EMAIL: str = _optional("ADMIN_EMAIL", "")

    # Webhook
    WEBHOOK_URL: str = _optional("WEBHOOK_URL", "")
    WEBHOOK_METHOD: str = _optional("WEBHOOK_METHOD", "POST")
    WEBHOOK_TIMEOUT: int = int(_optional("WEBHOOK_TIMEOUT", "10"))
    WEBHOOK_SECRET: str = _optional("WEBHOOK_SECRET", "")

    # Allgemein
    LOG_LEVEL: str = _optional("LOG_LEVEL", "INFO")
    DATA_PATH: str = _optional("DATA_PATH", "/app/data")
    TZ: str = _optional("TZ", "Europe/Berlin")


config = Config()
