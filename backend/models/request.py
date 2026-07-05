"""
request.py
----------
Pydantic models for incoming API requests.

Design decisions
~~~~~~~~~~~~~~~~
1. **Validation at the boundary.**
   FastAPI deserialises and validates the JSON body *before* the route
   handler runs.  If ``target_skill`` is missing or ``known_skills``
   contains a non-string, the client gets a 422 with a precise error —
   our planner code never sees invalid input.

2. **``min_length=1`` on ``target_skill``.**
   An empty string is not a valid skill ID.  Catching this here avoids
   a confusing ``SkillNotFound("")`` error from the planner.

3. **``known_skills`` defaults to an empty list.**
   A brand-new learner who knows nothing shouldn't have to send
   ``"known_skills": []`` explicitly — omitting the field is fine.

4. **``model_config["json_schema_extra"]``** provides a realistic
   example that shows up in the interactive Swagger docs at ``/docs``.
"""

from pydantic import BaseModel, Field


class LearningPathRequest(BaseModel):
    """Request body for the ``POST /learning-path`` endpoint."""

    known_skills: list[str] = Field(
        default_factory=list,
        description="Skill IDs the learner already knows. May be empty.",
        examples=[["web01", "web02"]],
    )
    target_skill: str = Field(
        ...,
        min_length=1,
        description="The skill ID the learner wants to reach.",
        examples=["web08"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "known_skills": ["web01", "web02"],
                    "target_skill": "web08",
                }
            ]
        }
    }
