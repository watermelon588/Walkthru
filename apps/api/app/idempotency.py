"""Durable, fail-closed claims for run intents. No retries of application work after an unknown outcome."""

import hashlib
import json
import logging
import uuid
from collections.abc import Callable

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app import db, provider_usage

UNKNOWN = "We could not confirm this request's result. Check the run in your dashboard before starting another test."
SAFE_HEADERS = {"x-walkthru-code", "retry-after"}


def run(request: Request, user_id: str, operation: str, body: dict, perform: Callable[[str], dict], run_id: str | None = None):
    raw_key = request.headers.get("Idempotency-Key")
    if raw_key is None:  # Older clients retain their contract, without automatic retry guarantees.
        resource = run_id or uuid.uuid4().hex
        with provider_usage.scope(run_id=resource, user_id=user_id):
            return perform(resource)
    try:
        key = str(uuid.UUID(raw_key))
        resource = str(uuid.UUID(run_id)) if run_id else str(uuid.uuid4())
    except ValueError as error:
        raise HTTPException(422, "Use a UUID for the request key and run ID.") from error
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    owner = str(uuid.uuid4())
    claim = db.claim_run_request(user_id, key, operation, digest, owner, resource)
    state = claim["state"]
    if state == "conflict":
        raise HTTPException(409, "This request key was already used for a different request.", headers={"X-Walkthru-Code": "idempotency_conflict"})
    if state == "pending":
        raise HTTPException(409, "This run request is still processing. Please wait.",
                            headers={"Retry-After": "2", "X-Walkthru-Code": "request_in_progress"})
    if state == "gone":
        raise HTTPException(410, "This request's saved response is no longer available. Check your dashboard.")
    if state == "uncertain":
        raise HTTPException(409, UNKNOWN, headers={"X-Walkthru-Code": "request_outcome_unknown"})
    if state == "replay":
        return JSONResponse(claim["response"], status_code=claim["status"], headers=(claim.get("headers") or {}) | {"Idempotency-Replayed": "true"})
    if state != "claimed":
        raise db.DatabaseUnavailable("Unexpected run request claim state")
    try:
        try:
            with provider_usage.scope(operation_id=key, user_id=user_id, run_id=claim["run_id"]):
                result, status, headers = perform(uuid.UUID(claim["run_id"]).hex), 200, {}
        except HTTPException as error:
            if error.status_code >= 500:
                raise
            result, status = {"detail": error.detail}, error.status_code
            headers = {k: v for k, v in (error.headers or {}).items() if k.lower() in SAFE_HEADERS}
        if not db.finish_run_request(user_id, key, owner, "complete", status, result, headers):
            raise db.DatabaseUnavailable("The request claim was invalidated before completion")
    except Exception as error:
        logging.getLogger("walkthru.requests").exception("Run request outcome unknown")
        try:
            db.finish_run_request(user_id, key, owner, "uncertain", 503, None, None)
        except Exception:
            logging.getLogger("walkthru.requests").exception("Could not record uncertain run request")
        raise HTTPException(503, UNKNOWN, headers={"X-Walkthru-Code": "request_outcome_unknown"}) from error
    return JSONResponse(result, status_code=status, headers=headers | {"Idempotency-Replayed": "false"})
