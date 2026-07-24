import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, complaints
from app.core.config import settings
from app.db.models import Base
from app.db.session import engine


class MaxBodySizeMiddleware:
    """ASGI-layer cap, checked via Content-Length before Starlette's MultiPartParser
    (or any other body parser) runs. An app-level bound in the route handler alone is
    too late: MultiPartParser.parse() drains the whole ASGI receive stream into the
    UploadFile's backing store during FastAPI's parameter resolution, before the route
    function -- and its own chunked-read bound -- ever executes.

    Covers every real client here: fetch() with a FormData body always computes and
    sends Content-Length (the File's size is known upfront, so it's never chunked
    transfer-encoding). A raw request using chunked encoding with no declared length is
    a residual gap -- out of scope for a local demo app with no public traffic; closing
    it needs wrapping `receive()` to count bytes across chunks, which is real ASGI
    middleware work than isn't justified here. `_read_upload_bounded` in complaints.py
    stays as defense in depth for whatever this doesn't catch."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            content_length = next(
                (v for k, v in scope.get("headers", []) if k == b"content-length"), None
            )
            if content_length is not None:
                try:
                    too_large = int(content_length) > self.max_bytes
                except ValueError:
                    too_large = False
                if too_large:
                    await send(
                        {
                            "type": "http.response.start",
                            "status": 413,
                            "headers": [(b"content-type", b"application/json")],
                        }
                    )
                    body = json.dumps(
                        {
                            "detail": f"Request body exceeds max size of "
                            f"{self.max_bytes // (1024 * 1024)}MB"
                        }
                    ).encode()
                    await send({"type": "http.response.body", "body": body})
                    return
        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AIVOA Complaint Management System", lifespan=lifespan)

app.add_middleware(MaxBodySizeMiddleware, max_bytes=settings.max_upload_bytes)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(complaints.router, prefix="/api/complaints", tags=["complaints"])
app.include_router(chat.router, prefix="/api/complaints", tags=["chat"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
