"""Load explicit model selections without resolving aliases or reading API keys."""

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


Price = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class _ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    provider: Literal["anthropic", "openai", "google"]
    model: str = Field(pattern=r"^\S+$")
    display_name: str = Field(min_length=1)
    api_key_env: str = Field(pattern=r"^[A-Z_][A-Z0-9_]*$")
    source_url: HttpUrl
    pricing_source_url: HttpUrl | None = None
    pricing_notes: str = ""
    notes: str = ""
    base_url: HttpUrl | None = None
    input_per_m: Price | None = None
    output_per_m: Price | None = None
    max_output_tokens: int = Field(default=1024, gt=0)
    enabled: bool = True


class _Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: int
    verified_at: date
    models: list[_ModelConfig]

    @field_validator("version")
    @classmethod
    def supported_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("Unsupported model catalog version")
        return value


def load_model_config(path: str | Path = "config/models.json") -> list[dict]:
    """Validate the catalog and return enabled models in their configured order."""
    catalog = _Catalog.model_validate_json(Path(path).read_text(encoding="utf-8"))
    ids = [model.id for model in catalog.models]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate model configuration IDs")
    enabled = [model for model in catalog.models if model.enabled]
    if any(count > 5 for count in Counter(model.provider for model in enabled).values()):
        raise ValueError("Configure at most five enabled models per provider")
    return [model.model_dump(mode="json") for model in enabled]
