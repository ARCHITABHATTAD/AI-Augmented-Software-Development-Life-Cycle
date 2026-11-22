from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


@dataclass(frozen=True)
class ReviewerPrincipal:
    username: str
    role: str


reviewer_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="reviewerAuth",
    description="Local access token for a configured support reviewer.",
)


def current_principal(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(reviewer_bearer)
    ],
) -> ReviewerPrincipal:
    if credentials is None or not credentials.credentials.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    reviewer = request.app.state.repository.resolve_reviewer(
        credentials.credentials.strip()
    )
    if reviewer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid reviewer credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return ReviewerPrincipal(username=reviewer["username"], role=reviewer["role"])


SupportReviewer = Annotated[ReviewerPrincipal, Depends(current_principal)]


def support_reviewer(principal: SupportReviewer) -> ReviewerPrincipal:
    if principal.role != "support-reviewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The support-reviewer role is required.",
        )
    return principal
