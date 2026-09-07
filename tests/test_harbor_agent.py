"""Harbor adapter contract tests using isolated, asynchronous file transfers."""

import asyncio
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from baseline.harbor_agent import BaselineVLMAgent


class Environment:
    def __init__(self):
        self.downloads = []
        self.uploads = {}

    async def download_file(self, source_path, target_path):
        self.downloads.append(source_path)
        from PIL import Image
        Image.new("RGB", (2, 2)).save(target_path)

    async def upload_file(self, source_path, target_path):
        self.uploads[target_path] = Path(source_path).read_text()


def test_harbor_interface_is_complete_and_asynchronous(tmp_path):
    agent = BaselineVLMAgent(mock=True, logs_dir=tmp_path)
    assert callable(getattr(agent, "name", None)), "Harbor requires the abstract name method"
    assert agent.name() == "fontbench-baseline"
    assert agent.version()
    assert inspect.iscoroutinefunction(agent.setup)
    assert inspect.iscoroutinefunction(agent.run)


def test_harbor_model_name_is_respected(tmp_path):
    agent = BaselineVLMAgent(mock=True, model_name="configured-model", logs_dir=tmp_path)
    assert agent.model_name == "configured-model"


def test_mock_transfers_image_and_six_field_json(tmp_path):
    environment = Environment()
    agent = BaselineVLMAgent(mock=True, logs_dir=tmp_path)
    asyncio.run(agent.run("Identify all typography properties.", environment, SimpleNamespace()))
    assert environment.downloads == ["/workspace/sample.png"]
    prediction = json.loads(environment.uploads["/workspace/output.json"])
    assert set(prediction) == {"font", "category", "weight", "modifier", "kerning", "line_height"}
    assert prediction["font"] == "Arial"


def test_model_output_is_json_data_and_instruction_is_used(tmp_path):
    prediction = {
        "font": "A'; touch /tmp/injected; echo '", "category": "serif", "weight": "bold",
        "modifier": "italic", "kerning": "tight", "line_height": "loose",
    }
    calls = []

    async def generate_content(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text=json.dumps(prediction))

    agent = BaselineVLMAgent(mock=True, logs_dir=tmp_path)
    agent.mock = False
    agent._client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    environment = Environment()
    asyncio.run(agent.run("Task-specific instruction.", environment, SimpleNamespace()))
    assert calls[0]["contents"][1] == "Task-specific instruction."
    assert calls[0]["config"].response_mime_type == "application/json"
    assert json.loads(environment.uploads["/workspace/output.json"]) == prediction


def test_model_errors_propagate_without_uploading_a_fake_prediction(tmp_path):
    async def generate_content(**kwargs):
        raise RuntimeError("provider unavailable")

    agent = BaselineVLMAgent(mock=True, logs_dir=tmp_path)
    agent.mock = False
    agent._client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    environment = Environment()
    with pytest.raises(RuntimeError, match="provider unavailable"):
        asyncio.run(agent.run("Identify typography.", environment, SimpleNamespace()))
    assert environment.uploads == {}


@pytest.mark.parametrize("response", ["not JSON", "[]", "null", "{}", '{"font":"Arial"}'])
def test_invalid_model_response_is_not_uploaded(tmp_path, response):
    from pydantic import ValidationError

    async def generate_content(**kwargs):
        return SimpleNamespace(text=response)

    agent = BaselineVLMAgent(mock=True, logs_dir=tmp_path)
    agent.mock = False
    agent._client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    environment = Environment()
    with pytest.raises(ValidationError):
        asyncio.run(agent.run("Identify typography.", environment, SimpleNamespace()))
    assert environment.uploads == {}
