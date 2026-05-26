from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict
from backend.tests.conftest import EXAMPLE_DIR, PROJECT_ROOT

GOLDEN_ROOT = Path(__file__).resolve().parent
FIXTURES = GOLDEN_ROOT / "fixtures"

SHIYUN_DOCX = EXAMPLE_DIR / "石云中证1000资产进取一号私募证券投资基金-基金合同(1).docx"
FULU_DOCX = EXAMPLE_DIR / "石云福禄1000指数增强一号私募证券投资基金(1).docx"
GOLDEN_PRODUCT_XLSX = EXAMPLE_DIR / "产品要素 - 副本(1).xlsx"
GOLDEN_FEE_XLSX = EXAMPLE_DIR / "产品运营费率导入模板.xlsx"

SHIYUN_KEY = "石云中证1000资产进取一号私募证券投资基金-基金合同(1).docx"
FULU_KEY = "石云福禄1000指数增强一号私募证券投资基金(1).docx"


def load_contract_expected() -> dict:
    path = FIXTURES / "contract_expected.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def golden_docx_shiyun():
    if not SHIYUN_DOCX.is_file():
        pytest.skip(f"Missing example docx: {SHIYUN_DOCX}")
    return SHIYUN_DOCX


@pytest.fixture(scope="module")
def golden_docx_fulu():
    if not FULU_DOCX.is_file():
        pytest.skip(f"Missing example docx: {FULU_DOCX}")
    return FULU_DOCX


@pytest.fixture(scope="module")
def shiyun_document(golden_docx_shiyun):
    doc = parse_docx(str(golden_docx_shiyun))
    return document_to_dict(doc)


@pytest.fixture(scope="module")
def fulu_document(golden_docx_fulu):
    doc = parse_docx(str(golden_docx_fulu))
    return document_to_dict(doc)


@pytest.fixture(scope="module")
def golden_product_xlsx():
    if not GOLDEN_PRODUCT_XLSX.is_file():
        pytest.skip(f"Missing golden product xlsx: {GOLDEN_PRODUCT_XLSX}")
    return GOLDEN_PRODUCT_XLSX


@pytest.fixture(scope="module")
def golden_fee_xlsx():
    if not GOLDEN_FEE_XLSX.is_file():
        pytest.skip(f"Missing golden fee xlsx: {GOLDEN_FEE_XLSX}")
    return GOLDEN_FEE_XLSX


@pytest.fixture
def tmp_exports(tmp_path, monkeypatch):
    root = tmp_path / "exports"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("backend.app.export.pipeline.exports_dir", lambda: root)
    return root


@pytest.fixture
def contract_expected():
    return load_contract_expected()
