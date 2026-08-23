import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / "Codes"
sys.path.insert(0, str(CODE_DIR))

from PyQt6.QtWidgets import QApplication, QFileDialog  # noqa: E402
import EMC_Fault_Database_Test as application  # noqa: E402


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = application.MainWindows(data_dir=CODE_DIR)

    def tearDown(self):
        self.window.close()

    def test_default_data_files_are_loaded_once(self):
        self.assertEqual(self.window.load_json_file(), 151)
        serialized = {json.dumps(entry, ensure_ascii=False, sort_keys=True) for entry in self.window.readJsonData}
        self.assertEqual(len(serialized), 151)

    def test_loader_deduplicates_entries_from_multiple_files(self):
        entry = {"故障对象": "测试设备", "故障现象": "测试现象"}
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            for filename in ("first.json", "second.json"):
                (data_dir / filename).write_text(json.dumps([entry], ensure_ascii=False), encoding="utf-8")

            self.window.json_dir = data_dir
            self.window.data_files = ("first.json", "second.json")
            self.assertEqual(self.window.load_json_file(), 1)
            self.assertEqual(self.window.readJsonData, [entry])

    def test_empty_table_has_no_exportable_blank_row(self):
        self.window.resetdispTableView()
        self.assertEqual(self.window.dispTableView.model().rowCount(), 0)

    def test_cancelled_export_does_not_attempt_to_write(self):
        with patch.object(QFileDialog, "getSaveFileName", return_value=("", "")):
            self.window.save_userdata_pushButtonClicked()
        self.assertEqual(self.window.infoLabel.text(), "已取消保存")

    def test_ollama_check_requires_the_configured_model(self):
        self.window.llm_model = "qwen2.5:7b"
        completed_process = SimpleNamespace(
            returncode=0,
            stdout="NAME ID SIZE\nqwen2.5:7b abc 1 GB\n",
            stderr="",
        )
        with patch.object(application, "chat", lambda **kwargs: None), patch.object(
            application.subprocess, "run", return_value=completed_process
        ):
            self.assertTrue(self.window.check_ollama_available())
            self.window.llm_model = "deepseek-r1:8b"
            self.assertFalse(self.window.check_ollama_available())

    def test_llm_output_keeps_original_query_and_uses_final_json_array(self):
        content = '<think>示例 ["无关词"]</think>\n["助听设备", "助听器"]'

        keywords = application.extract_keywords_from_llm(content, "助听器")

        self.assertEqual(keywords, ["助听器", "助听设备"])

    def test_invalid_llm_output_falls_back_to_original_query(self):
        self.assertEqual(application.extract_keywords_from_llm("无法解析", "助听器"), ["助听器"])

    def test_exit_button_closes_window(self):
        self.window.show()
        self.window.exitPushButtonClicked()
        self.assertFalse(self.window.isVisible())


if __name__ == "__main__":
    unittest.main()
