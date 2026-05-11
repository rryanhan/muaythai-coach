import json
import shutil
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from analysis.pipeline import AnalysisPaths, analyze_jab_video, default_output_dir
from analysis.video import ensure_ffmpeg_available
from app.schemas import AnalysisResponse, HealthResponse

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_ROOT = DATA_DIR / "outputs"
ALLOWED_VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Muay Thai Form Coach Analysis API",
    version="0.1.0",
    summary="Server-side video analysis for constrained Muay Thai striking tests.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/outputs", StaticFiles(directory=OUTPUT_ROOT), name="outputs")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/analyze/jab", response_model=AnalysisResponse)
async def analyze_jab(
    video: Annotated[UploadFile, File()],
    stance: Annotated[Literal["orthodox", "southpaw"], Form()] = "orthodox",
    include_overlay: Annotated[bool, Form()] = False,
) -> AnalysisResponse:
    if not ensure_ffmpeg_available():
        raise HTTPException(status_code=500, detail="FFmpeg is not available on PATH.")

    filename = video.filename or "uploaded-video.mp4"
    safe_name = Path(filename).name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_VIDEO_SUFFIXES:
        supported_types = ", ".join(sorted(ALLOWED_VIDEO_SUFFIXES))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video type. Use one of: {supported_types}",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    upload_path = _next_upload_path(UPLOAD_DIR / safe_name)
    with upload_path.open("wb") as destination:
        shutil.copyfileobj(video.file, destination)

    result = analyze_jab_video(
        AnalysisPaths(
            input_video=upload_path,
            output_dir=default_output_dir(upload_path, OUTPUT_ROOT),
        ),
        stance=stance,
        generate_overlay=include_overlay,
        normalize_fps=30,
        normalize_width=540,
    )
    result_payload = json.loads(result.result_path.read_text(encoding="utf-8"))

    return AnalysisResponse(
        status="complete",
        test_type="jab",
        filename=safe_name,
        stance=stance,
        metrics=result_payload["metrics"],
        diagnostics=result_payload["diagnostics"],
        output_dir=str(result.output_dir),
        result_url=_output_url(result.result_path),
        overlay_url=_output_url(result.overlay_path) if result.overlay_path is not None else None,
    )


def _next_upload_path(path: Path) -> Path:
    if not path.exists():
        return path

    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate

    raise HTTPException(status_code=500, detail="Could not allocate an upload filename.")


def _output_url(path: Path) -> str:
    relative = path.relative_to(OUTPUT_ROOT)
    return f"/outputs/{relative.as_posix()}"
