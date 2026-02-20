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
    async def fake_download(media_id, dest):
        dest.write_bytes(b"%PDF-1.4 fake")
    async def fake_send(to, text):
        return True

    monkeypatch.setattr(
        webhooks,
        "_download_whatsapp_cloud_media",
        fake_download,
    )
    monkeypatch.setattr(webhooks, "extract_text", lambda _: "fake cv text")
    monkeypatch.setattr(
        webhooks,
        "extract_structured",
        lambda paragraph, cv_text=None: {"full_name": "Test Candidate", "id_number": "1234567890", "experiences": []},
    )
    monkeypatch.setattr(webhooks, "_send_whatsapp_cloud_text", fake_send)

    response = client.post(
        "/webhooks/whatsapp-cloud",
        json={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.test.1",
                                        "from": "+1000000000",
                                        "type": "document",
                                        "document": {"id": "media-1", "filename": "cv.pdf"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["action"] == "created"
    assert isinstance(body["candidate_id"], int)

    search_response = client.get("/api/candidates/search")
    assert search_response.status_code == 200
    search_body = search_response.json()
    assert search_body["count"] == 1
    assert search_body["items"][0]["phone"] == "+1000000000"
