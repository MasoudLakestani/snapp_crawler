FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    tor \
    privoxy \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* ./

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry lock && \
    poetry install --no-root

RUN echo "ControlPort 9051" >> /etc/tor/torrc && \
    echo "CookieAuthentication 0" >> /etc/tor/torrc

RUN echo "forward-socks5t / 127.0.0.1:9050 ." >> /etc/privoxy/config

EXPOSE 9050 8118

# Copy project files
COPY . .

# Create entrypoint script that starts services
RUN echo '#!/bin/bash\n\
# Start Tor in the background\n\
tor &\n\
\n\
# Start Privoxy in the background\n\
privoxy --no-daemon /etc/privoxy/config &\n\
\n\
# Wait a moment for services to start\n\
sleep 5\n\
\n\
# Test connections\n\
echo "Testing Tor connection..."\n\
curl --connect-timeout 10 --socks5 127.0.0.1:9050 https://httpbin.org/ip || echo "Tor connection failed"\n\
\n\
echo "Testing Privoxy connection..."\n\
curl --connect-timeout 10 --proxy http://127.0.0.1:8118 https://httpbin.org/ip || echo "Privoxy connection failed"\n\
\n\
if [ "$SPIDER_NAME" = "snappNewProduct" ]; then\n\
    cd /app/snapp && scrapy crawl snappNewProduct\n\
elif [ "$SPIDER_NAME" = "snappProduct" ]; then\n\
    cd /app/snapp && scrapy crawl snappProduct\n\
else\n\
    echo "Please set SPIDER_NAME environment variable to either snappNewProduct or snappProduct"\n\
    exit 1\n\
fi' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]