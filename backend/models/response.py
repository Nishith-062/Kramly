"""
response.py
-----------
Pydantic models for outgoing API responses.

Design decisions
~~~~~~~~~~~~~~~~
1. **Typed response model on the route.**
   FastAPI uses this to generate the OpenAPI schema *and* to serialise
   the response.  The Swagger docs will show exactly what the client
   should expect — no guessing.

2. **``ErrorResponse`` for structured errors.**
   Instead of returning a plain string on 404/409/500, we return
   ``{"detail": "..."}`` — consistent, machine-parseable, and what
   FastAPI's own ``HTTPException`` does by default.
"""

from pydantic import BaseModel, Field


class LearningPathResponse(BaseModel):
    """Successful response from ``POST /learning-path``."""

    path: list[str] = Field(
        ...,
        description=(
            "Ordered list of skill IDs the learner should study, "
            "from first to last. Empty if the learner already knows the target."
        ),
        examples=[["web03", "web04", "web05", "web07", "web08"]],
    )


class ErrorResponse(BaseModel):
    """Standard error body returned by all non-2xx responses."""

    detail: str = Field(
        ...,
        description="Human-readable error message.",
        examples=["Skill not found in graph: 'INVALID_999'"],
    )
