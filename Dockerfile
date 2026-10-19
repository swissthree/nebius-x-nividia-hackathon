# Meeting-to-Actions — production image (also used for the Nebius Serverless Endpoint)
# Build for the cloud from any machine (incl. Apple Silicon):
#   docker build --platform linux/amd64 -t meeting-to-actions .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /srv

COPY requirements.txt .
# Runtime deps only — pytest/httpx are for development
RUN grep -vE "^(pytest|httpx)" requirements.txt > requirements.prod.txt \
 && pip install -r requirements.prod.txt

COPY app ./app
COPY samples ./samples
# Pre-recorded replies for the sample transcripts (see DEPLOY.md) — with LLM_CACHE=1 the demo
# samples answer instantly and identically on judging day, without spending credits.
COPY demo_cache ./.cache/llm

# Run as an unprivileged user; the response cache must stay writable
RUN useradd --create-home --uid 1000 appuser && chown -R appuser /srv/.cache
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health', timeout=4)"

# --proxy-headers so rate limiting sees the real client IP behind the endpoint's HTTPS proxy
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
