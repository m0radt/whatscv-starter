from app.routers import webhooks


def test_search_route_returns_200(client):
    response = client.get("/api/candidates/search")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 0
    assert payload["items"] == []


def test_non_integer_candidate_path_returns_404(client):
    response = client.get("/api/candidates/not-a-number")

    assert response.status_code == 404


def test_webhook_accepts_form_payload(client, monkeypatch):
    monkeypatch.setattr(
        webhooks,
        "extract_structured",
        lambda paragraph, cv_text=None: {
            "full_name": "Test Candidate",
            "id_number": "1234567890",
            "experiences": [],
        },
    )

    response = client.post(
        "/webhooks/twilio",
        data={"Body": "hello from test", "From": "+1000000000"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert isinstance(body["candidate_id"], int)

    search_response = client.get("/api/candidates/search")
    assert search_response.status_code == 200
    search_body = search_response.json()
    assert search_body["count"] == 1
    assert search_body["items"][0]["phone"] == "+1000000000"
