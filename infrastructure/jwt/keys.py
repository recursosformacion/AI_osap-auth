"""Gestión de claves RSA (privada para firmar, pública para verificar) de osap-auth."""

from __future__ import annotations

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class RsaKeys:
    """Carga las claves RSA a partir de PEM (desde configuración / secrets)."""

    _private_key: rsa.RSAPrivateKey
    _public_key: rsa.RSAPublicKey

    def __init__(self, *, private_key_pem: str, public_key_pem: str) -> None:
        private = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"), password=None
        )
        if not isinstance(private, rsa.RSAPrivateKey):
            raise TypeError("se requiere una clave RSA privada")
        self._private_key = private
        if public_key_pem:
            public = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            if not isinstance(public, rsa.RSAPublicKey):
                raise TypeError("se requiere una clave RSA pública")
            self._public_key = public
        else:
            self._public_key = self._private_key.public_key()

    @property
    def private_key(self) -> rsa.RSAPrivateKey:
        return self._private_key

    @property
    def public_key(self) -> rsa.RSAPublicKey:
        return self._public_key
