import os
import pathlib
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..extract.cv_text import extract_text
from ..extract.llm import extract_structured
from ..models import Candidate, Experience
from ..security import hash_sensitive
import httpx

router = APIRouter()
DATA_DIR = pathlib.Path("data/uploads")
DATA_DIR.mkdir(parents=True, exist_ok=True)

async def _download_media(url: str, dest: pathlib.Path) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)

@router.post("/twilio")
async def twilio_webhook(request: Request) -> Dict[str, Any]:
    """
    Generic webhook for Twilio Conversations/WhatsApp. Expects JSON events
    where message body is available, and media URLs if attachments exist.
    This route is intentionally permissive to simplify first run—add signature
    verification and IP allowlists before production.
    """
    payload = await request.json()

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
        await _download_media(media_url, cv_path)

    cv_text = extract_text(str(cv_path)) if cv_path else ""

    # LLM extraction
    fields = extract_structured(body, cv_text)

    # Persist
    db: Session = SessionLocal()
    try:
        cand = Candidate(
            phone=phone,
            full_name=fields.get("full_name"),
            id_number_hash=hash_sensitive(fields.get("id_number")),
            education_institution=fields.get("education_institution"),
            education_level=fields.get("education_level"),
            year_of_study=fields.get("year_of_study"),
            location_city=fields.get("location_city"),
            raw_paragraph=body,
            cv_text=cv_text,
        )
        db.add(cand)
        db.flush()

        for exp in fields.get("experiences", []) or []:
            db.add(Experience(
                candidate_id=cand.id,
                company=exp.get("company"),
                title=exp.get("title"),
                start=exp.get("start"),
                end=exp.get("end"),
                description=exp.get("description"),
            ))
        db.commit()
        return {"ok": True, "candidate_id": cand.id}
    finally:
        db.close()