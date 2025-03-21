FROM python:3.9-slim

RUN apt-get update && apt-get install -y nginx supervisor && rm -rf /var/lib/apt/lists/*


RUN mkdir -p /run/nginx

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80

CMD ["supervisord", "-c", "/app/supervisord.conf"]
