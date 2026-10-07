import unittest

from pydantic import ValidationError

from app.models import GeneratedLessonContent
from app.tutoring.generator import TUTOR_SCHEMA


SECTION_ORDER = ["meaning", "analogy", "example", "code", "result", "why_it_matters"]


def lesson_with(section_order: list[str]) -> dict:
    return {
        "title": "Train a classifier",
        "introduction": "Learn one stage of the pipeline.",
        "code_explanation": ["model.fit(X, y) — learns from features and labels."],
        "try_this": ["Print the fitted model and inspect its settings."],
        "key_takeaway": "Fitting turns examples into learned model parameters.",
        "sections": [
            {
                "type": section_type,
                "title": section_type.replace("_", " ").title(),
                "body": f"Content for {section_type}.",
                "items": [],
                "code": "model.fit(X, y)" if section_type == "code" else None,
                "language": "python" if section_type == "code" else None,
            }
            for section_type in section_order
        ],
    }


class LessonStructureTests(unittest.TestCase):
    def test_generation_schema_requires_the_six_named_sections(self):
        lesson_schema = TUTOR_SCHEMA["properties"]["lesson"]
        sections_schema = lesson_schema["properties"]["sections"]
        self.assertEqual(sections_schema["minItems"], 6)
        self.assertEqual(sections_schema["maxItems"], 6)
        self.assertEqual(sections_schema["items"]["properties"]["type"]["enum"], SECTION_ORDER)
        self.assertIn("code_explanation", lesson_schema["required"])
        self.assertNotIn("try_this", lesson_schema["required"])
        self.assertIn("key_takeaway", lesson_schema["required"])

    def test_model_accepts_the_complete_sequence_in_order(self):
        lesson = GeneratedLessonContent.model_validate(lesson_with(SECTION_ORDER))
        self.assertEqual([section.type for section in lesson.sections], SECTION_ORDER)

    def test_model_rejects_an_out_of_order_sequence(self):
        wrong_order = ["meaning", "example", "analogy", "code", "result", "why_it_matters"]
        with self.assertRaisesRegex(ValidationError, "six-part teaching sequence"):
            GeneratedLessonContent.model_validate(lesson_with(wrong_order))

    def experiment_lesson(self, find="model.fit(X, y)", replace="model.fit(X, y)\nprint(model)"):
        lesson = lesson_with(SECTION_ORDER)
        lesson["try_this"] = [{
            "title": "Inspect the fitted model",
            "find": find,
            "replace": replace,
            "expected_change": "The output now shows the model and its settings.",
        }]
        return lesson

    def test_llm_schema_does_not_generate_experiments(self):
        self.assertNotIn("try_this", TUTOR_SCHEMA["properties"]["lesson"]["properties"])

    def test_exact_edit_round_trips(self):
        source = self.experiment_lesson()
        lesson = GeneratedLessonContent.model_validate(source)
        self.assertEqual(lesson.model_dump()["try_this"], source["try_this"])

    def test_rejects_edit_for_code_that_is_not_in_cell(self):
        with self.assertRaisesRegex(ValidationError, "match exactly one location"):
            GeneratedLessonContent.model_validate(self.experiment_lesson(find="print(df.head())"))

    def test_rejects_ambiguous_edit(self):
        source = self.experiment_lesson()
        source["sections"][3]["code"] = "model.fit(X, y)\nmodel.fit(X, y)"
        with self.assertRaisesRegex(ValidationError, "match exactly one location"):
            GeneratedLessonContent.model_validate(source)

    def test_rejects_no_op_edit(self):
        with self.assertRaisesRegex(ValidationError, "must change the lesson code"):
            GeneratedLessonContent.model_validate(self.experiment_lesson(replace="model.fit(X, y)"))

    def test_rejects_invalid_python_edit(self):
        with self.assertRaisesRegex(ValidationError, "must produce valid Python"):
            GeneratedLessonContent.model_validate(self.experiment_lesson(replace="model.fit("))

    def test_accepts_multiline_edit_with_indentation(self):
        source = self.experiment_lesson(find="    print(value)", replace="    print(value * 2)")
        source["sections"][3]["code"] = "for value in [1, 2]:\n    print(value)"
        lesson = GeneratedLessonContent.model_validate(source)
        self.assertEqual(lesson.try_this[0].replace, "    print(value * 2)")


if __name__ == "__main__":
    unittest.main()
