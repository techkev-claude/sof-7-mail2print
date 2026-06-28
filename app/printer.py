import subprocess
import tempfile
import os
from pathlib import Path

from logger import get_logger
from config import config

log = get_logger("printer")


def print_attachment(filename: str, data: bytes) -> bool:
    tmp_dir = Path(config.DATA_PATH) / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(filename).suffix or ".dat"
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            dir=tmp_dir,
            suffix=suffix,
            delete=False,
            prefix="mail2print_",
        ) as tmp_file:
            tmp_file.write(data)
            tmp_path = tmp_file.name

        log.info("Temporäre Druckdatei erstellt", path=tmp_path, size_bytes=len(data))

        cmd = ["lp", "-d", config.PRINTER_NAME]
        if config.PRINT_OPTIONS:
            for opt in config.PRINT_OPTIONS.split():
                cmd += ["-o", opt]
        cmd.append(tmp_path)

        log.info("Druckauftrag wird gesendet", command=" ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            log.error(
                "Druckauftrag fehlgeschlagen",
                returncode=result.returncode,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
            )
            return False

        log.info(
            "Druckauftrag erfolgreich übergeben",
            stdout=result.stdout.strip(),
            filename=filename,
        )
        return True

    except subprocess.TimeoutExpired:
        log.error("Druckauftrag Timeout — lp antwortet nicht", filename=filename)
        return False
    except Exception as e:
        log.error("Unerwarteter Druckfehler", error=str(e), filename=filename)
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                log.debug("Temporäre Datei gelöscht", path=tmp_path)
            except Exception as e:
                log.warning("Temporäre Datei konnte nicht gelöscht werden", error=str(e))
