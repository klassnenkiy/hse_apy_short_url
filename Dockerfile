FROM python:3.9-slim

RUN apt-get update && apt-get install -y nginx supervisor \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /run/nginx

WORKDIR /app

COPY . /app
COPY nginx.conf /app/nginx.conf
COPY supervisord.conf /app/supervisord.conf

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80 8502

CMD ["supervisord", "-c", "/app/supervisord.conf"]
