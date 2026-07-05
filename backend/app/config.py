"""
config.py
---------
Centralised configuration for the Kramly backend.

Design decisions
~~~~~~~~~~~~~~~~
1. **pydantic-settings** (`BaseSettings`) is used instead of raw
   ``os.getenv()`` calls.  This gives us:
   - Automatic type coercion and validation at startup.
   - A single, importable ``settings`` object — no scattered getenv().
   - Built-in ``.env`` file loading without manually calling ``load_dotenv()``.
   - Frozen model — settings are immutable after creation, preventing
     accidental mutation at runtime.

2. The ``.env`` file is resolved relative to the *project root*
   (two levels above ``backend/app/``), so it reuses the same ``.env``
   that Person A's loading scripts already rely on.

3. ``NEO4J_USERNAME`` is the canonical name in the backend spec.
   ``validation_alias`` lets pydantic also accept ``NEO4J_USER`` from
   Person A's existing ``.env`` — zero friction, no file edits needed.
"""

import os
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

# Resolve the project root: backend/app/config.py  →  ../../.env
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings populated from environment variables / ``.env``."""

    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Bolt URI for the Neo4j instance.",
    )
    neo4j_username: str = Field(
        default="neo4j",
        # Accept either NEO4J_USERNAME (our spec) or NEO4J_USER (Person A's .env)
        validation_alias=AliasChoices("NEO4J_USERNAME", "NEO4J_USER"),
        description="Neo4j authentication username.",
    )
    neo4j_password: str = Field(
        ...,  # required — no default; fail loudly if missing
        description="Neo4j authentication password.",
    )

    model_config = {
        # Automatically load the .env sitting at the project root.
        "env_file": str(_PROJECT_ROOT / ".env"),
        # Environment variables are case-insensitive on Windows, but
        # pydantic-settings lowercases field names by default — this
        # keeps matching predictable regardless of OS.
        "case_sensitive": False,
        # Immutable after creation.
        "frozen": True,
    }


# Module-level singleton — imported everywhere as ``from app.config import settings``.
settings = Settings()
