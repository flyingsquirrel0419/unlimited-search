#!/usr/bin/env sh
set -eu

REPO="${UNLIMITED_SEARCH_REPO:-https://github.com/flyingsquirrel0419/unlimited-search.git}"
HOME_DIR="${UNLIMITED_SEARCH_HOME:-$HOME/.unlimited-search}"
BIN_DIR="${UNLIMITED_SEARCH_BIN:-$HOME/.local/bin}"
BIN="$BIN_DIR/unlimited-search"
ACTION="${1:-install}"

help() {
  cat <<EOF
unlimited-search installer

Usage:
  install.sh [install|update|uninstall|help]

Env:
  UNLIMITED_SEARCH_REPO  Git repo URL. Default: $REPO
  UNLIMITED_SEARCH_HOME  Install dir. Default: $HOME_DIR
  UNLIMITED_SEARCH_BIN   Bin dir. Default: $BIN_DIR

Commands after install:
  unlimited-search serve
  unlimited-search read https://example.com
  unlimited-search update
  unlimited-search uninstall
  unlimited-search help
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

need() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

uv_help() {
  cat >&2 <<'EOF'
uv is required.

Install uv:
  curl -LsSf https://astral.sh/uv/install.sh | sh

Or on macOS:
  brew install uv
EOF
}

write_wrapper() {
  mkdir -p "$BIN_DIR"
  cat > "$BIN" <<EOF
#!/usr/bin/env sh
set -eu
APP_HOME="$HOME_DIR"
cmd="\${1:-help}"
case "\$cmd" in
  serve)
    shift
    exec uv --directory "\$APP_HOME" run unlimited-search serve "\$@"
    ;;
  read)
    shift
    exec uv --directory "\$APP_HOME" run unlimited-search read "\$@"
    ;;
  diagnose)
    shift
    exec uv --directory "\$APP_HOME" run unlimited-search diagnose "\$@"
    ;;
  media)
    shift
    exec uv --directory "\$APP_HOME" run unlimited-search media "\$@"
    ;;
  update)
    exec sh "\$APP_HOME/scripts/install.sh" update
    ;;
  uninstall)
    exec sh "\$APP_HOME/scripts/install.sh" uninstall
    ;;
  help|-h|--help)
    cat <<'EOH'
unlimited-search

Usage:
  unlimited-search serve
  unlimited-search read URL
  unlimited-search diagnose URL
  unlimited-search media URL
  unlimited-search update
  unlimited-search uninstall
  unlimited-search help

MCP config:
  {"mcpServers":{"unlimited-search":{"command":"unlimited-search","args":["serve"]}}}
EOH
    ;;
  *)
    echo "unknown command: \$cmd" >&2
    echo "run: unlimited-search help" >&2
    exit 2
    ;;
esac
EOF
  chmod +x "$BIN"
}

install_app() {
  need git
  command -v uv >/dev/null 2>&1 || { uv_help; exit 1; }
  if [ -d "$HOME_DIR/.git" ]; then
    update_app
    return
  fi
  [ ! -e "$HOME_DIR" ] || die "$HOME_DIR exists but is not a git checkout"
  git clone "$REPO" "$HOME_DIR"
  uv --directory "$HOME_DIR" sync --no-dev
  write_wrapper
  installed_msg
}

update_app() {
  need git
  command -v uv >/dev/null 2>&1 || { uv_help; exit 1; }
  [ -d "$HOME_DIR/.git" ] || die "$HOME_DIR is not installed"
  git -C "$HOME_DIR" pull --ff-only
  uv --directory "$HOME_DIR" sync --no-dev
  write_wrapper
  installed_msg
}

uninstall_app() {
  rm -rf "$HOME_DIR" "$BIN"
  printf 'removed unlimited-search\n'
  printf 'remove it from your MCP client config if needed\n'
}

installed_msg() {
  cat <<EOF
installed unlimited-search

Try:
  unlimited-search read https://example.com

MCP config:
  {"mcpServers":{"unlimited-search":{"command":"unlimited-search","args":["serve"]}}}

If "unlimited-search" is not found, add this to PATH:
  export PATH="$BIN_DIR:\$PATH"
EOF
}

case "$ACTION" in
  install) install_app ;;
  update) update_app ;;
  uninstall) uninstall_app ;;
  help|-h|--help) help ;;
  *) die "unknown action: $ACTION" ;;
esac
