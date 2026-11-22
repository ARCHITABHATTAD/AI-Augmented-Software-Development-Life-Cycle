from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, StrictStr

from src.api.auth import ReviewerPrincipal, support_reviewer
from src.domain.triage import TriageResult

router = APIRouter()


@router.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(
        Path(__file__).with_name("static").joinpath("index.html"),
        headers={"Cache-Control": "no-store"},
    )


class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: StrictStr


@router.post("/triage", response_model=TriageResult)
def triage(request: Request, body: TriageRequest, response: Response) -> TriageResult:
    result = request.app.state.triage_service.triage(body.message)
    record_id = request.app.state.repository.create_record(body.message, result)
    response.headers["X-Record-ID"] = record_id
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("/retained/{record_id}")
def get_retained_record(
    record_id: str,
    request: Request,
    response: Response,
    principal: Annotated[ReviewerPrincipal, Depends(support_reviewer)],
) -> dict[str, object]:
    del principal
    record = request.app.state.repository.get_record(record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retained record was not found or has expired.",
        )
    response.headers["Cache-Control"] = "no-store"
    return record
