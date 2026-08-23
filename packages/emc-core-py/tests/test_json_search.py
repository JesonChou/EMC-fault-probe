"""Unit tests for the pure-Python JSON search helper and data integrity.

CI 中无法运行依赖本机 Ollama 服务或图形界面的脚本（Embedding_Test.py、
LLMTest.py、EMC_Fault_Database_Test.py），因此只测试不依赖外部服务的部分：
JSON 搜索函数与数据文件完整性。
"""

import json
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "published" / "v1"
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from emc_core.retrieval.json_search import search_json_by_string_enhanced

REQUIRED_FIELDS = ("故障对象", "故障现象", "故障原因", "解决方案", "故障等级", "发生频率")
DATA_FILES = ("data_1.json", "data_2.json")


def _load(file_name: str) -> list:
    with open(DATA_DIR / file_name, encoding="utf-8") as f:
        return json.load(f)


# ---------- search_json_by_string_enhanced ----------

def test_search_matches_across_all_fields():
    tmp = DATA_DIR / "data_1.json"
    results = search_json_by_string_enhanced(str(tmp), "干扰")
    assert results, "should find at least one entry containing 干扰"


def test_search_with_target_field_only():
    tmp = DATA_DIR / "data_1.json"
    results = search_json_by_string_enhanced(str(tmp), "严重", target_field="故障等级")
    assert results
    assert all(r["故障等级"] == "严重" for r in results)


def test_search_no_match_returns_empty():
    tmp = DATA_DIR / "data_1.json"
    assert search_json_by_string_enhanced(str(tmp), "不存在的关键词xyz") == []


def test_search_missing_file_returns_empty():
    assert search_json_by_string_enhanced(str(DATA_DIR / "nope.json"), "x") == []


def test_search_invalid_json_returns_empty(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    assert search_json_by_string_enhanced(str(bad), "x") == []


# ---------- data integrity ----------

@pytest.mark.parametrize("file_name", DATA_FILES)
def test_data_files_have_required_fields(file_name):
    data = _load(file_name)
    assert data, f"{file_name} should not be empty"
    for i, item in enumerate(data):
        missing = [k for k in REQUIRED_FIELDS if k not in item]
        assert not missing, f"{file_name}[{i}] missing keys: {missing}"


@pytest.mark.parametrize("file_name", DATA_FILES)
def test_data_files_have_unique_ids(file_name):
    data = _load(file_name)
    # 用故障对象+故障现象 前 20 字近似判断无重复词条
    seen = set()
    for item in data:
        key = (item["故障对象"], item["故障现象"][:20])
        assert key not in seen, f"duplicate entry in {file_name}: {key}"
        seen.add(key)
