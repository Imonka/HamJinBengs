"""The web server. Run with: python -m uvicorn app.main:app --port 8080

Each feature lives in app/modules/<name>/ and brings its own routes (see app/modules/__init__.py)."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.errors import AppError
from app.core.schema import HealthStatus
from app.modules import routers

log = logging.getLogger("api")

app = FastAPI(title="Leave Cover Scheduler API", version="2.0.0", docs_url="/api/docs",
              openapi_url="/api/openapi.json")



@app.get("/api/healthz", response_model=HealthStatus, tags=["health"])
def health():
    return {"status": "ok"}


for router in routers():
    app.include_router(router, prefix="/api")


@app.exception_handler(AppError)
async def app_error(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=exc.payload())


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", []) if p not in ("body", "query", "path"))
    message = first.get("msg", "Invalid request")
    return JSONResponse(status_code=400, content={"error": f"{where}: {message}" if where else message})


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


@app.exception_handler(Exception)
async def unexpected_error(_: Request, exc: Exception):
    log.exception("Unhandled error", exc_info=exc)
    return JSONResponse(status_code=500, content={"error": "Something went wrong on the server."})
