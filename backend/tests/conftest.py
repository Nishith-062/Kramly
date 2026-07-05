"""
conftest.py
-----------
Shared pytest fixtures for planner tests.

Design decisions
~~~~~~~~~~~~~~~~
1. **No Neo4j dependency.**
   Every fixture is a pure Python data structure.  Tests run in
   milliseconds with zero network calls — CI-friendly, offline-friendly.

2. **The "fake graph" pattern.**
   We define skills and edges as dicts/lists, then build three closures
   (``fake_fetch_skill``, ``fake_fetch_all_prereqs``, ``fake_fetch_edges``)
   that mimic the ``graph_service`` function signatures.  The planner
   can't tell the difference.

3. **Reusable via ``@pytest.fixture``.**
   Each test receives a ``fake_graph`` fixture and destructures what it
   needs.  Adding a new test scenario means adding a new fixture — no
   boilerplate repeated across tests.
"""

import pytest


# ---------------------------------------------------------------------------
# A realistic WebDev skill graph (mirrors your live Neo4j data)
# ---------------------------------------------------------------------------
#
#   web01 ──► web02 ──► web03 ──► web04 ──► web05
#              │                    │
#              └──► web07           └──► web08 ◄── web05
#                                        │
#                                        └──► web09
#
#   (edges: prerequisite → dependent)

SKILLS = {
    "web01": {"id": "web01", "name": "HTML Fundamentals", "domain": "WebDev", "difficulty_level": "beginner"},
    "web02": {"id": "web02", "name": "CSS Fundamentals", "domain": "WebDev", "difficulty_level": "beginner"},
    "web03": {"id": "web03", "name": "JavaScript Basics", "domain": "WebDev", "difficulty_level": "beginner"},
    "web04": {"id": "web04", "name": "DOM Manipulation", "domain": "WebDev", "difficulty_level": "intermediate"},
    "web05": {"id": "web05", "name": "JS ES6+ Features", "domain": "WebDev", "difficulty_level": "intermediate"},
    "web07": {"id": "web07", "name": "Responsive Design", "domain": "WebDev", "difficulty_level": "intermediate"},
    "web08": {"id": "web08", "name": "Frontend Framework (React)", "domain": "WebDev", "difficulty_level": "intermediate"},
    "web09": {"id": "web09", "name": "State Management", "domain": "WebDev", "difficulty_level": "intermediate"},
    "isolated": {"id": "isolated", "name": "Isolated Skill", "domain": "Other", "difficulty_level": "beginner"},
}

# (from, to) = from is prerequisite of to
EDGES = [
    ("web01", "web02"),
    ("web02", "web03"),
    ("web02", "web07"),
    ("web03", "web04"),
    ("web03", "web05"),
    ("web04", "web08"),
    ("web05", "web08"),
    ("web07", "web08"),
    ("web08", "web09"),
]


def _build_ancestor_set(target_id: str, edges: list[tuple[str, str]]) -> set[str]:
    """Compute all transitive ancestors of ``target_id`` via BFS."""
    # Build reverse adjacency: child → [parents]
    reverse = {}
    for src, dst in edges:
        reverse.setdefault(dst, []).append(src)

    visited = set()
    queue = list(reverse.get(target_id, []))
    while queue:
        node = queue.pop()
        if node not in visited:
            visited.add(node)
            queue.extend(reverse.get(node, []))
    return visited


@pytest.fixture
def fake_graph():
    """Provide fake graph-service callables for the planner.

    Returns a dict with keys matching the planner's keyword arguments:
    ``fetch_skill``, ``fetch_all_prereqs_recursive``, ``fetch_prereq_edges``.
    """
    def fetch_skill(skill_id: str):
        return SKILLS.get(skill_id)

    def fetch_all_prereqs_recursive(skill_id: str):
        ancestor_ids = _build_ancestor_set(skill_id, EDGES)
        return [SKILLS[sid] for sid in sorted(ancestor_ids) if sid in SKILLS]

    def fetch_prereq_edges(skill_ids: list[str]):
        id_set = set(skill_ids)
        return [(s, d) for s, d in EDGES if s in id_set and d in id_set]

    return {
        "fetch_skill": fetch_skill,
        "fetch_all_prereqs_recursive": fetch_all_prereqs_recursive,
        "fetch_prereq_edges": fetch_prereq_edges,
    }


@pytest.fixture
def cyclic_graph():
    """A graph with a cycle: A → B → C → A.

    Used to verify that the planner raises ``CycleDetected``.
    """
    skills = {
        "A": {"id": "A", "name": "Skill A", "domain": "Test", "difficulty_level": "beginner"},
        "B": {"id": "B", "name": "Skill B", "domain": "Test", "difficulty_level": "beginner"},
        "C": {"id": "C", "name": "Skill C", "domain": "Test", "difficulty_level": "beginner"},
        "target": {"id": "target", "name": "Target", "domain": "Test", "difficulty_level": "beginner"},
    }
    edges = [
        ("A", "B"),
        ("B", "C"),
        ("C", "A"),  # ← cycle
        ("A", "target"),
        ("B", "target"),
        ("C", "target"),
    ]

    def fetch_skill(sid):
        return skills.get(sid)

    def fetch_all_prereqs_recursive(sid):
        ancestor_ids = _build_ancestor_set(sid, edges)
        return [skills[s] for s in sorted(ancestor_ids) if s in skills]

    def fetch_prereq_edges(sids):
        id_set = set(sids)
        return [(s, d) for s, d in edges if s in id_set and d in id_set]

    return {
        "fetch_skill": fetch_skill,
        "fetch_all_prereqs_recursive": fetch_all_prereqs_recursive,
        "fetch_prereq_edges": fetch_prereq_edges,
    }
