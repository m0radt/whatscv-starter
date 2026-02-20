# whatscv-starter

### Local run
1. Copy `.env.sample` to `.env` and fill secrets.
2. Set `GEMINI_API_KEY` in `.env` (from Google AI Studio). Optionally change `GEMINI_MODEL` (default: `gemini-1.5-flash`).
3. `docker compose up --build`
4. Visit http://localhost:8000/docs for interactive API docs.

### DB migration (cleanup legacy columns)
Run this once after pulling latest changes:
`docker compose exec -T db psql -U postgres -d whatscv < backend/migrations/0002_cleanup_schema.sql`

### Webhook setup
- **WhatsApp Cloud API (1:1)**:
  - Verify URL: `GET https://<your-host>/webhooks/whatsapp-cloud`
  - Callback URL: `POST https://<your-host>/webhooks/whatsapp-cloud`
  - Set `WHATSAPP_VERIFY_TOKEN` and `CLOUDAPI_TOKEN` in `.env`.

### Data flow
WhatsApp → Webhook → (download CV) → Extract CV text → **Gemini JSON extract** → DB insert → Search API.

### Using Gemini (free-tier friendly)
- Create an API key in **Google AI Studio** and paste it into `GEMINI_API_KEY`.
- Default model is `gemini-2.0-flash`. Structured JSON output is requested via the `google-genai` SDK with `response_mime_type=application/json`.

### Security & privacy
- `id_number` is **never stored in plaintext**; only a salted SHA‑256 hash is saved (see `security.py`).
- Use HTTPS for all public endpoints.
- Provide candidates with a privacy notice and a deletion request channel.

### Extending
- Replace the simple keyword search with Postgres full‑text search or pgvector.
- Add a small admin UI for reviewing parsed records.
- Add field validation and confidence scores; route low‑confidence records to manual review.
