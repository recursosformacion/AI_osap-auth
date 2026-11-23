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
