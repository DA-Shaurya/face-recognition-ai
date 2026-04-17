FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for PostgreSQL and OpenCV
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The code will be mounted via docker-compose volume for development
COPY . .

CMD ["python", "app.py"]
