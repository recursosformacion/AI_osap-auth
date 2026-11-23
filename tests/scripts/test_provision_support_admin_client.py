from __future__ import annotations

import uuid

import pytest

from domain.entities.service_client import ServiceClient
from infrastructure.crypto.hmac_hasher import HmacTokenHasher
from scripts import provision_support_admin_client as provisioner


CLIENT_ID = "33333333-3333-4333-8333-333333333333"


def test_support_admin_client_is_declarative_and_least_privilege():
    client = provisioner.build_client(CLIENT_ID, "configured-secret", "test-pepper")

    assert isinstance(client, ServiceClient)
    assert client.client_id == uuid.UUID(CLIENT_ID)
    assert client.scopes == ["support:admin"]
    assert client.allowed_audiences == ["osap-support"]
    assert client.enabled is True
    assert client.client_secret_hash == HmacTokenHasher("test-pepper").hash("configured-secret")
    assert client.client_secret_hash != "configured-secret"


@pytest.mark.parametrize(
    ("client_id", "secret", "pepper", "message"),
    [
        ("not-a-uuid", "secret", "pepper", "UUID"),
        (CLIENT_ID, "", "pepper", "OSAP_SUPPORT_ADMIN_CLIENT_SECRET"),
        (CLIENT_ID, "secret", "", "OSAP_AUTH_TOKEN_PEPPER"),
    ],
)
def test_support_admin_client_rejects_invalid_configuration(client_id, secret, pepper, message):
    with pytest.raises(RuntimeError, match=message):
        provisioner.build_client(client_id, secret, pepper)


def test_provision_refuses_production_before_opening_database(monkeypatch):
    from types import SimpleNamespace

    settings = SimpleNamespace(env="production")
    monkeypatch.setattr(provisioner, "load_settings", lambda: settings)
    monkeypatch.setattr(
        provisioner,
        "create_pool",
        lambda **kwargs: pytest.fail("No debe abrir la BD de producción"),
    )

    import asyncio

    with pytest.raises(RuntimeError, match="solo permite Auth de desarrollo"):
        asyncio.run(provisioner.provision(CLIENT_ID, "configured-secret", "osap_auth"))


def test_provision_requires_exact_development_database_confirmation(monkeypatch):
    from types import SimpleNamespace

    settings = SimpleNamespace(
        env="development",
        database=SimpleNamespace(name="osap_auth_dev"),
    )
    monkeypatch.setattr(provisioner, "load_settings", lambda: settings)
    monkeypatch.setattr(
        provisioner,
        "create_pool",
        lambda **kwargs: pytest.fail("No debe abrir una BD sin confirmación exacta"),
    )

    import asyncio

    with pytest.raises(RuntimeError, match="no coincide"):
        asyncio.run(
            provisioner.provision(CLIENT_ID, "configured-secret", "osap_auth_prod")
        )


def test_provision_reconciles_declared_client_in_development(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    settings = SimpleNamespace(
        env="development",
        database=SimpleNamespace(
            name="osap_auth_dev",
            host="127.0.0.1",
            port=3306,
            user="test-user",
            password="test-password",
        ),
        crypto=SimpleNamespace(token_hmac_pepper="test-pepper"),
    )
    saved = {}

    class FakePool:
        def close(self):
            saved["closed"] = True

        async def wait_closed(self):
            saved["waited"] = True

    class FakeRepository:
        def __init__(self, pool):
            saved["pool"] = pool

        async def save(self, client):
            saved["client"] = client

    async def fake_create_pool(**kwargs):
        saved["connection"] = kwargs
        return FakePool()

    monkeypatch.setattr(provisioner, "load_settings", lambda: settings)
    monkeypatch.setattr(provisioner, "create_pool", fake_create_pool)
    monkeypatch.setattr(provisioner, "SqlServiceClientRepository", FakeRepository)

    result = asyncio.run(
        provisioner.provision(CLIENT_ID, "configured-secret", "osap_auth_dev")
    )

    assert result["result"] == "reconciled"
    assert result["database"] == "osap_auth_dev"
    assert saved["client"].client_id == uuid.UUID(CLIENT_ID)
    assert saved["client"].scopes == ["support:admin"]
    assert saved["client"].allowed_audiences == ["osap-support"]
    assert saved["closed"] is True
    assert saved["waited"] is True
