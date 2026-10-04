import pytest

from agents import upload_agent


def test_upload_defaults_to_private():
    assert upload_agent.PRIVACY_STATUS == "private"


def test_publish_requires_explicit_human_authorization(monkeypatch):
    monkeypatch.delenv("YOUTUBE_PUBLISH_AUTHORIZED", raising=False)

    with pytest.raises(SystemExit, match="publishing is disabled by default"):
        upload_agent.require_publish_authorization()


def test_unauthorized_main_stops_before_artifact_credentials_and_network(monkeypatch):
    monkeypatch.delenv("YOUTUBE_PUBLISH_AUTHORIZED", raising=False)
    touched = []

    def forbidden(name):
        def _fail(*args, **kwargs):
            touched.append(name)
            raise AssertionError(f"unauthorized path touched {name}")
        return _fail

    monkeypatch.setattr(upload_agent, "find_latest", forbidden("artifact discovery"))
    monkeypatch.setattr(upload_agent, "get_credentials", forbidden("credentials"))
    monkeypatch.setattr(upload_agent, "build", forbidden("YouTube API client"))
    monkeypatch.setattr(upload_agent, "MediaFileUpload", forbidden("network upload setup"))

    with pytest.raises(SystemExit, match="publishing is disabled by default"):
        upload_agent.main()

    assert touched == []
