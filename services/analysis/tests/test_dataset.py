import json
from pathlib import Path

from analysis.dataset import load_manifest


def test_load_manifest_reads_clip_labels(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dataset": "sample_dataset",
                "stance": "orthodox",
                "clips": [
                    {
                        "filename": "strike_clean_jab_orthodox.MOV",
                        "category": "clean_strike",
                        "primary_action": "jab",
                        "expected_reps": 10,
                        "expected_issues": [],
                        "use_for": ["jab_detection"],
                        "notes": "Clean jab reference.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    dataset, stance, clips = load_manifest(manifest_path)

    assert dataset == "sample_dataset"
    assert stance == "orthodox"
    assert len(clips) == 1
    assert clips[0].filename == "strike_clean_jab_orthodox.MOV"
    assert clips[0].expected_reps == 10
