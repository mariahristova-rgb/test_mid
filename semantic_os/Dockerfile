FROM zricethezav/gitleaks:v8.24.3 AS credential-scan
COPY backend /scan/backend
RUN gitleaks dir /scan/backend --redact=100 --no-banner && touch /scan-passed

FROM python:3.12-slim
COPY --from=credential-scan /scan-passed /usr/local/share/assistant-secret-scan-passed
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
COPY backend/requirements-messaging.txt /tmp/requirements-messaging.txt
COPY backend/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -c /tmp/requirements.lock -r /tmp/requirements.txt
RUN pip install --no-cache-dir -c /tmp/requirements.lock -r /tmp/requirements-messaging.txt
COPY backend /app/backend
RUN groupadd --gid 10001 assistant && useradd --uid 10001 --gid 10001 --create-home assistant && mkdir /data /backups && chown 10001:10001 /data /backups
ENV ASSISTANT_DATABASE=/data/assistant.sqlite3
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live',timeout=3)"
CMD ["uvicorn", "backend.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
