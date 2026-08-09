"""Tests de criptografía: Argon2, cifrado AEAD, HMAC lookup y generación de secretos."""

from __future__ import annotations

from infrastructure.crypto.aes_gcm import AesGcmEmailProtector
from infrastructure.crypto.argon2_hasher import Argon2PasswordHasher, Argon2TokenHasher
from infrastructure.crypto.secrets import SecretGenerator


def test_password_argon2id_irreversible() -> None:
    hasher = Argon2PasswordHasher()
    h = hasher.hash("s3cret-password")
    assert h != "s3cret-password"
    assert hasher.verify("s3cret-password", h)
    assert not hasher.verify("wrong", h)


def test_token_hash() -> None:
    hasher = Argon2TokenHasher()
    token = "raw-opaque-token"
    h = hasher.hash(token)
    assert hasher.verify(token, h)
    assert not hasher.verify("other", h)


def test_email_lookup_deterministic_and_normalized() -> None:
    protector = AesGcmEmailProtector(
        aead_key_b64="QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=", pepper="pepper"
    )
    assert protector.lookup("User@Gmail.com") == protector.lookup("user@gmail.com")
    assert protector.lookup("a@b.com") != protector.lookup("other@b.com")


def test_email_encrypt_decrypt_roundtrip() -> None:
    protector = AesGcmEmailProtector(
        aead_key_b64="QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=", pepper="pepper"
    )
    cipher = protector.encrypt("user@example.com")
    assert isinstance(cipher, bytes)
    assert protector.decrypt(cipher) == "user@example.com"
    assert cipher != b"user@example.com"


def test_secret_generator_high_entropy() -> None:
    gen = SecretGenerator()
    a = gen.generate(32)
    b = gen.generate(32)
    assert a != b
    assert len(a) >= 32
