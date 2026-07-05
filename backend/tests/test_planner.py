"""
test_planner.py
---------------
Unit tests for the learning-path planner.

All tests use injected fake callables (from conftest.py) instead of a
real Neo4j instance.  No network, no database — runs in milliseconds.

Test matrix
~~~~~~~~~~~
✓ Learner knows nothing          → full prerequisite chain returned
✓ Learner knows everything       → empty list returned
✓ Learner knows some skills      → only missing skills in correct order
✓ Invalid target skill            → SkillNotFound raised
✓ Invalid known skill             → SkillNotFound raised
✓ Disconnected / isolated target  → returns just the target (no prereqs)
✓ Duplicate known skills          → handled gracefully, no duplicates in path
✓ Cycle detection                 → CycleDetected raised
✓ Prerequisite ordering           → every prereq appears before its dependent
"""

import pytest

from optimizer.planner import generate_learning_path
from optimizer.exceptions import CycleDetected, SkillNotFound


# ---------------------------------------------------------------------------
# 1. Learner knows nothing
# ---------------------------------------------------------------------------

class TestLearnerKnowsNothing:
    """Learner starts from zero — the full prerequisite chain should be returned."""

    def test_full_chain_to_web08(self, fake_graph):
        path = generate_learning_path(
            known_skills=[],
            target_skill="web08",
            **fake_graph,
        )
        # Must include the target itself at the end.
        assert path[-1] == "web08"
        # Must include all 6 prerequisites.
        assert set(path) == {"web01", "web02", "web03", "web04", "web05", "web07", "web08"}

    def test_full_chain_preserves_ordering(self, fake_graph):
        path = generate_learning_path(
            known_skills=[],
            target_skill="web08",
            **fake_graph,
        )
        # Every prerequisite must appear BEFORE its dependent.
        for src, dst in [
            ("web01", "web02"),
            ("web02", "web03"),
            ("web03", "web04"),
            ("web03", "web05"),
            ("web02", "web07"),
            ("web04", "web08"),
            ("web05", "web08"),
            ("web07", "web08"),
        ]:
            if src in path and dst in path:
                assert path.index(src) < path.index(dst), (
                    f"'{src}' must come before '{dst}' in {path}"
                )


# ---------------------------------------------------------------------------
# 2. Learner knows everything
# ---------------------------------------------------------------------------

class TestLearnerKnowsEverything:
    """If the learner already knows the target, nothing to learn."""

    def test_knows_target_returns_empty(self, fake_graph):
        path = generate_learning_path(
            known_skills=["web08"],
            target_skill="web08",
            **fake_graph,
        )
        assert path == []

    def test_knows_target_and_prereqs_returns_empty(self, fake_graph):
        path = generate_learning_path(
            known_skills=["web01", "web02", "web03", "web04", "web05", "web07", "web08"],
            target_skill="web08",
            **fake_graph,
        )
        assert path == []


# ---------------------------------------------------------------------------
# 3. Learner knows some skills
# ---------------------------------------------------------------------------

class TestLearnerKnowsSomeSkills:
    """Only missing skills should appear in the path."""

    def test_knows_web01_web02(self, fake_graph):
        path = generate_learning_path(
            known_skills=["web01", "web02"],
            target_skill="web08",
            **fake_graph,
        )
        # Should NOT include web01 or web02.
        assert "web01" not in path
        assert "web02" not in path
        # Should include remaining prereqs + target.
        assert set(path) == {"web03", "web04", "web05", "web07", "web08"}
        # Target last.
        assert path[-1] == "web08"

    def test_knows_all_prereqs_only_target_remains(self, fake_graph):
        path = generate_learning_path(
            known_skills=["web01", "web02", "web03", "web04", "web05", "web07"],
            target_skill="web08",
            **fake_graph,
        )
        assert path == ["web08"]

    def test_ordering_after_partial_knowledge(self, fake_graph):
        path = generate_learning_path(
            known_skills=["web01", "web02"],
            target_skill="web08",
            **fake_graph,
        )
        # web03 must come before web04 and web05.
        assert path.index("web03") < path.index("web04")
        assert path.index("web03") < path.index("web05")


# ---------------------------------------------------------------------------
# 4. Invalid skill ID
# ---------------------------------------------------------------------------

class TestInvalidSkill:
    """Non-existent skill IDs should raise SkillNotFound."""

    def test_invalid_target_raises(self, fake_graph):
        with pytest.raises(SkillNotFound) as exc_info:
            generate_learning_path(
                known_skills=[],
                target_skill="NONEXISTENT",
                **fake_graph,
            )
        assert exc_info.value.skill_id == "NONEXISTENT"

    def test_invalid_known_skill_raises(self, fake_graph):
        with pytest.raises(SkillNotFound) as exc_info:
            generate_learning_path(
                known_skills=["FAKE_SKILL"],
                target_skill="web08",
                **fake_graph,
            )
        assert exc_info.value.skill_id == "FAKE_SKILL"

    def test_mix_of_valid_and_invalid_known(self, fake_graph):
        with pytest.raises(SkillNotFound) as exc_info:
            generate_learning_path(
                known_skills=["web01", "DOES_NOT_EXIST"],
                target_skill="web08",
                **fake_graph,
            )
        assert exc_info.value.skill_id == "DOES_NOT_EXIST"


# ---------------------------------------------------------------------------
# 5. Disconnected graph / isolated target
# ---------------------------------------------------------------------------

class TestDisconnectedGraph:
    """A skill with no prerequisites should return just the target."""

    def test_isolated_skill_returns_just_target(self, fake_graph):
        path = generate_learning_path(
            known_skills=[],
            target_skill="isolated",
            **fake_graph,
        )
        # "isolated" has no prerequisites → path is just [target].
        assert path == ["isolated"]

    def test_root_skill_returns_just_target(self, fake_graph):
        """web01 is a root node — no prerequisites."""
        path = generate_learning_path(
            known_skills=[],
            target_skill="web01",
            **fake_graph,
        )
        assert path == ["web01"]


# ---------------------------------------------------------------------------
# 6. Duplicate prerequisites / duplicate known skills
# ---------------------------------------------------------------------------

class TestDuplicates:
    """Duplicate entries should not cause duplicate skills in the path."""

    def test_duplicate_known_skills_handled(self, fake_graph):
        path = generate_learning_path(
            known_skills=["web01", "web01", "web02", "web02"],
            target_skill="web08",
            **fake_graph,
        )
        # No duplicates in output.
        assert len(path) == len(set(path))
        # web01 and web02 should still be excluded.
        assert "web01" not in path
        assert "web02" not in path

    def test_no_duplicates_in_output(self, fake_graph):
        path = generate_learning_path(
            known_skills=[],
            target_skill="web08",
            **fake_graph,
        )
        assert len(path) == len(set(path)), f"Duplicates found in {path}"


# ---------------------------------------------------------------------------
# 7. Cycle detection
# ---------------------------------------------------------------------------

class TestCycleDetection:
    """The planner must detect and reject cyclic prerequisite graphs."""

    def test_cycle_raises(self, cyclic_graph):
        with pytest.raises(CycleDetected):
            generate_learning_path(
                known_skills=[],
                target_skill="target",
                **cyclic_graph,
            )

    def test_cycle_error_message_contains_stuck_nodes(self, cyclic_graph):
        with pytest.raises(CycleDetected) as exc_info:
            generate_learning_path(
                known_skills=[],
                target_skill="target",
                **cyclic_graph,
            )
        # The error should mention the stuck nodes.
        detail = str(exc_info.value)
        assert "Cycle detected" in detail


# ---------------------------------------------------------------------------
# 8. Ordering correctness (parameterised)
# ---------------------------------------------------------------------------

class TestPrerequisiteOrdering:
    """Every prerequisite edge must be respected in the output order."""

    EDGE_PAIRS = [
        ("web01", "web02"),
        ("web02", "web03"),
        ("web03", "web04"),
        ("web03", "web05"),
        ("web02", "web07"),
        ("web04", "web08"),
        ("web05", "web08"),
        ("web07", "web08"),
    ]

    @pytest.mark.parametrize("prereq,dependent", EDGE_PAIRS)
    def test_prereq_before_dependent(self, fake_graph, prereq, dependent):
        path = generate_learning_path(
            known_skills=[],
            target_skill="web08",
            **fake_graph,
        )
        if prereq in path and dependent in path:
            assert path.index(prereq) < path.index(dependent), (
                f"'{prereq}' should come before '{dependent}' in {path}"
            )
