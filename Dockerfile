FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_STATE_PATH=/app/data/learning-app.sqlite3 \
    VAULT_PATH=/vault

WORKDIR /app

COPY index.html live.js server.py manifest.webmanifest ./
COPY assets/saketh-learning-icon.png ./assets/

RUN mkdir -p /app/data

EXPOSE 8768

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import json, urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8768/health'))['status'] == 'ok'"

CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8768", "--vault", "/vault", "--state", "/app/data/learning-app.sqlite3"]
