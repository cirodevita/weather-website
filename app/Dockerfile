FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .env .env
COPY config/* config/*
COPY static/ static/
COPY templates/ templates/
COPY models.py models.py
COPY app.py app.py
COPY utils.py utils.py
COPY alert.py alert.py