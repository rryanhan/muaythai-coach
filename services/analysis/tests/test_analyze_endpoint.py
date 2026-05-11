import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

import app.main as main


def test_analyze_jab_upload_returns_pipeline_result(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "outputs"
    upload_dir = tmp_path / "uploads"
    output_dir = output_root / "sample"
    output_dir.mkdir(parents=True)
    result_path = output_dir / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "metrics": {
                    "detected_reps": 10,
                    "rear_hand_drops": 1,
                    "hand_dip_telegraphs": 2,
                    "average_return_time_ms": 180.0,
                    "reps": [],
                },
                "diagnostics": {"pose_visibility_ratio": 0.98},
            }
        ),
        encoding="utf-8",
    )

    def fake_analyze_jab_video(*_: Any, **__: Any) -> SimpleNamespace:
        return SimpleNamespace(
            output_dir=output_dir,
            result_path=result_path,
            overlay_path=None,
        )

    monkeypatch.setattr(main, "OUTPUT_ROOT", output_root)
    monkeypatch.setattr(main, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(main, "ensure_ffmpeg_available", lambda: True)
    monkeypatch.setattr(main, "analyze_jab_video", fake_analyze_jab_video)

    client = TestClient(main.app)
    response = client.post(
        "/analyze/jab",
        data={"stance": "orthodox"},
        files={"video": ("sample.mp4", b"video-bytes", "video/mp4")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "complete"
    assert payload["metrics"]["detected_reps"] == 10
    assert payload["overlay_url"] is None
