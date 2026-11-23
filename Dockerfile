FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=false DJANGO_DB_PATH=/data/db.sqlite3 \
    DJANGO_MEDIA_ROOT=/data/media DJANGO_STATIC_ROOT=/data/static
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 coderr \
    && useradd --uid 10001 --gid coderr --no-create-home coderr \
    && mkdir -p /data/media /data/static \
    && chown -R coderr:coderr /data
COPY --chown=coderr:coderr . .
RUN chmod +x /app/docker-entrypoint.sh
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-tmp-dir", "/tmp", "--access-logfile", "-"]
