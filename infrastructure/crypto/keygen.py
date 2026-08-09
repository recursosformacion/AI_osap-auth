"""Generación de claves criptográficas para osap-auth.

Uso: `python -m infrastructure.crypto.keygen`

Genera e imprime (a stdout) los valores que debes colocar en las variables de entorno:
  OSAP_AUTH_EMAIL_PEPPER
  OSAP_AUTH_EMAIL_AEAD_KEY   (base64url, 32 bytes)
  OSAP_AUTH_TOKEN_PEPPER
  OSAP_AUTH_JWT_PRIVATE_KEY  (PEM PKCS8)
  OSAP_AUTH_JWT_PUBLIC_KEY   (PEM)
"""

from __future__ import annotations

import base64
import secrets

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main() -> None:
    email_pepper = secrets.token_urlsafe(48)
    email_aead_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    token_pepper = secrets.token_urlsafe(48)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwt_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    jwt_public = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    print("OSAP_AUTH_EMAIL_PEPPER=", email_pepper)
    print("OSAP_AUTH_EMAIL_AEAD_KEY=", email_aead_key)
    print("OSAP_AUTH_TOKEN_PEPPER=", token_pepper)
    print("OSAP_AUTH_JWT_PRIVATE_KEY=", jwt_private.replace("\n", "\\n"))
    print("OSAP_AUTH_JWT_PUBLIC_KEY=", jwt_public.replace("\n", "\\n"))


if __name__ == "__main__":
    main()
