import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.world_evolution_engine import (
    WorldEvolutionEngine,
    _build_cumulative_state,
    _build_parent_rounds_data,
    _is_time_regression,
)


def test_validate_round_result_keeps_new_entities():
    engine = WorldEvolutionEngine.__new__(WorldEvolutionEngine)

    result = engine._validate_round_result(
        {
            "year_advanced_to": "Year 12",
            "narrative": "A new guild appears and changes the balance of power.",
            "affected_entities": [
                {
                    "name": "Old Kingdom",
                    "state_changes": "Loses control of the western road.",
                    "new_status": "Weakened regional power",
                },
                {
                    "name": "New Guild",
                    "state_changes": "Forms around the western road trade.",
                    "new_status": "Emergent trade faction",
                },
            ],
            "new_events": [],
        },
        {"Old Kingdom"},
        1,
    )

    assert [item["name"] for item in result["affected_entities"]] == ["Old Kingdom", "New Guild"]
    assert result["affected_entities"][0]["is_new_entity"] is False
    assert result["affected_entities"][1]["is_new_entity"] is True
    assert "warnings" in result


def test_validate_round_result_normalizes_invalid_events():
    engine = WorldEvolutionEngine.__new__(WorldEvolutionEngine)

    result = engine._validate_round_result(
        {
            "year_advanced_to": "",
            "narrative": "",
            "affected_entities": [],
            "new_events": [
                {"name": "Road Accord", "involved_entities": "Old Kingdom"},
                {"description": "missing name"},
                "not a dict",
            ],
        },
        set(),
        2,
    )

    assert result["year_advanced_to"] == "未知"
    assert result["narrative"]
    assert result["new_events"] == [
        {
            "name": "Road Accord",
            "date": "",
            "description": "",
            "involved_entities": [],
        }
    ]
    assert any("year_advanced_to" in warning for warning in result["warnings"])
    assert any("involved_entities" in warning for warning in result["warnings"])


def test_normalize_phase_plan_preserves_llm_time_span():
    engine = WorldEvolutionEngine.__new__(WorldEvolutionEngine)

    phases = engine._normalize_phase_plan(
        [
            {
                "phase_name": "动荡期",
                "rounds": 1,
                "time_span": "第五纪1352-1353年",
                "focus": "势力重组",
            }
        ],
        1,
        {"label": "第五纪1352年"},
    )

    assert phases[0]["time_span"] == "第五纪1352-1353年"


def test_time_regression_detection_for_common_formats():
    assert _is_time_regression("第五纪1352年秋", "第五纪1352年春") is True
    assert _is_time_regression("Year 12", "Year 11") is True
    assert _is_time_regression("第五纪1352年", "第五纪1353年") is False


def test_validate_round_result_marks_time_regression_warning():
    engine = WorldEvolutionEngine.__new__(WorldEvolutionEngine)

    result = engine._validate_round_result(
        {
            "year_advanced_to": "第五纪1352年春",
            "narrative": "这是一段足够长的推演叙事，用来描述世界在一个阶段内发生的变化和各方势力的互动。" * 3,
            "affected_entities": [],
            "new_events": [],
        },
        set(),
        3,
        previous_time="第五纪1352年秋",
    )

    assert any("早于上一轮时间" in warning for warning in result["warnings"])


def test_parent_rounds_data_builds_structured_cumulative_state():
    parent_rounds = _build_parent_rounds_data(
        {
            "parent_rounds": [
                {
                    "year_advanced_to": "Year 10",
                    "affected_entities": [
                        {"name": "New Guild", "new_status": "Controls western trade"}
                    ],
                    "new_events": [
                        {"name": "Trade Pact", "date": "Year 10"}
                    ],
                }
            ]
        }
    )

    state = _build_cumulative_state(parent_rounds, {"Old Kingdom"})

    assert "New Guild" in state
    assert "[新实体]" in state
    assert "Trade Pact" in state
