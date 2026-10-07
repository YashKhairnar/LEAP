import pandas as pd

from leap.learner_state.data.preprocessing import normalize_code, prepare_dcu_submissions


def test_normalize_code_preserves_hash_in_string() -> None:
    code = "#!/usr/bin/python\nvalue = '#tag'  # remove me\n\n\nprint(value)\n"
    assert normalize_code(code) == "value = '#tag'\nprint(value)"


def test_prepare_dcu_submissions_filters_and_deduplicates() -> None:
    frame = pd.DataFrame(
        [
            {"user": "u1", "module": "m1", "task": "task.py", "date": "2024-01-01", "upload": "print(1)", "extension": "py", "correct": False},
            {"user": "u1", "module": "m1", "task": "task.py", "date": "2024-01-02", "upload": "print(1) # duplicate", "extension": "py", "correct": False},
            {"user": "u1", "module": "m1", "task": "task.py", "date": "2024-01-03", "upload": "print(2)", "extension": "txt", "correct": True},
        ]
    )
    result = prepare_dcu_submissions(frame)
    assert len(result) == 1
    assert result.iloc[0]["unique_task_id"] == "m1_task.py"

