from __future__ import annotations

from types import SimpleNamespace

from domain.entities.service_client import ServiceClient
from infrastructure.crypto.hmac_hasher import HmacTokenHasher
from scripts import provision_support_admin_client as provisioner


def test_support_admin_client_has_only_required_scope_and_audience(monkeypatch):
    monkeypatch.setattr(
        provisioner,
        "SecretGenerator",
        lambda: SimpleNamespace(generate=lambda size: "one-time-secret"),
    )

    client, secret = provisioner.build_client("test-pepper")

    assert secret == "one-time-secret"
    assert isinstance(client, ServiceClient)
    assert client.scopes == ["support:admin"]
    assert client.allowed_audiences == ["osap-support"]
    assert client.client_secret_hash == HmacTokenHasher("test-pepper").hash(secret)
    assert client.client_secret_hash != secret


def test_support_admin_client_refuses_empty_pepper():
    try:
        provisioner.build_client("")
    except RuntimeError as exc:
        assert "OSAP_AUTH_TOKEN_PEPPER" in str(exc)
    else:
        raise AssertionError("Debe rechazar una clave HMAC vacía")
