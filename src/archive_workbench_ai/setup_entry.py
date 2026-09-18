from __future__ import annotations

from .setup_app import serve_setup


def main() -> int:
    return serve_setup(open_browser=True)


if __name__ == "__main__":
    raise SystemExit(main())
