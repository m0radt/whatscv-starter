from fastapi import FastAPI
from .db import init_db
from .routers import webhooks, candidates, search

app = FastAPI(title="whatscv-starter")

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(candidates.router, prefix="/api/candidates", tags=["candidates"])
app.include_router(search.router, prefix="/api/candidates", tags=["search"])

@app.get("/")
def root():
    return {"ok": True, "service": "whatscv-starter"}