FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    cups \
    cups-client \
    cups-filters \
    printer-driver-gutenprint \
    libcups2-dev \
    gcc \
    ghostscript \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /var/spool/cups /var/log/cups /etc/cups && \
    echo "ServerName localhost" >> /etc/cups/cupsd.conf && \
    echo "Listen localhost:631" >> /etc/cups/cupsd.conf

RUN mkdir -p /app/data

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
