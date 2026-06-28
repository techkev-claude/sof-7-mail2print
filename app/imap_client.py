import imaplib
import email
import email.utils
from contextlib import contextmanager
from dataclasses import dataclass, field

from logger import get_logger
from config import config

log = get_logger("imap_client")


@dataclass
class MailAttachment:
    filename: str
    mime_type: str
    data: bytes


@dataclass
class MailInfo:
    mail_id: str
    sender: str
    subject: str
    printable: list[MailAttachment] = field(default_factory=list)
    unsupported: list[MailAttachment] = field(default_factory=list)


def _connect() -> imaplib.IMAP4_SSL | imaplib.IMAP4:
    if config.IMAP_USE_SSL:
        conn = imaplib.IMAP4_SSL(config.IMAP_HOST, config.IMAP_PORT)
        log.info("IMAP SSL-Verbindung hergestellt", host=config.IMAP_HOST, port=config.IMAP_PORT)
    else:
        conn = imaplib.IMAP4(config.IMAP_HOST, config.IMAP_PORT)
        conn.starttls()
        log.info("IMAP STARTTLS-Verbindung hergestellt", host=config.IMAP_HOST)
    conn.login(config.IMAP_USER, config.IMAP_PASSWORD)
    conn.select(config.IMAP_FOLDER)
    return conn


@contextmanager
def imap_connection():
    conn = _connect()
    try:
        yield conn
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def fetch_unseen_mails(conn) -> list[MailInfo]:
    status, data = conn.search(None, "UNSEEN")
    if status != "OK" or not data[0]:
        log.debug("Keine neuen Mails gefunden")
        return []

    mail_ids = data[0].split()
    log.info("Neue Mails gefunden", count=len(mail_ids))
    mails = []

    for mail_id in mail_ids:
        status, msg_data = conn.fetch(mail_id, "(RFC822)")
        if status != "OK":
            log.warning("Mail konnte nicht abgerufen werden", mail_id=mail_id)
            continue

        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        sender = email.utils.parseaddr(msg.get("From", ""))[1].lower()
        subject = msg.get("Subject", "(kein Betreff)")

        log.info("Mail verarbeite", sender=sender, subject=subject)

        if config.ALLOWED_SENDERS and sender not in config.ALLOWED_SENDERS:
            log.warning(
                "Absender nicht in Whitelist — Mail wird ignoriert",
                sender=sender,
                whitelist=config.ALLOWED_SENDERS,
            )
            mark_seen(conn, mail_id)
            continue

        mail_info = MailInfo(
            mail_id=mail_id.decode(),
            sender=sender,
            subject=subject,
        )

        has_attachments = False
        for part in msg.walk():
            content_disposition = part.get("Content-Disposition", "")
            if "attachment" not in content_disposition and "inline" not in content_disposition:
                continue

            has_attachments = True
            mime_type = part.get_content_type().lower()
            filename = part.get_filename() or f"attachment_{mail_id.decode()}"
            payload = part.get_payload(decode=True)

            if not payload:
                log.warning("Leerer Anhang", filename=filename)
                continue

            attachment = MailAttachment(filename=filename, mime_type=mime_type, data=payload)

            if mime_type in config.ALLOWED_MIME_TYPES:
                mail_info.printable.append(attachment)
                log.info(
                    "Druckbarer Anhang gefunden",
                    filename=filename,
                    mime_type=mime_type,
                    size_bytes=len(payload),
                )
            else:
                mail_info.unsupported.append(attachment)
                log.warning(
                    "MIME-Type nicht erlaubt — Anhang übersprungen",
                    mime_type=mime_type,
                    filename=filename,
                    allowed=config.ALLOWED_MIME_TYPES,
                )

        if not has_attachments:
            log.warning("Mail enthält keine Anhänge", sender=sender, subject=subject)
        elif not mail_info.printable and not mail_info.unsupported:
            log.warning("Mail enthält keine druckbaren Anhänge", sender=sender, subject=subject)

        mails.append(mail_info)

    return mails


def mark_seen(conn, mail_id: str | bytes) -> None:
    mid = mail_id if isinstance(mail_id, bytes) else mail_id.encode()
    conn.store(mid, "+FLAGS", "\\Seen")
    log.debug("Mail als SEEN markiert", mail_id=mail_id)


def move_to_trash(conn, mail_id: str | bytes) -> None:
    mid = mail_id if isinstance(mail_id, bytes) else mail_id.encode()
    status, _ = conn.copy(mid, config.IMAP_TRASH_FOLDER)
    if status == "OK":
        conn.store(mid, "+FLAGS", "\\Deleted")
        conn.expunge()
        log.debug("Mail in Papierkorb verschoben", mail_id=mail_id, folder=config.IMAP_TRASH_FOLDER)
    else:
        log.warning(
            "Papierkorb-Verschiebung fehlgeschlagen — markiere als SEEN",
            mail_id=mail_id,
            trash_folder=config.IMAP_TRASH_FOLDER,
        )
        mark_seen(conn, mid)
