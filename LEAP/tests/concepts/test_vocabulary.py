import json

from leap.concepts import ConceptVocabulary

VOCABULARY_PATH = "configs/concepts/concept_vocabulary_v2.json"


def test_vocabulary_maps_every_observed_stage_and_objective():
    vocabulary = ConceptVocabulary(VOCABULARY_PATH)
    with open("data/action/processed/action_data.jsonl", encoding="utf-8") as file:
        records = [json.loads(line) for line in file if line.strip()]

    for record in records:
        assert vocabulary.concepts_for_stage(record["task"], record["stage"])
        for objective in record.get("learning_objectives", []):
            assert vocabulary.concepts_for_objective(record["task"], objective)


def test_vocabulary_encodes_concepts_into_64_dimensions():
    vocabulary = ConceptVocabulary(VOCABULARY_PATH)
    encoded = vocabulary.encode(["feature_representation", "text_vectorization"])

    assert encoded.shape == (64,)
    assert encoded.sum().item() == 2
    assert encoded[vocabulary.indices["feature_representation"]].item() == 1


def test_vocabulary_defines_all_64_dimensions():
    vocabulary = ConceptVocabulary(VOCABULARY_PATH)
    assert vocabulary.capacity == 64
    assert len(vocabulary.concepts) == 64
    assert set(vocabulary.indices.values()) == set(range(64))
