"""
routes.py
---------
FastAPI route definitions.

Design decisions
~~~~~~~~~~~~~~~~
1. **Thin route handler.**
   The route does *only* three things:
     a) Accept and validate the request (Pydantic handles this).
     b) Wire up the planner with the real graph_service functions.
     c) Translate planner exceptions into HTTP status codes.
   All business logic lives in ``planner.py``.  The route is glue code.

2. **Exception → HTTP status mapping.**
   - ``SkillNotFound``  → 404 Not Found
   - ``CycleDetected``  → 409 Conflict (the graph data is inconsistent)
   - ``NoLearningPath`` → 404 Not Found (target unreachable)
   - Unexpected errors  → 500 Internal Server Error (logged, not leaked)

3. **``APIRouter`` instead of decorating ``app`` directly.**
   This keeps routes modular.  ``main.py`` includes the router via
   ``app.include_router()``.  As the API grows you can add more routers
   (e.g., ``learner_routes.py``) without touching main.

4. **``response_model`` on the route.**
   FastAPI will serialise the return value through ``LearningPathResponse``
   and show the exact schema in the Swagger docs.

5. **Dependency injection bridge.**
   The planner receives ``graph_service.get_skill`` etc. as callables —
   the route is the *only* place where ``graph_service`` and ``planner``
   meet.  Neither knows about the other directly.
"""

import logging

from fastapi import APIRouter, HTTPException

from app import graph_service
from models.request import LearningPathRequest
from models.response import ErrorResponse, LearningPathResponse
from optimizer.exceptions import CycleDetected, NoLearningPath, SkillNotFound
from optimizer.planner import generate_learning_path

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/learning-path",
    response_model=LearningPathResponse,
    summary="Generate a personalised learning path",
    description=(
        "Given a learner's known skills and a target skill, returns an "
        "ordered sequence of skills to study.  The sequence respects all "
        "prerequisite relationships in the knowledge graph."
    ),
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Target skill or a known skill was not found in the graph.",
        },
        409: {
            "model": ErrorResponse,
            "description": "A cycle was detected in the prerequisite graph.",
        },
    },
)
async def create_learning_path(
    request: LearningPathRequest,
) -> LearningPathResponse:
    """Compute and return a learning path.

    This handler wires the planner to the real graph service and
    translates domain exceptions into HTTP responses.
    """
    logger.info(
        "POST /learning-path  known_skills=%s  target_skill='%s'",
        request.known_skills,
        request.target_skill,
    )

    try:
        path = generate_learning_path(
            known_skills=request.known_skills,
            target_skill=request.target_skill,
            # --- Dependency injection bridge ---
            fetch_skill=graph_service.get_skill,
            fetch_all_prereqs_recursive=graph_service.get_all_prerequisites_recursive,
            fetch_prereq_edges=graph_service.get_prerequisite_edges,
        )
    except SkillNotFound as exc:
        logger.warning("Skill not found: %s", exc.skill_id)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoLearningPath as exc:
        logger.warning("No learning path: %s", exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CycleDetected as exc:
        logger.error("Cycle detected in graph: %s", exc)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        # Catch-all: log the full traceback, return a generic 500.
        logger.exception("Unexpected error in learning-path generation")
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Please try again later.",
        ) from exc

    return LearningPathResponse(path=path)
