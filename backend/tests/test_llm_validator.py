import asyncio

from pydantic import BaseModel

from backend.app.validate.llm_validator import run_llm_validation, run_llm_validation_sync
from backend.app.validate.schemas import ValidationBatchItem, ValidationBatchResponse


class MockLlmClient:
    def __init__(self, responses: list[ValidationBatchResponse] | None = None):
        self._responses = list(responses or [])
        self._call = 0

    @property
    def available(self) -> bool:
        return True

    @property
    def model_name(self) -> str:
        return "mock-model"

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
    ) -> BaseModel:
        if self._responses:
            resp = self._responses[min(self._call, len(self._responses) - 1)]
            self._call += 1
            return resp
        return response_model(items=[])


def test_contradiction_returns_fail():
    extraction = {
        "product_elements": {
            "管理人": {
                "value": "北京石云科技有限公司",
                "snippet": "本基金管理人登记为海南正仁量化私募基金管理有限公司。",
            },
        }
    }
    mock_response = ValidationBatchResponse(
        items=[
            ValidationBatchItem(
                field="管理人",
                status="fail",
                reason="摘录为海南正仁，与值北京石云矛盾",
            )
        ]
    )
    client = MockLlmClient([mock_response])
    result = asyncio.run(
        run_llm_validation(extraction, None, {}, llm_client=client)
    )
    assert result.skipped is False
    assert result.summary.get("fail", 0) >= 1
    assert any(i.status == "fail" for i in result.items)


def test_consistent_returns_pass():
    extraction = {
        "product_elements": {
            "管理人": {
                "value": "海南正仁量化私募基金管理有限公司",
                "snippet": "基金管理人：海南正仁量化私募基金管理有限公司，依法登记。",
            },
        }
    }
    mock_response = ValidationBatchResponse(
        items=[
            ValidationBatchItem(
                field="管理人",
                status="pass",
                reason="全称出现在摘录中",
            )
        ]
    )
    client = MockLlmClient([mock_response])
    result = run_llm_validation_sync(extraction, None, {}, llm_client=client)
    assert result.summary.get("pass", 0) >= 1


class UnavailableClient:
    @property
    def available(self) -> bool:
        return False


def test_llm_off_returns_skipped():
    result = run_llm_validation_sync({}, None, {}, llm_client=UnavailableClient())
    assert result.skipped is True
    assert result.items == []
