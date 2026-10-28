# syntax=docker/dockerfile:1

ARG RUST_VERSION=1.90.0
FROM rust:${RUST_VERSION}-slim-bookworm AS build

RUN apt-get update \
    && apt-get install -y --no-install-recommends dbus-x11 libwebkit2gtk-4.1-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY Cargo.toml Cargo.lock ./
COPY src/ ./src/

ARG TARGETARCH
ARG CARGO_BUILD_JOBS=2
RUN --mount=type=cache,target=/usr/local/cargo/registry,sharing=locked \
    --mount=type=cache,id=bruster-target-${TARGETARCH},target=/build/target,sharing=locked \
    cargo build --release --locked --bin bruster --jobs "${CARGO_BUILD_JOBS}" \
    && install -Dm755 target/release/bruster /out/bruster

FROM debian:bookworm-slim AS runtime

LABEL org.opencontainers.image.title="Bruster" \
    org.opencontainers.image.description="Native WebKitGTK browser automation over stdio MCP" \
    org.opencontainers.image.source="https://github.com/aliilyas/bruster" \
    org.opencontainers.image.licenses="MIT"

# Xvfb supplies the display WebKitGTK needs, including in hidden/MCP mode.
# --no-install-recommends avoids desktop applications and development tools.
# dbus-x11 satisfies the session-bus dependency without pulling in systemd.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        dbus-x11 \
        fonts-dejavu-core \
        fonts-liberation \
        libwebkit2gtk-4.1-0 \
        tini \
        xauth \
        xvfb \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 bruster \
    && useradd --uid 10001 --gid bruster --create-home --shell /usr/sbin/nologin bruster \
    && install -d -m 0700 -o bruster -g bruster /run/bruster

COPY --from=build /out/bruster /usr/local/bin/bruster
COPY LICENSE /usr/share/doc/bruster/LICENSE

# Docker's default seccomp profile prevents WebKit's nested user namespaces.
# Use the container boundary and a non-root user without privileged flags.
ENV HOME=/home/bruster \
    XDG_RUNTIME_DIR=/run/bruster \
    GDK_BACKEND=x11 \
    WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1

USER 10001:10001
WORKDIR /home/bruster

# Bruster starts Xvfb automatically. Tini forwards signals to its process group
# and reaps orphaned browser helpers; stdout stays exclusively MCP JSON-RPC.
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/bruster"]
CMD ["--mcp"]
