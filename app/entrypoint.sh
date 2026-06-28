#!/bin/bash
set -e

# CUPS-Daemon starten
service cups start
sleep 2

# Drucker bei CUPS registrieren (idempotent via lpstat-Prüfung)
if ! lpstat -p "${PRINTER_NAME}" 2>/dev/null | grep -q "printer"; then
    lpadmin -p "${PRINTER_NAME}" \
            -E \
            -v "socket://${PRINTER_HOST}:${PRINTER_PORT}" \
            -m drv:///sample.drv/generpcl6.ppd
    lpoptions -d "${PRINTER_NAME}"
    echo "[entrypoint] Drucker '${PRINTER_NAME}' registriert unter socket://${PRINTER_HOST}:${PRINTER_PORT}"
else
    echo "[entrypoint] Drucker '${PRINTER_NAME}' bereits registriert"
fi

# Healthcheck-Datei initial anlegen
touch /app/data/healthcheck

# Minimaler HTTP-Healthcheck-Server im Hintergrund
python -c "
import http.server, threading
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'ok')
    def log_message(self, *a): pass
s = http.server.HTTPServer(('0.0.0.0', 8000), H)
threading.Thread(target=s.serve_forever, daemon=True).start()
import time
while True: time.sleep(3600)
" &

# Hauptanwendung starten
exec python main.py
