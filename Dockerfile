# R 4.5.0, immutable multi-platform image index. Validated target: linux/amd64.
FROM rocker/r-ver:4.5.0@sha256:f97b4944221bdc309583dfbc37dc0bf2654cfbd1f330cded047aeec4ae5df7e3 AS system
# Optional build-only CA supports proxied cloud builds without baking it in.
RUN --mount=type=secret,id=proxy_ca \
    touch /tmp/algss2-apt.conf && \
    if [ -s /run/secrets/proxy_ca ]; then \
      printf 'Acquire::https::CaInfo "/run/secrets/proxy_ca";\n' > /tmp/algss2-apt.conf; \
    fi && \
    apt-get -c /tmp/algss2-apt.conf update && \
    apt-get -c /tmp/algss2-apt.conf upgrade -y --no-install-recommends && \
    apt-get -c /tmp/algss2-apt.conf install -y --no-install-recommends \
      ca-certificates libcurl4t64 libssl3t64 libxml2 libicu74 zlib1g tini && \
    rm -rf /var/lib/apt/lists/* /tmp/algss2-apt.conf

FROM system AS dependencies
RUN --mount=type=secret,id=proxy_ca \
    touch /tmp/algss2-apt.conf && \
    if [ -s /run/secrets/proxy_ca ]; then \
      printf 'Acquire::https::CaInfo "/run/secrets/proxy_ca";\n' > /tmp/algss2-apt.conf; \
    fi && \
    apt-get -c /tmp/algss2-apt.conf update && \
    apt-get -c /tmp/algss2-apt.conf install -y --no-install-recommends \
      libcurl4-openssl-dev libssl-dev libxml2-dev libicu-dev zlib1g-dev pkg-config && \
    rm -rf /var/lib/apt/lists/* /tmp/algss2-apt.conf
WORKDIR /build
ENV R_LIBS_USER=/opt/algss2/library
COPY scripts/setup.R scripts/dependencies.R scripts/package-versions.R scripts/source-integrity.R scripts/source-lock.tsv scripts/
RUN --mount=type=secret,id=proxy_ca \
    Rscript --vanilla -e 'if (file.exists("/run/secrets/proxy_ca")) Sys.setenv(CURL_CA_BUNDLE="/run/secrets/proxy_ca"); source("scripts/setup.R")'

FROM system AS runtime
ARG VCS_REF=unknown
LABEL org.opencontainers.image.source="https://github.com/goatcheese98/algss2_clusterapp" \
      org.opencontainers.image.revision="$VCS_REF"
RUN groupadd --gid 10001 shiny && \
    useradd --uid 10001 --gid 10001 --create-home --home-dir /home/shiny --shell /usr/sbin/nologin shiny
WORKDIR /opt/algss2/app
COPY --from=dependencies /opt/algss2/library /opt/algss2/library
COPY app.R ./
COPY R/ R/
COPY data/ALGS_Split_2.csv data/
COPY www/ www/
COPY scripts/start.R scripts/health.R scripts/package-versions.R scripts/dependencies.R scripts/source-lock.tsv scripts/
RUN chmod -R a=rX /opt/algss2
ENV R_LIBS_USER=/opt/algss2/library HOME=/home/shiny XDG_CACHE_HOME=/tmp/algss2-cache PORT=3838
USER 10001:10001
EXPOSE 3838
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["Rscript", "--vanilla", "scripts/health.R"]
ENTRYPOINT ["/usr/bin/tini", "--", "Rscript", "--vanilla", "scripts/start.R"]
