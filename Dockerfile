FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JEV_HFT_HOST=0.0.0.0 \
    JEV_HFT_PORT=8000

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["jev-hft-api"]
