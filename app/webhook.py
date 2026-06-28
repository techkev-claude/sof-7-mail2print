import hashlib
import hmac
import json
from datetime import datetime, timezone

import httpx

from logger import get_logger
from config import config

log = get_logger("webhook")


def call_webhook(filename: str, sender: str, success: bool) -> None:
    if not config.WEBHOOK_URL:
        log.debug("Kein Webhook konfiguriert — übersprungen")
        return

    payload = {
        "event": "print_job",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "filename": filename,
        "sender": sender,
        "success": success,
        "printer": config.PRINTER_NAME,
    }

    headers = {"Content-Type": "application/json"}

    if config.WEBHOOK_SECRET:
        body = json.dumps(payload).encode()
        sig = hmac.new(
            config.WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        headers["X-Mail2Print-Signature"] = f"sha256={sig}"

    try:
        with httpx.Client(timeout=config.WEBHOOK_TIMEOUT) as client:
            response = client.request(
                method=config.WEBHOOK_METHOD.upper(),
                url=config.WEBHOOK_URL,
                json=payload,
                headers=headers,
            )
        log.info(
            "Webhook aufgerufen",
            url=config.WEBHOOK_URL,
            status_code=response.status_code,
            filename=filename,
            success=success,
        )
    except httpx.TimeoutException:
        log.warning("Webhook Timeout", url=config.WEBHOOK_URL)
    except httpx.RequestError as e:
        log.error("Webhook Fehler", url=config.WEBHOOK_URL, error=str(e))
