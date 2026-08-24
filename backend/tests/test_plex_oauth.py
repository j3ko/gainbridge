import pytest

from app.services import plex_oauth


@pytest.fixture(autouse=True)
def clear_pending():
    plex_oauth._pending.clear()
    yield
    plex_oauth._pending.clear()


class _FakePinLogin:
    def __init__(self, oauth=True):
        self._id = "123"
        self.token = None
        self._authorized = False

    def oauthUrl(self):
        return "https://app.plex.tv/auth/#!?code=abcd"

    def checkLogin(self):
        if self._authorized:
            self.token = "plex-token"
            return True
        return False


def test_create_pin_returns_id_and_url(monkeypatch):
    monkeypatch.setattr(plex_oauth, "MyPlexPinLogin", _FakePinLogin)
    result = plex_oauth.create_pin()
    assert result == {"id": "123", "oauth_url": "https://app.plex.tv/auth/#!?code=abcd"}
    assert "123" in plex_oauth._pending


def test_check_pin_not_yet_authenticated(monkeypatch):
    monkeypatch.setattr(plex_oauth, "MyPlexPinLogin", _FakePinLogin)
    plex_oauth.create_pin()
    result = plex_oauth.check_pin("123")
    assert result == {"authenticated": False}
    assert "123" in plex_oauth._pending


def test_check_pin_authenticated_pops_entry(monkeypatch):
    monkeypatch.setattr(plex_oauth, "MyPlexPinLogin", _FakePinLogin)
    plex_oauth.create_pin()
    pinlogin, _ = plex_oauth._pending["123"]
    pinlogin._authorized = True

    result = plex_oauth.check_pin("123")
    assert result == {"authenticated": True, "token": "plex-token"}
    assert "123" not in plex_oauth._pending


def test_check_pin_unknown_id_raises_key_error():
    with pytest.raises(KeyError):
        plex_oauth.check_pin("does-not-exist")


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
            ),
            _FakeResource("My Phone", "client,player", []),
            _FakeResource("Empty Server", "server", []),
        ]


def test_list_servers_filters_to_servers_with_connections(monkeypatch):
    monkeypatch.setattr(plex_oauth, "MyPlexAccount", _FakeAccount)
    result = plex_oauth.list_servers("sometoken")
    assert result == [
        {
            "name": "My Server",
            "connections": [{"uri": "http://192.168.1.10:32400", "local": True}],
        }
    ]
