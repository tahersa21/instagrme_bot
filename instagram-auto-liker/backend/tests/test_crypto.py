import os

os.environ.setdefault("MASTER_KEY", "test-master-key-12345")
os.environ.setdefault("ADMIN_PASSWORD", "x")
os.environ.setdefault("JWT_SECRET", "x")

from app.config import get_settings  # noqa: E402
from app.services import crypto  # noqa: E402


def test_encrypt_decrypt_roundtrip():
    get_settings.cache_clear()
    plaintext = "hello world — مرحبا"
    token = crypto.encrypt(plaintext)
    assert token != plaintext
    assert crypto.decrypt(token) == plaintext


def test_decrypt_wrong_token_raises():
    import pytest

    get_settings.cache_clear()
    with pytest.raises(ValueError):
        crypto.decrypt("not-a-valid-token")
