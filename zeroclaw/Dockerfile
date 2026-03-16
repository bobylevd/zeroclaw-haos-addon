ARG BUILD_FROM=debian:trixie-slim
FROM ${BUILD_FROM}

ARG BUILD_ARCH
ARG ZEROCLAW_VERSION=v0.1.7

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl tar python3 jq \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    build_arch="${BUILD_ARCH:-}"; \
    if [ -z "${build_arch}" ]; then \
        build_arch="$(uname -m)"; \
    fi; \
    case "${build_arch}" in \
        aarch64|arm64) target="aarch64-unknown-linux-gnu" ;; \
        x86_64|amd64) target="x86_64-unknown-linux-gnu" ;; \
        *) echo "Unsupported BUILD_ARCH: ${build_arch}" >&2; exit 1 ;; \
    esac; \
    archive_url="https://github.com/zeroclaw-labs/zeroclaw/releases/download/${ZEROCLAW_VERSION}/zeroclaw-${target}.tar.gz"; \
    tmp_dir="$(mktemp -d)"; \
    curl -fsSL "${archive_url}" -o "${tmp_dir}/zeroclaw.tar.gz"; \
    tar -xzf "${tmp_dir}/zeroclaw.tar.gz" -C "${tmp_dir}"; \
    install -m 0755 "${tmp_dir}/zeroclaw" /usr/local/bin/zeroclaw; \
    rm -rf "${tmp_dir}"

RUN mkdir -p /opt/zeroclaw/skills/homeassistant

COPY run.sh /run.sh
COPY ha_api /usr/local/bin/ha_api
COPY seed_workspace.py /usr/local/bin/seed_workspace
COPY generate_config.py /usr/local/bin/generate_config
COPY skills/homeassistant/SKILL.md /opt/zeroclaw/skills/homeassistant/SKILL.md

RUN chmod 0755 /run.sh /usr/local/bin/ha_api /usr/local/bin/seed_workspace /usr/local/bin/generate_config

ENTRYPOINT ["/run.sh"]
CMD ["zeroclaw"]
