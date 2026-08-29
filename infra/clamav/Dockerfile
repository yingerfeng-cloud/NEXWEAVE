FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2

ARG CLAMAV_DEBIAN_VERSION=1.4.3+dfsg-1~deb12u2

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        "clamav-daemon=${CLAMAV_DEBIAN_VERSION}" \
        "clamav-freshclam=${CLAMAV_DEBIAN_VERSION}" \
    && rm -rf /var/lib/apt/lists/* \
    && install -d -o clamav -g clamav /run/clamav /var/lib/clamav

COPY infra/clamav/clamd.conf /etc/clamav/clamd.conf
COPY infra/clamav/freshclam.conf /etc/clamav/freshclam.conf
COPY infra/clamav/entrypoint.sh /usr/local/bin/nexweave-clamav-entrypoint.sh
COPY infra/clamav/healthcheck.sh /usr/local/bin/clamdcheck.sh

RUN chmod 0555 \
    /usr/local/bin/nexweave-clamav-entrypoint.sh \
    /usr/local/bin/clamdcheck.sh

EXPOSE 3310
ENTRYPOINT ["/usr/local/bin/nexweave-clamav-entrypoint.sh"]
