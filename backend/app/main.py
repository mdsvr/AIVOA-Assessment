import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, complaints
from app.core.config import settings
from app.db.models import Base
from app.db.session import engine


class BodyTooLargeError(Exception):
    pass


class MaxBodySizeMiddleware:
    """ASGI-layer cap, checked via Content-Length before Starlette's MultiPartParser
    (or any other body parser) runs. An app-level bound in the route handler alone is
    too late: MultiPartParser.parse() drains the whole ASGI receive stream into the
    UploadFile's backing store during FastAPI's parameter resolution, before the route
    function -- and its own chunked-read bound -- ever executes.

    Most real clients here declare Content-Length (fetch() with a FormData body always
    computes it upfront), so the header check above rejects those before any body is
    read. For the residual case -- chunked transfer-encoding with no declared length --
    `receive()` is wrapped below to count bytes across chunks so an unbounded body still
    can't be buffered into memory. `_read_upload_bounded` in complaints.py stays as
    defense in depth for whatever this doesn't catch."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def _reject(self, send):
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        body = json.dumps(
            {"detail": f"Request body exceeds max size of {self.max_bytes // (1024 * 1024)}MB"}
        ).encode()
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        content_length = next(
            (v for k, v in scope.get("headers", []) if k == b"content-length"), None
        )
        if content_length is not None:
            try:
                too_large = int(content_length) > self.max_bytes
            except ValueError:
                too_large = False
            if too_large:
                await self._reject(send)
                return
            return await self.app(scope, receive, send)

        total = 0

        async def counted_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.max_bytes:
                    raise BodyTooLargeError
            return message

        try:
            await self.app(scope, counted_receive, send)
        except BodyTooLargeError:
            await self._reject(send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AIVOA Complaint Management System", lifespan=lifespan)

# Multipart framing (boundaries, part headers) and the non-file form fields add a little
# on top of the file's own bytes -- pad the transport-level cap so a legitimately
# max-size file isn't rejected here. settings.max_upload_bytes stays the authoritative
# file-size limit, enforced at the route level by validate_upload/_read_upload_bounded.
MULTIPART_OVERHEAD_BYTES = 64 * 1024
app.add_middleware(
    MaxBodySizeMiddleware, max_bytes=settings.max_upload_bytes + MULTIPART_OVERHEAD_BYTES
)

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
