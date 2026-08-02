FROM python:3.14.6-alpine3.24@sha256:26730869004e2b9c4b9ad09cab8625e81d256d1ce97e72df5520e806b1709f92

ARG APP_UID=65532
ARG APP_GID=65532

RUN addgroup -S -g "${APP_GID}" portfolio \
    && adduser -S -D -H -u "${APP_UID}" -G portfolio portfolio

WORKDIR /app
COPY --chown=portfolio:portfolio src/ /app/src/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

USER portfolio:portfolio
ENTRYPOINT ["python", "-m", "portfolio_architect_gateway"]
CMD ["--config", "/config/gateway.toml", "serve"]
