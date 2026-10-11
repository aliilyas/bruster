#!/bin/sh
# Installs the latest bruster release for this OS and CPU into ~/.local/bin
# (or $BRUSTER_INSTALL_DIR). Usage: curl -fsSL https://raw.githubusercontent.com/iliyasalikhojayev/bruster/main/install.sh | sh
set -eu
REPO=iliyasalikhojayev/bruster
DIR=${BRUSTER_INSTALL_DIR:-$HOME/.local/bin}

os=$(uname -s); arch=$(uname -m)
case "$os-$arch" in
  Darwin-arm64)            target=aarch64-apple-darwin ;;
  Darwin-x86_64)           target=x86_64-apple-darwin ;;
  Linux-x86_64)            target=x86_64-unknown-linux-gnu ;;
  Linux-aarch64|Linux-arm64) target=aarch64-unknown-linux-gnu ;;
  *) echo "no prebuilt bruster for $os $arch; build with cargo" >&2; exit 1 ;;
esac

tag=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p')
ver=${tag#v}
url="https://github.com/$REPO/releases/download/$tag/bruster-$ver-$target.tar.gz"
tmp=$(mktemp -d)
curl -fsSL "$url" | tar xz -C "$tmp"
mkdir -p "$DIR"
install -m 755 "$tmp/bruster-$ver-$target/bruster" "$DIR/bruster"
rm -rf "$tmp"
echo "installed bruster $ver to $DIR/bruster"

case "$os" in
  Linux)
    ldd "$DIR/bruster" 2>/dev/null | grep -q 'not found' && echo "missing libraries: install WebKitGTK 4.1 (apt: libwebkit2gtk-4.1-0, apk: webkit2gtk-4.1, dnf: webkit2gtk4.1)" >&2
    command -v xvfb-run >/dev/null || echo "no xvfb-run: without a desktop session install xvfb (apt: xvfb, apk: xvfb-run)" >&2
    ;;
esac
case ":$PATH:" in *":$DIR:"*) ;; *) echo "add $DIR to PATH" >&2 ;; esac
