"""Harbor adapter that predicts all six FontBench typography attributes.

    harbor run --path dataset/fontbench-1/tasks --agent baseline.harbor_agent:BaselineVLMAgent --model gemini-2.5-flash
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from PIL import Image

from baseline.evaluator import TypographicPrediction
from baseline.providers import parse_prediction

try:
    from harbor.agents.base import BaseAgent
    from harbor.environments.base import BaseEnvironment
    from harbor.models.agent.context import AgentContext
except ModuleNotFoundError as exc:
    if exc.name != "harbor":
        raise

    # Keep the optional adapter importable for local tests without installing Harbor.
    class BaseAgent:  # type: ignore[no-redef]
        def __init__(self, model_name: str, **kwargs: Any):
            self.model_name = model_name

    BaseEnvironment = Any  # type: ignore[misc,assignment]
    AgentContext = Any  # type: ignore[misc,assignment]


class BaselineVLMAgent(BaseAgent):
    """Zero-shot structured VLM agent using Harbor's async file transfer API."""

    def __init__(
        self,
        model: str | None = None,
        mock: bool = False,
        model_name: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(model_name=model_name or model or "gemini-2.5-flash", **kwargs)
        self.mock = mock
        self._client = None

        if not self.mock:
            from google import genai
            from google.genai import types
            self._client = genai.Client(http_options=types.HttpOptions(timeout=60_000))

    @staticmethod
    def name() -> str:
        return "fontbench-baseline"

    def version(self) -> str:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        """Model calls run on the host, so no container setup is needed."""

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        """Upload model answers as data; the verifier gives invalid answers zero credit."""
        with TemporaryDirectory(prefix="fontbench-agent-") as directory:
            image_path = Path(directory) / "sample.png"
            await environment.download_file(source_path="/workspace/sample.png", target_path=image_path)
            if self.mock:
                prediction = TypographicPrediction(
                    font="Arial", category="non-serif", weight="regular", modifier="regular",
                    kerning="normal", line_height="normal",
                )
                output = prediction.model_dump_json()
            else:
                from google.genai import types
                with Image.open(image_path) as image:
                    response = await self._client.aio.models.generate_content(
                        model=self.model_name,
                        contents=[image, instruction],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=TypographicPrediction,
                            temperature=0.0,
                            max_output_tokens=1024,
                        ),
                    )
                output = response.text or ""
                try:
                    output = TypographicPrediction.model_validate(parse_prediction(output)).model_dump_json()
                except ValueError:
                    pass  # The verifier scores invalid model answers as zero.
            output_path = Path(directory) / "output.json"
            output_path.write_text(output + "\n", encoding="utf-8")
            await environment.upload_file(source_path=output_path, target_path="/workspace/output.json")
