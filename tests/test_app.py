"""HTTP tests for the Flask app."""


def test_index_ok(client) -> None:
    """Home page returns HTML."""
    r = client.get("/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Počasí" in body or "Weather" in body


def test_health_ok(client) -> None:
    """Health endpoint returns JSON."""
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_chat_ok(client) -> None:
    """Chat with stub LLM returns a reply field."""
    r = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hi"}]},
        headers={"X-Locale": "en"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data is not None
    assert "reply" in data
    assert data.get("locale") == "en"


def test_chat_bad_locale(client) -> None:
    """Invalid X-Locale yields 400."""
    r = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hi"}]},
        headers={"X-Locale": "xx"},
    )
    assert r.status_code == 400


def test_chat_bad_messages(client) -> None:
    """Empty messages yields 400."""
    r = client.post("/api/chat", json={"messages": []})
    assert r.status_code == 400
