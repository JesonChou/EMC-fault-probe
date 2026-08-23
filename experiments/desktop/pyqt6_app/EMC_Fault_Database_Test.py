import os
import sys
import json
import traceback
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    pd = None
import EMC_Fault_Database
import subprocess

try:
    from ollama import chat
except ImportError:
    chat = None

from PyQt6.QtGui import QIcon, QStandardItemModel, QStandardItem, QFont, QPixmap
from PyQt6.QtWidgets import QMainWindow, QApplication, QHeaderView, QMessageBox, QFileDialog
from PyQt6.QtCore import pyqtSignal, QThread


APP_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_FILES = ("data_1.json", "data_2.json")
DEFAULT_LLM_MODEL = "deepseek-r1:8b"


def normalize_keywords(original_keyword, generated_keywords):
    """始终保留用户原始输入，并移除空白和重复关键词。"""
    keywords = []
    seen = set()
    for keyword in [original_keyword, *generated_keywords]:
        if not isinstance(keyword, str):
            continue
        normalized = keyword.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            keywords.append(normalized)
    return keywords


def extract_keywords_from_llm(content, original_keyword):
    """从 LLM 输出中取得最后一个有效的字符串 JSON 数组。

    DeepSeek-R1 可能先输出思考过程，其中也可能包含方括号；选择最后一个
    有效数组，且无论解析是否成功都保留原始查询，避免模糊搜索破坏精确搜索。
    """
    decoder = json.JSONDecoder()
    generated_keywords = []

    for index, character in enumerate(content):
        if character != "[":
            continue
        try:
            candidate, _ = decoder.raw_decode(content[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, list) and all(isinstance(item, str) for item in candidate):
            generated_keywords = candidate

    return normalize_keywords(original_keyword, generated_keywords)


class LLMWorker(QThread):
    # 定义信号，用于将LLM生成的结果发送回主线程
    keywords_ready = pyqtSignal(list)

    def __init__(self, user_keyword, model_name):
        super().__init__()
        self.user_keyword = user_keyword
        self.model_name = model_name

    def run(self):
        try:
            if chat is None:
                raise RuntimeError("未安装 ollama Python 包")
            prompt = f"""
                请根据用户输入的电磁兼容故障关键词，生成用于模糊搜索的关键词。
                只返回 JSON 数组，不要解释。
                示例：["传导发射", "传导发射超标", "辐射发射超标"]

                输入关键词：
                "{self.user_keyword}"
                """

            resp = chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )

            content = resp["message"]["content"]
            keywords = extract_keywords_from_llm(content, self.user_keyword)

        except Exception as e:
            print("LLM 关键词生成失败:", e)
            keywords = normalize_keywords(self.user_keyword, [])

        # 通过信号发送结果
        self.keywords_ready.emit(keywords)


class MainWindows(QMainWindow, EMC_Fault_Database.Ui_MainWindow):
    def __init__(self, parent=None, data_dir=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.app_dir = Path(data_dir) if data_dir else APP_DIR
        self.BUAALabel.setPixmap(QPixmap(str(self.app_dir / "BUAA-白底蓝字.png")))
        # 初始化显示表格
        self.resetdispTableView()

        # 将“发送”按钮的信号与Slot函数连接
        self.sendPushButton.clicked.connect(self.sendPushButtonClicked)
        # 将“保存数据”按钮的信号与Slot函数连接
        self.saveDataPushButton.clicked.connect(self.save_userdata_pushButtonClicked)
        # 将“退出程序”按钮的信号与Slot函数连接
        self.exitPushButton.clicked.connect(self.exitPushButtonClicked)

        # 全局变量
        # QTableView更新
        self.model = None

        # 字符串匹配
        self.json_dir = self.app_dir
        self.data_files = DEFAULT_DATA_FILES
        self.readJsonData = []  # 读取json文件得到的数据
        self.searchTextfromUserInput = None  # 来自用户输入的要搜索的字段
        self.target_field = None  # 目标字段
        self.search_string = None  # 搜索字段
        self.search_results_exact = []  # 精确字段匹配的结果

        # LLM线程相关变量
        self.llm_model = os.getenv("EMC_OLLAMA_MODEL", DEFAULT_LLM_MODEL)
        self.ollama_available = self.check_ollama_available()
        self.llm_worker = None

        # 数据保存相关变量
        self.save_data_path = ""  # 数据保存的文件路径

        # 显示Ollama状态
        if self.ollama_available:
            self.infoLabel.setText(f"系统已连接至 Ollama（{self.llm_model}），支持模糊搜索")
        else:
            self.infoLabel.setText("未检测到本地ollama服务，使用精确匹配搜索")

    def resetdispTableView(self):
        # 规定水平表头标签
        tableTitle = ['故障对象', '故障现象', '故障原因', '解决方案', '故障等级', '发生频率']
        self.model = QStandardItemModel(0, len(tableTitle))

        # 设置水平表头标签
        self.model.setHorizontalHeaderLabels(tableTitle)

        # 设置表格基础字体及表头字体
        base_font = QFont("HarmonyOS Sans SC Medium", 10)
        self.dispTableView.setFont(base_font)
        header_font = QFont("HarmonyOS Sans SC Medium", 12, QFont.Weight.Bold)
        self.dispTableView.horizontalHeader().setFont(header_font)

        # 将模型设置给dispTableView控件
        self.dispTableView.setModel(self.model)

        # 均匀拉伸所有的列和行
        header = self.dispTableView.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        vheader = self.dispTableView.verticalHeader()
        vheader.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


    def load_json_file(self):
        """加载发布时指定的数据文件，并以完整词条内容去重。"""
        self.readJsonData = []
        seen = set()
        errors = []

        for filename in self.data_files:
            file_path = self.json_dir / filename
            try:
                with file_path.open('r', encoding='utf-8') as file:
                    data = json.load(file)
            except (OSError, json.JSONDecodeError) as error:
                errors.append(f"{filename}: {error}")
                continue

            entries = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                entry_id = json.dumps(entry, ensure_ascii=False, sort_keys=True)
                if entry_id not in seen:
                    seen.add(entry_id)
                    self.readJsonData.append(entry)

        if errors:
            QMessageBox.warning(self, '数据加载警告', "以下数据文件未能加载：\n" + "\n".join(errors))
        return len(self.readJsonData)

    def sendPushButtonClicked(self):
        try:
            # 重置表格
            self.resetdispTableView()
            # 判断输入框是否为空
            if self.userInputTextEdit.toPlainText() != "":
                # 获取用户输入
                user_input = str(
                    self.userInputTextEdit.toPlainText())
                # 禁用发送按钮，防止重复点击
                self.sendPushButton.setEnabled(False)
                # 判断本地LLM大模型是否可用
                # 可用则使用大模型进行关键词模糊匹配
                if self.ollama_available:
                    self.infoLabel.setText("正在生成搜索关键词...")
                    # 创建并启动LLM工作线程
                    self.llm_worker = LLMWorker(user_input, self.llm_model)
                    self.llm_worker.keywords_ready.connect(self.handle_llm_keywords)
                    self.llm_worker.finished.connect(self.llm_thread_finished)
                    self.llm_worker.start()
                # 本地LLM不可用，直接使用精确匹配
                else:
                    self.infoLabel.setText("正在使用精确匹配搜索...")
                    self.do_exact_search([user_input])
                    self.sendPushButton.setEnabled(True)
            else:
                self.infoLabel.setText("请您输入文本！")
        except Exception as e:
            error_details = f"错误类型: {type(e).__name__}\n\n详细错误:\n{traceback.format_exc()}"
            QMessageBox.critical(self, '系统错误', f'发生错误:\n{error_details}')

    def handle_llm_keywords(self, fuzzy_keywords):
        self.search_results_exact = []
        seen = set()
        # 处理LLM返回的关键词并执行搜索
        for search_string in fuzzy_keywords:
            for item in self.readJsonData:
                if self.target_field:
                    if self.target_field in item and isinstance(item[self.target_field], str):
                        if search_string in item[self.target_field]:
                            item_id = json.dumps(item, ensure_ascii=False)
                            if item_id not in seen:
                                seen.add(item_id)
                                self.search_results_exact.append(item)
                else:
                    for value in item.values():
                        if isinstance(value, str) and search_string in value:
                            item_id = json.dumps(item, ensure_ascii=False)
                            if item_id not in seen:
                                seen.add(item_id)
                                self.search_results_exact.append(item)
                            break
        # 更新UI显示结果
        user_input = str(self.userInputTextEdit.toPlainText())
        self.infoLabel.setText(user_input + f"——找到 {len(self.search_results_exact)} 条匹配结果\n")
        # 更新表格
        for i, entry in enumerate(self.search_results_exact):
            self.model.setItem(i, 0, QStandardItem(entry.get('故障对象', '')))
            self.model.setItem(i, 1, QStandardItem(entry.get('故障现象', '')))
            self.model.setItem(i, 2, QStandardItem(entry.get('故障原因', '')))
            self.model.setItem(i, 3, QStandardItem(entry.get('解决方案', '')))
            self.model.setItem(i, 4, QStandardItem(entry.get('故障等级', '')))
            self.model.setItem(i, 5, QStandardItem(entry.get('发生频率', '')))
        self.dispTableView.setModel(self.model)
        self.search_results_exact = []

    def llm_thread_finished(self):
        # LLM线程完成后清理
        self.sendPushButton.setEnabled(True)

    def check_ollama_available(self):
        """检查本地是否有ollama部署的大模型服务"""
        if chat is None:
            print("未安装 ollama Python 包，使用精确匹配搜索")
            return False
        try:
            # 尝试调用ollama list命令检查服务状态
            result = subprocess.run(['ollama', 'list'],
                                    capture_output=True,
                                    text=True,
                                    timeout=5)

            if result.returncode == 0:
                model_names = {
                    line.split()[0]
                    for line in result.stdout.splitlines()[1:]
                    if line.split()
                }
                if self.llm_model in model_names:
                    return True
                else:
                    print(f"警告：Ollama 服务运行中，但未找到模型 {self.llm_model}")
                    return False
            else:
                print(f"ollama服务不可用: {result.stderr}")
                return False

        except FileNotFoundError:
            print("ollama命令未找到，请确认是否已安装")
            return False
        except subprocess.TimeoutExpired:
            print("连接ollama服务超时")
            return False
        except Exception as e:
            print(f"检查ollama服务时出错: {e}")
            return False

    def do_exact_search(self, keywords):
        """执行精确匹配搜索"""
        self.search_results_exact = []
        seen = set()

        for search_string in keywords:
            for item in self.readJsonData:
                if self.target_field:
                    if self.target_field in item and isinstance(item[self.target_field], str):
                        if search_string in item[self.target_field]:
                            item_id = json.dumps(item, ensure_ascii=False)
                            if item_id not in seen:
                                seen.add(item_id)
                                self.search_results_exact.append(item)
                else:
                    for value in item.values():
                        if isinstance(value, str) and search_string in value:
                            item_id = json.dumps(item, ensure_ascii=False)
                            if item_id not in seen:
                                seen.add(item_id)
                                self.search_results_exact.append(item)
                            break

        # 更新UI显示结果
        user_input = str(self.userInputTextEdit.toPlainText())
        self.infoLabel.setText(f"{user_input}——找到 {len(self.search_results_exact)} 条匹配结果")

        for i, entry in enumerate(self.search_results_exact):
            self.model.setItem(i, 0, QStandardItem(entry.get('故障对象', '')))
            self.model.setItem(i, 1, QStandardItem(entry.get('故障现象', '')))
            self.model.setItem(i, 2, QStandardItem(entry.get('故障原因', '')))
            self.model.setItem(i, 3, QStandardItem(entry.get('解决方案', '')))
            self.model.setItem(i, 4, QStandardItem(entry.get('故障等级', '')))
            self.model.setItem(i, 5, QStandardItem(entry.get('发生频率', '')))
        self.dispTableView.setModel(self.model)

        self.search_results_exact = []

    def save_userdata_pushButtonClicked(self):
        try:
            self.save_data_path = QFileDialog.getSaveFileName(
                None,
                "选择目录",
                "",
                "Excel Files (*.xlsx);;All Files (*)"
                # QFileDialog.ShowDirsOnly,
            )
            if not self.save_data_path[0]:
                self.infoLabel.setText("已取消保存")
                return
            if pd is None:
                QMessageBox.warning(self, '缺少依赖', '导出 Excel 需要安装 pandas 和 openpyxl。')
                return

            to_save_model = self.dispTableView.model()
            # 获取行数和列数
            row_count = to_save_model.rowCount()
            col_count = to_save_model.columnCount()
            if row_count > 0 and col_count > 0:
                # 提取表头
                headers = []
                for col in range(col_count):
                    # 获取列标题
                    header = to_save_model.headerData(col, 1)  # 1表示水平表头
                    if header is None:
                        header = f"Column_{col + 1}"
                    headers.append(header)

                # 提取表格数据
                data = []
                for row in range(row_count):
                    row_data = []
                    for col in range(col_count):
                        index = to_save_model.index(row, col)
                        # 0表示显示表头角色的数据
                        value = to_save_model.data(index, 0)
                        row_data.append(value if value is not None else "")
                    data.append(row_data)

                # 使用pandas创建DataFrame并保存为Excel
                df = pd.DataFrame(data, columns=headers)
                df.to_excel(self.save_data_path[0], index=False)
                self.infoLabel.setText("数据保存完成")
            else:
                self.infoLabel.setText("警告：表格数据为空！")
        except Exception as e:
            error_details = f"错误类型: {type(e).__name__}\n\n详细错误:\n{traceback.format_exc()}"
            QMessageBox.critical(self, '系统错误', f'发生错误:\n{error_details}')
            # print(error_details) # 调试用

    def exitPushButtonClicked(self):
        self.close()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainWindows()
    main.setWindowTitle('电磁兼容故障库')
    main.setWindowIcon(QIcon(str(APP_DIR / "BUAA_logo_2048px.png")))
    main.show()

    main.load_json_file()

    sys.exit(app.exec())
