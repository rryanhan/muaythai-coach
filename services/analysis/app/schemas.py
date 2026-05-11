from typing import Any, Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class AnalysisResponse(BaseModel):
    status: Literal["complete"]
    test_type: str
    filename: str
    stance: Literal["orthodox", "southpaw"]
    metrics: dict[str, Any]
    diagnostics: dict[str, Any]
    output_dir: str
    result_url: str
    overlay_url: str | None
