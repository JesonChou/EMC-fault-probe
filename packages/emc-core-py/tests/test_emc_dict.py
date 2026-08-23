"""EMC 分词词典完整性测试。

验证 emc_dict.py 中的领域术语集合非空且无重复（术语库是模糊
搜索与分词的依据，属于项目的核心数据资产）。
"""

import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from emc_core.retrieval.emc_dict import EMC_DICT


def test_emc_dict_non_empty():
    assert len(EMC_DICT) > 0


def test_emc_dict_no_duplicates():
    assert len(EMC_DICT) == len(set(EMC_DICT))


def test_emc_dict_is_str_set():
    assert all(isinstance(w, str) and w.strip() for w in EMC_DICT)
