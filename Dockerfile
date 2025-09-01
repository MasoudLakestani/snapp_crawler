FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* ./

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry lock && \
    poetry install --no-root

# Copy project files
COPY . .

# Create the entrypoint script based on your working version
RUN echo '#!/bin/bash\n\
echo "Starting Scrapy crawler..."\n\
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