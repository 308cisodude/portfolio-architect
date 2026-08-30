FROM python:3.14.6-alpine3.24@sha256:26730869004e2b9c4b9ad09cab8625e81d256d1ce97e72df5520e806b1709f92

ARG BUILD_VERSION=1.60.0
ARG BUILD_ARCH
ARG APP_UID=65532
ARG APP_GID=65532

RUN apk add --no-cache openssl \
    && addgroup -S -g "${APP_GID}" portfolio \
    && adduser -S -D -H -u "${APP_UID}" -G portfolio portfolio

WORKDIR /app
COPY src/ /app/src/
COPY requirements.txt /tmp/requirements.txt
COPY entrypoint.py /entrypoint.py

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

RUN /usr/local/bin/python3.14 -m pip install \
      --disable-pip-version-check \
      --no-cache-dir \
      --require-hashes \
      --only-binary=:all: \
      --no-deps \
      -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}" \
    org.opencontainers.image.title="Portfolio Architect Provider Gateway" \
    org.opencontainers.image.description="Isolated read-only provider Gateway shell for Portfolio Architect" \
    org.opencontainers.image.licenses="MIT"

RUN /usr/local/bin/python3.14 -c \
    "import encodings, json, ssl, pypdf; import portfolio_architect_gateway.trade_republic_app"

ENTRYPOINT ["/usr/local/bin/python3.14", "/entrypoint.py"]
