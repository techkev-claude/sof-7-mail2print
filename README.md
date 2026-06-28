# Mail2Print

Schlanker Hintergrunddienst, der ein IMAP-Postfach überwacht und alle Dateianhänge neu eingegangener E-Mails automatisch an einen Netzwerkdrucker sendet. Ein einfaches Weiterleiten einer Mail reicht zum Drucken aus.

## Voraussetzungen

- Docker & Docker Compose
- Netzwerkdrucker mit RAW-Port (Standard: 9100 / JetDirect)
- IMAP-Postfach (netcup oder anderer Anbieter mit Standard-IMAP-Auth)

## Schnellstart

```bash
git clone <repo-url> mail2print
cd mail2print
cp .env.example .env
# .env anpassen (siehe Tabelle unten)
docker compose up -d
```

### Über Portainer

1. Portainer → **Stacks** → **Add Stack**
2. Repository-URL eintragen, Branch `main`
3. Unter **Env variables** die Werte aus `.env` eintragen (oder `.env`-Datei hochladen)
4. **Deploy the stack**

## Logs prüfen

```bash
docker logs mail2print -f
```

## Drucker-Status prüfen

```bash
docker exec mail2print lpstat -p
```

## Healthcheck

```bash
curl http://localhost:${PORT}/
# → ok
```

---

## Konfiguration (`.env`)

| Variable | Beschreibung | Pflicht | Standard |
|---|---|---|---|
| `PORT` | Externer Port für Healthcheck | ✅ | — |
| `TZ` | Zeitzone für Log-Timestamps | — | `Europe/Berlin` |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` | — | `INFO` |
| `DATA_PATH` | Host-Pfad für persistente Daten & tmp | ✅ | — |
| `IMAP_HOST` | IMAP-Server-Hostname | ✅ | — |
| `IMAP_PORT` | IMAP-Port | — | `993` |
| `IMAP_USER` | IMAP-Benutzername / E-Mail | ✅ | — |
| `IMAP_PASSWORD` | IMAP-Passwort | ✅ | — |
| `IMAP_FOLDER` | Zu überwachender Ordner | — | `INBOX` |
| `IMAP_USE_SSL` | SSL statt STARTTLS | — | `true` |
| `IMAP_TRASH_FOLDER` | Papierkorb-Ordnername auf dem Server | — | `Trash` |
| `POLL_INTERVAL_SECONDS` | Prüfintervall in Sekunden | — | `60` |
| `ALLOWED_SENDERS` | Absender-Whitelist, kommagetrennt (leer = alle) | — | — |
| `PRINTER_NAME` | CUPS-interner Druckername | — | `mail2print` |
| `PRINTER_HOST` | IP-Adresse des Druckers | ✅ | — |
| `PRINTER_PORT` | RAW-Druckport | — | `9100` |
| `PRINT_OPTIONS` | Zusatz-Optionen für `lp -o` | — | — |
| `ALLOWED_MIME_TYPES` | Erlaubte Anhang-Typen, kommagetrennt | — | PDF, JPEG, PNG, TIFF |
| `SMTP_HOST` | SMTP-Server für Benachrichtigungen | — | — |
| `SMTP_PORT` | SMTP-Port | — | `587` |
| `SMTP_USER` | SMTP-Benutzername | — | — |
| `SMTP_PASSWORD` | SMTP-Passwort | — | — |
| `SMTP_USE_STARTTLS` | STARTTLS (Port 587); `false` = Implicit SSL (Port 465) | — | `true` |
| `SMTP_FROM` | Absender-Adresse für ausgehende Mails | — | — |
| `ADMIN_EMAIL` | Admin-E-Mail für Fehlerbenachrichtigungen | — | — |
| `WEBHOOK_URL` | Ziel-URL nach jedem Druckauftrag | — | — |
| `WEBHOOK_METHOD` | HTTP-Methode | — | `POST` |
| `WEBHOOK_TIMEOUT` | Timeout in Sekunden | — | `10` |
| `WEBHOOK_SECRET` | HMAC-Secret für `X-Mail2Print-Signature` Header | — | — |

### Hinweise

**`IMAP_TRASH_FOLDER`:** Der Ordnername des Papierkorbs variiert je nach Server. Netcup nutzt meist `Trash`, andere Anbieter `Deleted Items` oder `INBOX.Trash`. Prüfen via `docker exec mail2print python -c "import imaplib; c = imaplib.IMAP4_SSL('imap.netcup.de'); c.login('user', 'pass'); print(c.list())"`.

**SMTP-Konfiguration (netcup):**
- `SMTP_HOST=mail.netcup.de`
- `SMTP_PORT=587` mit `SMTP_USE_STARTTLS=true`
- Gleiche Zugangsdaten wie IMAP

**`PRINT_OPTIONS`-Beispiele:**
- Duplex: `sides=two-sided-long-edge`
- Papierformat: `media=A4`
- Kombiniert: `sides=two-sided-long-edge media=A4`

---

## Verhalten

| Situation | Aktion |
|---|---|
| PDF / Bild erhalten, Druck OK | Mail in Papierkorb verschoben |
| Druck fehlgeschlagen | Mail als SEEN markiert, Fehler-Mail an `ADMIN_EMAIL` |
| Nicht unterstütztes Format (z.B. `.docx`) | Antwort-Mail an Absender (CC Admin) mit Hinweis auf erlaubte Formate |
| Mail ohne Anhang | Als SEEN markiert, Log-Eintrag |
| Absender nicht in Whitelist | Als SEEN markiert, ignoriert |
| Webhook-Timeout | Dienst läuft weiter, Fehler wird geloggt |
