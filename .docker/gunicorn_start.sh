#!/bin/sh

gunicorn \
  --worker-tmp-dir /dev/shm \
  --bind :8000 \
  --workers 2 \
  --threads 4 \
  --worker-class gthread \
  project.wsgi:application