FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN pip install --upgrade pip \
    && pip install poetry \
    && pip install gunicorn \
    && poetry install

EXPOSE 9000
