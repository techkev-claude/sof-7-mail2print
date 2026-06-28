import schedule
import signal
import sys
import time

from config import config
from imap_client import fetch_unseen_mails, imap_connection, mark_seen, move_to_trash
from logger import get_logger, setup_logging
from mailer import send_print_error_notification, send_unsupported_format_notification
from printer import print_attachment
from webhook import call_webhook

setup_logging()
log = get_logger("main")


def check_and_print() -> None:
    log.info("Postfach-Check gestartet", folder=config.IMAP_FOLDER, user=config.IMAP_USER)
    try:
        with imap_connection() as conn:
            mails = fetch_unseen_mails(conn)

            for mail in mails:
                # Notify sender about unsupported attachments
                if mail.unsupported:
                    filenames = [a.filename for a in mail.unsupported]
                    log.info(
                        "Nicht unterstützte Anhänge — Benachrichtigung an Absender",
                        sender=mail.sender,
                        filenames=filenames,
                    )
                    send_unsupported_format_notification(
                        mail_sender=mail.sender,
                        subject=mail.subject,
                        filenames=filenames,
                    )

                # No printable attachments → just mark as seen
                if not mail.printable:
                    log.info(
                        "Keine druckbaren Anhänge — Mail wird als SEEN markiert",
                        sender=mail.sender,
                        subject=mail.subject,
                    )
                    mark_seen(conn, mail.mail_id)
                    continue

                # Print each printable attachment
                all_ok = True
                for attachment in mail.printable:
                    success = print_attachment(attachment.filename, attachment.data)
                    call_webhook(
                        filename=attachment.filename,
                        sender=mail.sender,
                        success=success,
                    )

                    if success:
                        log.info(
                            "Druckvorgang abgeschlossen",
                            filename=attachment.filename,
                            mail_id=mail.mail_id,
                        )
                    else:
                        log.error(
                            "Druckvorgang fehlgeschlagen",
                            filename=attachment.filename,
                            mail_id=mail.mail_id,
                        )
                        send_print_error_notification(
                            mail_sender=mail.sender,
                            subject=mail.subject,
                            filename=attachment.filename,
                            error_info="lp-Druckbefehl ist fehlgeschlagen (Rückgabecode ≠ 0)",
                        )
                        all_ok = False

                if all_ok:
                    move_to_trash(conn, mail.mail_id)
                    log.info(
                        "Mail in Papierkorb verschoben nach erfolgreichem Druck",
                        mail_id=mail.mail_id,
                    )
                else:
                    mark_seen(conn, mail.mail_id)
                    log.warning(
                        "Mail als SEEN markiert wegen Druckfehler",
                        mail_id=mail.mail_id,
                    )

    except Exception as e:
        log.error("Fehler im Prüf-Zyklus", error=str(e), exc_info=True)


def _shutdown(signum, frame) -> None:
    log.info("Shutdown-Signal empfangen", signal=signum)
    sys.exit(0)


signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)

log.info(
    "Mail2Print gestartet",
    poll_interval=config.POLL_INTERVAL_SECONDS,
    imap_host=config.IMAP_HOST,
    printer_host=config.PRINTER_HOST,
    printer_name=config.PRINTER_NAME,
)

check_and_print()

schedule.every(config.POLL_INTERVAL_SECONDS).seconds.do(check_and_print)

while True:
    schedule.run_pending()
    time.sleep(1)
