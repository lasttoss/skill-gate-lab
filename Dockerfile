# No dependencies, no build stage: the gate is stdlib Python on purpose, so the
# image that runs in CI is the same one that runs on a laptop.
FROM python:3.12-slim

WORKDIR /app
COPY gate ./gate
COPY catalog ./catalog
COPY cases ./cases
COPY fixtures ./fixtures
COPY config ./config
COPY Makefile ./

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python3", "-m", "gate.cli"]
CMD ["gate"]
