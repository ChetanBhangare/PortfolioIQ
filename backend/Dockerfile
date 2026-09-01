FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app
COPY requirements-api.txt ./
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements-api.txt \
    && groupadd --system portfolioiq \
    && useradd --system --gid portfolioiq --home-dir /app portfolioiq

COPY --chown=portfolioiq:portfolioiq app ./app
USER portfolioiq

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/health',timeout=3)" || exit 1
CMD ["sh","-c","exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*' --no-access-log"]
