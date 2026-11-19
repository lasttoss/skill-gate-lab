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

# Non-root on purpose: the container writes into a bind-mounted out/ and into a PVC,
# and a root-owned run directory on the host is a bug that costs an hour to diagnose.
RUN useradd --uid 1000 --create-home app && chown -R app:app /app
USER app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python3", "-m", "gate.cli"]
CMD ["gate"]
