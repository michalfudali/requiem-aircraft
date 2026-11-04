# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080 \
    BIPOL_AIRCRAFT_DB=/var/lib/bipol/aircraft.sqlite3 \n    BIPOL_PROJECTS_DB=/var/lib/bipol/projects.sqlite3
WORKDIR /app

COPY requirements.txt requirements-production.txt ./
# The optional CA is only for managed build environments; it is not stored in the image.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir -r requirements-production.txt

RUN groupadd --gid 10001 bipol \
    && useradd --uid 10001 --gid bipol --no-create-home bipol \
    && mkdir -p /var/lib/bipol \
    && chown bipol:bipol /var/lib/bipol
COPY app.py production.py gunicorn.conf.py bipol_topics_list.txt LICENSE ./
COPY calculations/ ./calculations/
COPY data/ ./data/
COPY static/ ./static/
COPY templates/ ./templates/
RUN chmod -R a+rX /app

USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/healthz', timeout=3)"
CMD ["python", "production.py"]
