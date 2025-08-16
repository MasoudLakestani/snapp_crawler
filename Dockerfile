FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Configure poetry: Don't create virtual environment, install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy project files
COPY . .

# Create entrypoint script
RUN echo '#!/bin/bash\n\
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