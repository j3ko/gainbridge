from app.services import jobs as jobs_module
from app.services import plex_oauth


def _create_source(client, name="lib", **overrides):
    body = {
        "name": name,
        "type": "plex",
        "base_url": "http://x",
        "token": "t",
        **overrides,
    }
    response = client.post("/api/v1/sources/", json=body)
    assert response.status_code == 200
    return response.json()


# ----- CRUD -----


def test_list_sources_empty(client):
    response = client.get("/api/v1/sources/")
    assert response.status_code == 200
    assert response.json() == []


def test_add_and_list_source(client):
    _create_source(client)
    response = client.get("/api/v1/sources/")
    assert response.status_code == 200
    names = [s["name"] for s in response.json()]
    assert names == ["lib"]


def test_add_source_rejects_bad_path_mapping(client, tmp_path):
    missing = tmp_path / "does-not-exist"
    response = client.post(
        "/api/v1/sources/",
        json={
            "name": "lib",
            "type": "plex",
            "base_url": "http://x",
            "token": "t",
            "path_mappings": [
                {"remote_path": "/data/music", "local_path": str(missing)}
            ],
        },
    )
    assert response.status_code == 422


def test_delete_source(client):
    _create_source(client)
    response = client.delete("/api/v1/sources/lib")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert client.get("/api/v1/sources/").json() == []


def test_delete_source_not_found(client):
    response = client.delete("/api/v1/sources/missing")
    assert response.status_code == 404


# ----- schedule -----


def test_set_schedule(client):
    _create_source(client)
    response = client.put(
        "/api/v1/sources/lib/schedule", json={"schedule_cron": "* * * * *"}
    )
    assert response.status_code == 200
    assert response.json()["schedule_cron"] == "* * * * *"


def test_set_schedule_not_found(client):
    response = client.put(
        "/api/v1/sources/missing/schedule", json={"schedule_cron": "* * * * *"}
    )
    assert response.status_code == 404


def test_set_schedule_invalid_cron(client):
    _create_source(client)
    response = client.put(
        "/api/v1/sources/lib/schedule", json={"schedule_cron": "not a cron"}
    )
    assert response.status_code == 422


def test_clear_schedule(client):
    _create_source(client)
    client.put("/api/v1/sources/lib/schedule", json={"schedule_cron": "* * * * *"})
    response = client.delete("/api/v1/sources/lib/schedule")
    assert response.status_code == 200
    assert response.json()["schedule_cron"] is None


def test_clear_schedule_not_found(client):
    response = client.delete("/api/v1/sources/missing/schedule")
    assert response.status_code == 404


# ----- connection testing -----


class _FakePlexService:
    def __init__(self, base_url, token):
        pass

    def test_connection(self):
        return {"ok": True, "server_name": "My Plex", "version": "1.0"}

    def get_music_libraries(self):
        return [{"id": "1", "name": "Music", "type": "music"}]


class _FailingPlexService:
    def __init__(self, base_url, token):
        pass

    def test_connection(self):
        raise RuntimeError("connection refused")

    def get_music_libraries(self):
        raise RuntimeError("connection refused")


def test_test_source(client, monkeypatch):
    _create_source(client)
    monkeypatch.setattr(jobs_module, "PlexService", _FakePlexService)
    response = client.post("/api/v1/sources/lib/test")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_test_source_not_found(client):
    response = client.post("/api/v1/sources/missing/test")
    assert response.status_code == 404


def test_test_source_connection_failure(client, monkeypatch):
    _create_source(client)
    monkeypatch.setattr(jobs_module, "PlexService", _FailingPlexService)
    response = client.post("/api/v1/sources/lib/test")
    assert response.status_code == 400


def test_test_connection(client, monkeypatch):
    monkeypatch.setattr(jobs_module, "PlexService", _FakePlexService)
    response = client.post(
        "/api/v1/sources/test",
        json={"type": "plex", "base_url": "http://x", "token": "t"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_test_connection_failure(client, monkeypatch):
    monkeypatch.setattr(jobs_module, "PlexService", _FailingPlexService)
    response = client.post(
        "/api/v1/sources/test",
        json={"type": "plex", "base_url": "http://x", "token": "t"},
    )
    assert response.status_code == 400


def test_list_libraries_for_connection(client, monkeypatch):
    monkeypatch.setattr(jobs_module, "PlexService", _FakePlexService)
    response = client.post(
        "/api/v1/sources/libraries",
        json={"type": "plex", "base_url": "http://x", "token": "t"},
    )
    assert response.status_code == 200
    assert response.json() == [{"id": "1", "name": "Music", "type": "music"}]


def test_list_libraries_for_connection_failure(client, monkeypatch):
    monkeypatch.setattr(jobs_module, "PlexService", _FailingPlexService)
    response = client.post(
        "/api/v1/sources/libraries",
        json={"type": "plex", "base_url": "http://x", "token": "t"},
    )
    assert response.status_code == 400


def test_list_libraries_for_source(client, monkeypatch):
    _create_source(client)
    monkeypatch.setattr(jobs_module, "PlexService", _FakePlexService)
    response = client.get("/api/v1/sources/lib/libraries")
    assert response.status_code == 200
    assert response.json() == [{"id": "1", "name": "Music", "type": "music"}]


def test_list_libraries_for_source_not_found(client):
    response = client.get("/api/v1/sources/missing/libraries")
    assert response.status_code == 404


# ----- plex oauth -----


class _FakePinLogin:
    def __init__(self, oauth=True):
        self._id = "123"
        self.token = None
        self._authorized = True

    def oauthUrl(self):
        return "https://app.plex.tv/auth/#!?code=abcd"

    def checkLogin(self):
        self.token = "plex-token"
        return self._authorized


def test_create_plex_pin(client, monkeypatch):
    monkeypatch.setattr(plex_oauth, "MyPlexPinLogin", _FakePinLogin)
    response = client.post("/api/v1/sources/plex/oauth/pin")
    assert response.status_code == 200
    assert response.json() == {
        "id": "123",
        "oauth_url": "https://app.plex.tv/auth/#!?code=abcd",
    }


def test_check_plex_pin(client, monkeypatch):
    monkeypatch.setattr(plex_oauth, "MyPlexPinLogin", _FakePinLogin)
    client.post("/api/v1/sources/plex/oauth/pin")
    response = client.get("/api/v1/sources/plex/oauth/pin/123")
    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "token": "plex-token"}


def test_check_plex_pin_not_found(client):
    response = client.get("/api/v1/sources/plex/oauth/pin/missing")
    assert response.status_code == 404


class _FakeConnection:
    def __init__(self, uri, local):
        self.uri = uri
        self.local = local


class _FakeResource:
    def __init__(self, name, provides, connections):
        self.name = name
        self.provides = provides
        self.connections = connections


class _FakeAccount:
    def __init__(self, token):
        self.token = token

    def resources(self):
        return [
            _FakeResource(
                "My Server",
                "server",
                [_FakeConnection("http://192.168.1.10:32400", True)],
            )
        ]


def test_list_plex_servers(client, monkeypatch):
    monkeypatch.setattr(plex_oauth, "MyPlexAccount", _FakeAccount)
    response = client.get("/api/v1/sources/plex/oauth/servers?token=sometoken")
    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "My Server",
            "connections": [{"uri": "http://192.168.1.10:32400", "local": True}],
        }
    ]


class _FailingAccount:
    def __init__(self, token):
        raise RuntimeError("bad token")


def test_list_plex_servers_failure(client, monkeypatch):
    monkeypatch.setattr(plex_oauth, "MyPlexAccount", _FailingAccount)
    response = client.get("/api/v1/sources/plex/oauth/servers?token=bad")
    assert response.status_code == 400
