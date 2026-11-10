"""Tests de entidades y pertenencias con aprobación del gestor."""

from __future__ import annotations

from fastapi.testclient import TestClient

from application.context import AuthContext

TERMS = "2026-10-01"
PRIVACY = "2026-10-01"


def _login(app: TestClient, email: str, password: str = "s3cret-password") -> str:
    reg = app.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201, reg.text
    token = reg.json().get("verification_token")
    if token:
        app.post("/auth/verify-email", json={"token": token})
    r = app.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _onboard(
    app: TestClient,
    token: str,
    nickname: str,
    *,
    entity_id: str | None = None,
    entity_name: str | None = None,
    entity_kind: str | None = None,
) -> object:
    payload: dict[str, object] = {
        "nickname": nickname,
        "terms_version": TERMS,
        "privacy_version": PRIVACY,
    }
    if entity_id is not None:
        payload["entity_id"] = entity_id
    if entity_name is not None:
        payload["entity_name"] = entity_name
    if entity_kind is not None:
        payload["entity_kind"] = entity_kind
    return app.post("/auth/onboarding", json=payload, headers=_auth(token))


def _create_entity(
    app: TestClient, token: str, name: str = "Coral Aurora", nickname: str = "gestor"
) -> dict[str, object]:
    r = _onboard(app, token, nickname, entity_name=name, entity_kind="coral")
    assert r.status_code == 200, r.text
    return r.json()["memberships"][0]


def _requests(app: TestClient, token: str) -> list[dict[str, object]]:
    r = app.get("/auth/me/entity-requests", headers=_auth(token))
    assert r.status_code == 200, r.text
    return r.json()


def _decide(app: TestClient, token: str, membership_id: str, action: str) -> object:
    return app.post(
        f"/auth/me/entity-requests/{membership_id}/decision",
        json={"action": action},
        headers=_auth(token),
    )


def _email_kinds(ctx: AuthContext) -> list[str]:
    sender = ctx.email_sender
    sent = getattr(sender, "sent", [])
    return [str(message.context.get("kind")) for message in sent]


def test_onboarding_represent_creates_approved_membership(app: TestClient) -> None:
    token = _login(app, "represent@example.com")
    membership = _create_entity(app, token)

    assert membership["entity_name"] == "Coral Aurora"
    assert membership["entity_kind"] == "coral"
    assert membership["status"] == "approved"
    assert membership["is_representative"] is True


def test_list_entities_requires_auth_and_lists(app: TestClient) -> None:
    assert app.get("/auth/entities").status_code == 401

    token = _login(app, "list@example.com")
    membership = _create_entity(app, token, "Orquesta Sinfónica")

    r = app.get("/auth/entities", headers=_auth(token))
    assert r.status_code == 200, r.text
    assert r.json() == [
        {"id": membership["entity_id"], "name": "Orquesta Sinfónica", "kind": "coral"}
    ]


def test_join_is_pending_and_notifies_manager(
    app: TestClient, ctx: AuthContext
) -> None:
    manager = _login(app, "manager@example.com")
    entity = _create_entity(app, manager, "Coral Aurora")

    member = _login(app, "member@example.com")
    r = _onboard(app, member, "miembro", entity_id=str(entity["entity_id"]))
    assert r.status_code == 200, r.text
    membership = r.json()["memberships"][0]
    assert membership["status"] == "pending"
    assert membership["is_representative"] is False

    requests = _requests(app, manager)
    assert len(requests) == 1
    assert requests[0]["nickname"] == "miembro"
    assert requests[0]["entity_name"] == "Coral Aurora"
    assert "membership_request" in _email_kinds(ctx)


def test_manager_approves_request_and_user_is_notified(
    app: TestClient, ctx: AuthContext
) -> None:
    manager = _login(app, "manager-approve@example.com")
    entity = _create_entity(app, manager, "Coral Aurora")

    member = _login(app, "member-approve@example.com")
    assert _onboard(app, member, "aprobado", entity_id=str(entity["entity_id"])).status_code == 200
    request_id = _requests(app, manager)[0]["id"]

    decided = _decide(app, manager, str(request_id), "approve")
    assert decided.status_code == 200, decided.text
    assert _requests(app, manager) == []

    me = app.get("/auth/me", headers=_auth(member)).json()
    assert me["memberships"][0]["status"] == "approved"
    assert "membership_approved" in _email_kinds(ctx)


def test_manager_rejects_request(app: TestClient, ctx: AuthContext) -> None:
    manager = _login(app, "manager-reject@example.com")
    entity = _create_entity(app, manager, "Coral Rechazo")

    member = _login(app, "member-reject@example.com")
    assert _onboard(app, member, "rechazado", entity_id=str(entity["entity_id"])).status_code == 200
    request_id = _requests(app, manager)[0]["id"]

    decided = _decide(app, manager, str(request_id), "reject")
    assert decided.status_code == 200, decided.text

    me = app.get("/auth/me", headers=_auth(member)).json()
    assert me["memberships"][0]["status"] == "rejected"
    assert "membership_rejected" in _email_kinds(ctx)


def test_non_manager_cannot_decide(app: TestClient) -> None:
    manager = _login(app, "manager-owner@example.com")
    entity = _create_entity(app, manager, "Coral Privada")

    member = _login(app, "member-intruder@example.com")
    assert _onboard(app, member, "miembro2", entity_id=str(entity["entity_id"])).status_code == 200
    request_id = _requests(app, manager)[0]["id"]

    intruder = _login(app, "intruder@example.com")
    r = _decide(app, intruder, str(request_id), "approve")
    assert r.status_code == 403


def test_user_can_request_multiple_entities_independently(app: TestClient) -> None:
    manager_a = _login(app, "manager-a@example.com")
    entity_a = _create_entity(app, manager_a, "Coral A")

    manager_b = _login(app, "manager-b@example.com")
    entity_b = _create_entity(app, manager_b, "Orquesta B", nickname="gestor-b")

    user = _login(app, "multi@example.com")
    assert _onboard(app, user, "multi").status_code == 200

    for entity in (entity_a, entity_b):
        r = app.put(
            "/auth/me/entity",
            json={"action": "join", "entity_id": entity["entity_id"]},
            headers=_auth(user),
        )
        assert r.status_code == 200, r.text

    memberships = app.get("/auth/me", headers=_auth(user)).json()["memberships"]
    assert len(memberships) == 2
    assert {m["status"] for m in memberships} == {"pending"}

    request_a = _requests(app, manager_a)[0]
    assert _decide(app, manager_a, str(request_a["id"]), "approve").status_code == 200

    memberships = app.get("/auth/me", headers=_auth(user)).json()["memberships"]
    states = {m["entity_name"]: m["status"] for m in memberships}
    assert states == {"Coral A": "approved", "Orquesta B": "pending"}

    left = app.put(
        "/auth/me/entity",
        json={"action": "leave", "entity_id": entity_a["entity_id"]},
        headers=_auth(user),
    )
    assert left.status_code == 200, left.text
    remaining = left.json()["memberships"]
    assert len(remaining) == 1
    assert remaining[0]["entity_name"] == "Orquesta B"
    assert remaining[0]["status"] == "pending"


def test_duplicate_join_is_idempotent(app: TestClient) -> None:
    manager = _login(app, "manager-idem@example.com")
    entity = _create_entity(app, manager, "Coral Idempotente")

    user = _login(app, "idem@example.com")
    assert _onboard(app, user, "idem").status_code == 200
    for _ in range(2):
        r = app.put(
            "/auth/me/entity",
            json={"action": "join", "entity_id": entity["entity_id"]},
            headers=_auth(user),
        )
        assert r.status_code == 200, r.text

    memberships = app.get("/auth/me", headers=_auth(user)).json()["memberships"]
    assert len(memberships) == 1


def test_represent_renames_own_entity(app: TestClient) -> None:
    token = _login(app, "rename@example.com")
    membership = _create_entity(app, token, "Coral Vella")

    renamed = app.put(
        "/auth/me/entity",
        json={
            "action": "represent",
            "entity_id": membership["entity_id"],
            "entity_name": "Coral Nova",
        },
        headers=_auth(token),
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["memberships"][0]["entity_name"] == "Coral Nova"
    assert renamed.json()["memberships"][0]["entity_kind"] == "coral"


def test_duplicate_entity_name_is_409(app: TestClient) -> None:
    first = _login(app, "first-entity@example.com")
    assert _create_entity(app, first, "Coral Duplicada")

    second = _login(app, "second-entity@example.com")
    r = _onboard(
        app, second, "segundo", entity_name="coral duplicada", entity_kind="coral"
    )
    assert r.status_code == 409


def test_invalid_entity_kind_is_422(app: TestClient) -> None:
    token = _login(app, "badkind@example.com")
    r = _onboard(app, token, "malo", entity_name="Coral X", entity_kind="banda")
    assert r.status_code == 422


def test_entity_name_and_membership_conflict_is_422(app: TestClient) -> None:
    owner = _login(app, "conflict-owner@example.com")
    entity = _create_entity(app, owner)

    token = _login(app, "conflict@example.com")
    r = _onboard(
        app,
        token,
        "conflicto",
        entity_id=str(entity["entity_id"]),
        entity_name="Coral Nueva",
        entity_kind="coral",
    )
    assert r.status_code == 422
