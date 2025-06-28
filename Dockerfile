FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt requirements.txt

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

CMD ["bash"]