FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["sh", "-c", "gunicorn render_app:app --bind 0.0.0.0:${PORT:-10000} --workers ${WEB_CONCURRENCY:-1} --worker-class uvicorn.workers.UvicornWorker --access-logfile - --error-logfile -"]
