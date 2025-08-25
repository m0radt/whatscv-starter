# whatscv-starter

### Local run
1. Copy `.env.sample` to `.env` and fill secrets.
2. Set `GEMINI_API_KEY` in `.env` (from Google AI Studio). Optionally change `GEMINI_MODEL` (default: `gemini-1.5-flash`).
3. `docker compose up --build`
4. Visit http://localhost:8000/docs for interactive API docs.

### Webhook setup
- **Twilio Conversations**: Add a webhook for *message added* events pointing to `https://<your-host>/webhooks/twilio`.
- **WhatsApp Cloud API (1:1)**: Add a webhook for messages and adapt `webhooks.py` payload mapping.

### Data flow
WhatsApp → Webhook → (download CV) → Extract CV text → **Gemini JSON extract** → DB insert → Search API.

### Using Gemini (free-tier friendly)
- Create an API key in **Google AI Studio** and paste it into `GEMINI_API_KEY`.
- Default model is `gemini-1.5-flash`. Structured JSON output is enforced via the Gemini SDK `response_schema`.

### Security & privacy
- `id_number` is **never stored in plaintext**; only a salted SHA‑256 hash is saved (see `security.py`).
- Use HTTPS for all public endpoints; add Twilio signature verification before production.
- Provide candidates with a privacy notice and a deletion request channel.

### Extending
- Replace the simple keyword search with Postgres full‑text search or pgvector.
- Add a small admin UI for reviewing parsed records.
- Add field validation and confidence scores; route low‑confidence records to manual review.