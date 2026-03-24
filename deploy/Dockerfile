FROM python:3.11.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Create non-root user
RUN addgroup --system django && adduser --system --ingroup django django

# Create directories and set ownership BEFORE switching user
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R django:django /app

RUN chmod +x /app/deploy/entrypoint.sh

# Switch to non-root user
USER django

EXPOSE 8000

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "3", \
    "--threads", "2", \
    "--access-logfile", "-", \
    "--error-logfile", "-"]