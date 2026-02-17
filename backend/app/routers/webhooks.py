import os
import pathlib
import json
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..extract.cv_text import extract_text
from ..extract.llm import extract_structured
from ..models import Candidate, Education, Experience
from ..security import hash_sensitive
import httpx

router = APIRouter()
DATA_DIR = pathlib.Path("data/uploads")
DATA_DIR.mkdir(parents=True, exist_ok=True)

async def _download_media(url: str, dest: pathlib.Path) -> None:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)


async def _download_whatsapp_cloud_media(media_id: str, dest: pathlib.Path) -> None:
    token = os.getenv("CLOUDAPI_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="CLOUDAPI_TOKEN is not set")

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        meta = await client.get(f"https://graph.facebook.com/v21.0/{media_id}", headers=headers)
        meta.raise_for_status()
        media_url = meta.json().get("url")
        if not media_url:
            raise HTTPException(status_code=400, detail="WhatsApp media URL not found")

        blob = await client.get(media_url, headers=headers)
        blob.raise_for_status()
        dest.write_bytes(blob.content)


def _persist_candidate(fields: Dict[str, Any], body: str, phone: str | None, cv_text: str) -> int:
    education_items = fields.get("education", []) or []

    db: Session = SessionLocal()
    try:
        cand = Candidate(
            phone=fields.get("phone") or phone,
            email=fields.get("email"),
            full_name=fields.get("full_name"),
            id_number_hash=hash_sensitive(fields.get("id_number")),
            location_city=fields.get("location_city"),
            raw_paragraph=body,
            cv_text=cv_text,
        )
        db.add(cand)
        db.flush()

        for edu in education_items:
            db.add(Education(
                candidate_id=cand.id,
                institution=edu.get("institution"),
                degree=edu.get("degree"),
                major=edu.get("major"),
                gpa=edu.get("gpa"),
                status=edu.get("status"),
                expected_graduation_date=edu.get("expected_graduation_date"),
            ))

        for exp in fields.get("experiences", []) or []:
            db.add(Experience(
                candidate_id=cand.id,
                company=exp.get("company") or exp.get("organization"),
                title=exp.get("title"),
                dates=exp.get("dates"),
                employment_status=exp.get("employment_status"),
                description=exp.get("description"),
            ))
        db.commit()
        return cand.id
    finally:
        db.close()

@router.post("/twilio")
async def twilio_webhook(request: Request) -> Dict[str, Any]:
    """
    Generic webhook for Twilio Conversations/WhatsApp. Expects JSON events
    where message body is available, and media URLs if attachments exist.
    This route is intentionally permissive to simplify first run—add signature
    verification and IP allowlists before production.
    """
    payload: Dict[str, Any] = {}
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            payload = {}
    else:
        form = await request.form()
        payload = dict(form)

    # Try to read a message body and sender phone; adapt mapping as needed
    body = (payload.get("Body") or payload.get("body") or "").strip()
    phone = payload.get("From") or payload.get("from")

    # Media handling (Twilio Conversations example: payload["media"]) – adapt keys
    media_url = None
    media = payload.get("media")
    if isinstance(media, list) and media:
        media_url = media[0].get("url")

    cv_path = None
    if media_url:
        filename = (payload.get("media")[0].get("filename") or "attachment")
        cv_path = DATA_DIR / filename
        try:
            await _download_media(media_url, cv_path)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=400, detail=f"Unable to download CV from URL: {exc}") from exc

    cv_text = extract_text(str(cv_path)) if cv_path else ""

    fields = extract_structured(body, cv_text)
    candidate_id = _persist_candidate(fields, body, phone, cv_text)
    return {"ok": True, "candidate_id": candidate_id}


@router.get("/whatsapp-cloud")
async def whatsapp_cloud_verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    expected = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    if mode == "subscribe" and token and token == expected:
        return int(challenge or "0")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/whatsapp-cloud")
async def whatsapp_cloud_webhook(request: Request) -> Dict[str, Any]:
    payload = await request.json()

    changes = ((payload.get("entry") or [{}])[0].get("changes") or [{}])
    value = changes[0].get("value") or {}
    messages = value.get("messages") or []
    if not messages:
        return {"ok": True, "ignored": True}

    msg = messages[0]
    body = ((msg.get("text") or {}).get("body") or "").strip()
    phone = msg.get("from")

    cv_path = None
    msg_type = msg.get("type")
    media_obj = msg.get(msg_type, {}) if msg_type else {}
    media_id = media_obj.get("id")
    if media_id:
        filename = media_obj.get("filename") or f"{media_id}.bin"
        cv_path = DATA_DIR / filename
        try:
            await _download_whatsapp_cloud_media(media_id, cv_path)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=400, detail=f"Unable to download WhatsApp media: {exc}") from exc

    cv_text = extract_text(str(cv_path)) if cv_path else ""
    fields = extract_structured(body, cv_text)
    candidate_id = _persist_candidate(fields, body, phone, cv_text)
    return {"ok": True, "candidate_id": candidate_id}
