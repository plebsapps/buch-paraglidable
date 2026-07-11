# Web layer container (stage D2): FastAPI + Uvicorn on Python 3.11.
# Separate from the frozen legacy image (docker/Dockerfile, stage A1) --
# this is the first service of the target compose architecture
# (docs/plan.md). Image digest-pinned like everything else (stage B).
FROM python:3.11-slim@sha256:e031123e3d85762b141ad1cbc56452ba69c6e722ebf2f042cc0dc86c47c0d8b3

COPY web/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
