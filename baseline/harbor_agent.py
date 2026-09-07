"""Harbor BaseAgent Adapter for Baseline VLM.

Allows FontBench tasks to be run directly via Harbor CLI:
    harbor run -d fontbench-1 --agent baseline.harbor_agent:BaselineVLMAgent --ak model=gemini-2.5-flash
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import Any, Optional

try:
    from harbor.agents.base import BaseAgent
    from harbor.environments.base import BaseEnvironment
    from harbor.models.agent.context import AgentContext
except ImportError:
    # Minimal fallback interface for standalone execution
    class BaseAgent:  # type: ignore
        session_id: Optional[str] = None
        def __init__(self, **kwargs: Any):
            pass

    class BaseEnvironment:  # type: ignore
        def exec(self, command: str, **kwargs: Any):
            pass

    class AgentContext:  # type: ignore
        session_id: str = "mock-session"


class BaselineVLMAgent(BaseAgent):
    """Zero-shot VLM Agent conforming to Harbor's BaseAgent interface."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        mock: bool = False,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.model_name = model
        self.mock = mock
        self._client = None

        if not self.mock:
            from google import genai
            self._client = genai.Client()

    def run(
        self,
        instruction: str,
        environment: Any,
        context: Optional[Any] = None,
    ) -> None:
        """Execute task inside Harbor environment.
        
        Reads sample.png from /workspace or local dir, calls the VLM,
        and writes the predicted font name to /workspace/output.txt.
        """
        prompt = (
            "Examine the rendered text in the provided image. "
            "Identify the primary font family used to typeset this text. "
            "Output only the canonical font name (e.g., Arial, Times New Roman, Roboto)."
        )

        # In Harbor, files can be fetched or read directly from container
        # If running locally or with mock environment:
        candidate_image_paths = [
            "/workspace/sample.png",
            "./sample.png",
            "environment/sample.png",
        ]
        
        image_path = None
        for p in candidate_image_paths:
            if os.path.exists(p):
                image_path = p
                break

        if not image_path:
            # Try pulling from environment if it supports file download
            if hasattr(environment, "read_file"):
                raw_bytes = environment.read_file("/workspace/sample.png")
                prediction = self._predict_bytes(raw_bytes, prompt)
            else:
                prediction = "Unknown"
        else:
            prediction = self._predict_file(image_path, prompt)

        # Write output.txt
        write_cmd = f"echo '{prediction}' > /workspace/output.txt"
        if hasattr(environment, "exec"):
            environment.exec(write_cmd)
        else:
            # Fallback to local filesystem write
            target = "/workspace/output.txt" if os.path.exists("/workspace") else "output.txt"
            with open(target, "w", encoding="utf-8") as f:
                f.write(prediction.strip() + "\n")

    def _predict_file(self, path: str, prompt: str) -> str:
        if self.mock:
            return "Helvetica"

        from PIL import Image
        img = Image.open(path)
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=[img, prompt]
            )
            return response.text.strip() if response.text else ""
        except Exception as e:
            return f"Error: {e}"

    def _predict_bytes(self, raw_bytes: bytes, prompt: str) -> str:
        if self.mock:
            return "Helvetica"

        from PIL import Image
        img = Image.open(io.BytesIO(raw_bytes))
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=[img, prompt]
            )
            return response.text.strip() if response.text else ""
        except Exception as e:
            return f"Error: {e}"
