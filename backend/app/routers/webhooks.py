import os
import pathlib
import logging
from typing import Any, Dict
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
logger = logging.getLogger(__name__)

NO_CV_MESSAGE = "Please send your CV as an attachment so we can continue your application."
SUCCESS_MESSAGE = "Your CV was received successfully. Thank you."
UPDATED_MESSAGE = "Your information was updated successfully. Thank you."
FAIL_MESSAGE = "We could not process your CV. Please try again with a clear file."


def _format_display_name(value: object) -> str:
    if not isinstance(value, str):
        return ""
    name = " ".join(value.split()).strip()
    if not name:
        return ""
    return name.title()


def _safe_delete_file(path: pathlib.Path | None) -> None:
    if not path:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Unable to delete uploaded file %s: %s", path, exc)


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


async def _send_whatsapp_cloud_text(to: str | None, text: str) -> bool:
    token = os.getenv("CLOUDAPI_TOKEN")
    phone_number_id = os.getenv("WABA_PHONE_NUMBER_ID")
    if not token or not phone_number_id or not to:
        return False

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://graph.facebook.com/v21.0/{phone_number_id}/messages",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.warning("Unable to send WhatsApp Cloud reply: %s", exc)
        return False


def _upsert_candidate(fields: Dict[str, object], body: str, phone: str | None, cv_text: str) -> tuple[int, str]:
    db: Session = SessionLocal()
    try:
        effective_phone = fields.get("phone") or phone
        cand = None
        if effective_phone:
            cand = db.query(Candidate).filter(Candidate.phone == effective_phone).first()

        action = "created"
        if cand:
            action = "updated"
            cand.phone = effective_phone
            cand.email = fields.get("email")
            cand.full_name = fields.get("full_name")
            cand.id_number_hash = hash_sensitive(fields.get("id_number"))
            cand.location_city = fields.get("location_city")
            cand.raw_paragraph = body
            cand.cv_text = cv_text
        else:
            cand = Candidate(
                phone=effective_phone,
                email=fields.get("email"),
                full_name=fields.get("full_name"),
                id_number_hash=hash_sensitive(fields.get("id_number")),
                location_city=fields.get("location_city"),
                raw_paragraph=body,
                cv_text=cv_text,
            )
            db.add(cand)
            db.flush()

        db.query(Education).filter(Education.candidate_id == cand.id).delete(synchronize_session=False)
        db.query(Experience).filter(Experience.candidate_id == cand.id).delete(synchronize_session=False)

        for edu in fields.get("education", []) or []:
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
        return cand.id, action
    finally:
        db.close()

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

    msg_type = msg.get("type")
    # Only process CV uploads from document messages.
    # For plain text messages we guide the user to upload CV.
    if msg_type == "text":
        await _send_whatsapp_cloud_text(phone, NO_CV_MESSAGE)
        return {"ok": False, "message": NO_CV_MESSAGE, "ignored": True}
    if msg_type != "document":
        return {"ok": True, "ignored": True, "reason": f"Unsupported message type: {msg_type}"}

    cv_path = None
    media_obj = msg.get(msg_type, {}) if msg_type else {}
    media_id = media_obj.get("id")
    if media_id:
        filename = media_obj.get("filename") or f"{media_id}.bin"
        cv_path = DATA_DIR / filename
        try:
            await _download_whatsapp_cloud_media(media_id, cv_path)
        except httpx.HTTPError as exc:
            _safe_delete_file(cv_path)
            await _send_whatsapp_cloud_text(phone, FAIL_MESSAGE)
            return {"ok": False, "message": FAIL_MESSAGE, "error": f"Unable to download WhatsApp media: {exc}"}
    else:
        await _send_whatsapp_cloud_text(phone, NO_CV_MESSAGE)
        return {"ok": False, "message": NO_CV_MESSAGE, "ignored": True}

    try:
        cv_text = extract_text(str(cv_path)) if cv_path else ""
        fields = extract_structured(body, cv_text)
        candidate_id, action = _upsert_candidate(fields, body, phone, cv_text)
        reply_message = UPDATED_MESSAGE if action == "updated" else SUCCESS_MESSAGE
        saved_name = _format_display_name(fields.get("full_name"))
        if saved_name:
            reply_message = f"{reply_message} Candidate: {saved_name}."
        await _send_whatsapp_cloud_text(phone, reply_message)
        return {"ok": True, "candidate_id": candidate_id, "action": action, "message": reply_message}
    except Exception:
        logger.exception("WhatsApp Cloud CV processing failed")
        await _send_whatsapp_cloud_text(phone, FAIL_MESSAGE)
        return {"ok": False, "message": FAIL_MESSAGE}
    finally:
        _safe_delete_file(cv_path)
