"""Helper to generate strong random keys for `.env`.

Usage:
    python scripts/generate_keys.py
"""

import secrets


def main() -> None:
    print("# Paste these into your .env file:\n")
    print(f"MASTER_KEY={secrets.token_urlsafe(48)}")
    print(f"JWT_SECRET={secrets.token_urlsafe(48)}")
    print(f"ADMIN_PASSWORD={secrets.token_urlsafe(16)}")


if __name__ == "__main__":
    main()
