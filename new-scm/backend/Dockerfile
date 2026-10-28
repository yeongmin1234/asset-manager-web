FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/new-scm
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN mkdir -p /srv/new-scm/logs /srv/new-scm/db-socket \
    && chown -R 10001:10001 /srv/new-scm \
    && chmod 700 /srv/new-scm/db-socket
USER 10001:10001
EXPOSE 8012
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8012", "--timeout-keep-alive", "5", "--no-access-log"]
