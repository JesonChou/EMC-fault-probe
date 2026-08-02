<h1 align="center">电磁兼容故障库（中文资料）</h1>


> [!NOTE]
>
> **项目愿景**：构建一个基于 **RAG（检索增强生成）与长期记忆系统**的电磁兼容故障库 **AGENT** —— 沿"数据来源 → 知识加工 → 结构化存储 → 功能迭代"主线，将分散、非结构化的 EMC 故障资料沉淀为结构化、可复用的故障知识体系，由 LLM 驱动实现智能查询、故障诊断辅助、知识动态增量构建与更新提示。
>
> **当前进度**：故障库基础版已完成 —— 从文献、网页与在线 LLM 三渠道收集数据，经清洗、LLM 结构化提取与合并去重，入库约 200 条"故障—原因—方案"词条；PyQt6 桌面程序实现关键词检索、本地 Ollama LLM 查询扩展与 Excel 导出。基于 ChromaDB 的 RAG 语义检索已有实验实现（见`Codes/Embedding_Test.py` 与 `Codes/emc_vector_db/`）；AGENT 化（长期记忆、诊断辅助、增量入库）为后续迭代方向。

<p align="center">
  <strong>简体中文</strong>
  &nbsp;·&nbsp;
  <a href="./README.en.md">English</a>
  &nbsp;·&nbsp;
  <a href="./docs/项目过程与细节记录.md">项目过程与细节记录</a>
</p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/github/license/JesonChou/EMC-fault-probe?style=flat-square&color=8b949e&labelColor=161b22" alt="license"/></a>
  <a href=".github/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/JesonChou/EMC-fault-probe/ci.yml?style=flat-square&label=ci&labelColor=161b22&logo=githubactions&logoColor=white" alt="CI"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10+-5fa04e?style=flat-square&labelColor=161b22&logo=python&logoColor=white" alt="python"/></a>
  <a href="https://github.com/JesonChou/EMC-fault-probe/stargazers"><img src="https://img.shields.io/github/stars/JesonChou/EMC-fault-probe?style=flat-square&color=dbab09&labelColor=161b22&logo=github&logoColor=white" alt="stars"/></a>
  <a href="https://github.com/JesonChou/EMC-fault-probe/graphs/contributors"><img src="https://img.shields.io/github/contributors/JesonChou/EMC-fault-probe?style=flat-square&color=bc8cff&labelColor=161b22&logo=github&logoColor=white" alt="contributors"/></a>
  <a href="https://github.com/JesonChou/EMC-fault-probe/issues"><img src="https://img.shields.io/github/issues/JesonChou/EMC-fault-probe?style=flat-square&color=58a6ff&labelColor=161b22&logo=github&logoColor=white" alt="issues"/></a>
  <a href="./CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square&labelColor=161b22" alt="PRs welcome"/></a>
</p>
<h3 align="center">输入中文故障描述，一键检索"故障—原因—方案"</h3>
<p align="center">从文献、网页与在线 LLM 三渠道收集 EMC 故障案例，经数据清洗与 LLM 结构化提取，构建约 200 条结构化词条；桌面程序支持精确检索、LLM 语义扩展与 Excel 导出。</p>

<p align="center">
  <img src="./README.assets/main.png" alt="故障库查询程序主界面" width="720"/>
</p>
<p align="center">
  <img src="./README.assets/llm1.png" alt="LLM 语义扩展检索" width="360"/>
  <img src="./README.assets/llm2.png" alt="LLM 检索结果" width="360"/>
</p>
> [!NOTE]
>
> 未安装本地 Ollama 模型时，程序自动降级为普通关键词检索，全部功能不受影响。

## Install

要求 Python 3.10+，支持 Windows / Linux / macOS。

```powershell
python -m pip install -r requirements.txt
cd Codes
python EMC_Fault_Database_Test.py
```

> [!NOTE]
>
> 程序仅加载发布数据文件 `data_1.json` 与 `data_2.json`，并在加载时按完整词条去重。`12.29.json` 是 `data_2.json` 的历史重复副本，仅供追溯，不参与运行时检索。

运行测试：

```powershell
python -m pip install -r requirements-dev.txt pytest
python -m pytest tests/ -v              # 应用级测试（仓库根目录）
cd Codes; python -m pytest tests/ -v    # 代码级测试
```

打包 Windows 可执行文件（输出到未跟踪的 `artifacts/`，避免覆盖历史发布文件）：

```powershell
python -m pip install -r requirements-dev.txt
cd Codes
pyinstaller --clean --noconfirm --distpath ..\artifacts\dist --workpath ..\artifacts\build EMC_Fault_Database_Test.spec
```

## Configuration

本地语义扩展是可选功能，通过 [Ollama](https://ollama.com/) 提供。

| 配置项 | 说明 |
|:-:|:-:|
| Ollama 服务 | 安装并启动 Ollama，`ollama run deepseek-r1:8b` 下载默认模型 |
| `EMC_OLLAMA_MODEL` | 环境变量，指定本地已安装的其他模型（默认 `deepseek-r1:8b`） |

```cmd
ollama run deepseek-r1:8b
```

```powershell
$env:EMC_OLLAMA_MODEL = "qwen2.5:7b"   # 可选，覆盖默认模型
```

程序启动时自动探测 Ollama 服务与可用模型；检测到后将用户输入交由 LLM 扩展为多个相关关键词再检索，提高模糊查询召回率。模型训练实验与提示词细节见 [docs/项目过程与细节记录.md](./docs/项目过程与细节记录.md)。

## What makes it different

数据是核心资产：本项目不依赖现成数据集，而是从三类来源（期刊论文与行业报告、网页资料、在线 LLM 问答）收集故障案例，逐条完成"收集 → 清洗 → LLM 结构化提取 → 合并去重 → 入库"的完整流水线，最终形成故障现象、故障原因、解决方案一一对应的结构化词条库，并配套桌面检索程序落地使用。

- 六字段结构化词条：故障对象 / 故障现象 / 故障原因 / 解决方案 / 故障等级 / 发生频率
- 按完整词条去重，保证检索结果唯一
- `QTableView` 表格化展示，一键导出 `.xlsx` 存档
- LLM 查询扩展在后台线程（`QThread`）执行，不阻塞界面

## How it compares

|                                | 纯关键词检索 | 关键词 + LLM 语义扩展 |
|:------------------------------:|:---:|:---:|
| 精确匹配查询                  | 支持 | 支持 |
| 近义/模糊语义匹配             | —   | 支持 |
| 本地部署，数据不出本机        | 支持 | 支持 |
| 离线可用（无 Ollama）         | 支持 | 自动降级为关键词检索 |
| 额外依赖                      | 无 | Ollama + 本地模型 |

## Documentation

- [**项目过程与细节记录**](./docs/项目过程与细节记录.md) — 完整开发过程：数据收集、预处理、LLM 提取、故障库构建、程序实现与代码讲解
- [**README.en.md**](./README.en.md) — English version
- [**CONTRIBUTING.md**](./CONTRIBUTING.md) — 贡献指南（GitHub Flow）
- [**LICENSE**](./LICENSE) — MIT License

## Community

本项目按社区规范开放协作：

- 报告 Bug 或功能建议 → [GitHub Issues](https://github.com/JesonChou/EMC-fault-probe/issues)
- 提交代码 → 遵循 [CONTRIBUTING.md](./CONTRIBUTING.md)：从 `main` 创建 `feat/xxx` 分支，完成后提交 Pull Request
- 代码质量门槛 → `ruff check Codes/` 通过，新功能附带测试；CI 在 Ubuntu / Windows 上对 Python 3.11 / 3.12 自动执行 lint 与 pytest

## Non-goals

本项目定位明确，以下内容不在范围内：

- **多语言语料**。当前仅收录中文资料；英文 EMC 语料可作为后续扩展方向。
- **Web / 移动端**。以 Windows 桌面程序为主要交付形态（支持 PyInstaller 打包 `.exe`），不做在线服务。
- **大规模数据库系统**。JSON 文件存储已满足约 200 条词条的结构化查询需求，不引入 MySQL / MongoDB 等外部服务。
- **商业化**。MIT协议，若有商业需求，可直接联系开发者说明。

## Star History

<a href="https://www.star-history.com/?repos=JesonChou%2FEMC-fault-probe&type=date&legend=top-left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=JesonChou/EMC-fault-probe&type=date&theme=dark&legend=top-left" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=JesonChou/EMC-fault-probe&type=date&legend=top-left" />
    <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=JesonChou/EMC-fault-probe&type=date&legend=top-left" />
  </picture>
</a>

## Support

如果这个项目对你有帮助，欢迎给仓库点一个 Star；遇到问题请先查阅 [Issues](https://github.com/JesonChou/EMC-fault-probe/issues) 或直接提问。

## Acknowledgments

致谢：

- [**JesonChou**](https://github.com/JesonChou)
- [**eternalweightlessness**](https://github.com/eternalweightlessness)

- [**421951168-cyber**](https://github.com/421951168-cyber)
- [**JGCF-XDB**](https://github.com/JGCF-XDB)

同时感谢 [Ollama](https://ollama.com/) 本地大模型平台与 [PyQt](https://www.riverbankcomputing.com/software/pyqt/) 桌面框架，以及提供数据支持的在线 LLM（DeepSeek、ChatGPT）与课程参考资料。

<p align="center">
  <a href="https://github.com/JesonChou/EMC-fault-probe/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=JesonChou/EMC-fault-probe&max=100&columns=12" alt="Contributors to JesonChou/EMC-fault-probe" width="720"/>
  </a>
</p>

---

<p align="center">
  <sub>MIT — see <a href="./LICENSE">LICENSE</a></sub>
  <br/>
  <sub>Built by group 20 at <a href="https://github.com/JesonChou/EMC-fault-probe">JesonChou/EMC-fault-probe</a></sub>
</p>
