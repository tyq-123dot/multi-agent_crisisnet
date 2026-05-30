# CrisisNet - 城市灾害多智能体应急响应系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" />
  <img src="https://img.shields.io/badge/Redis-7-red?logo=redis" />
  <img src="https://img.shields.io/badge/ChromaDB-0.4-green?logo=chroma" />
  <img src="https://img.shields.io/badge/License-MIT-yellow" />
</p>

CrisisNet 是一个基于混合智能体架构的城市灾害应急响应系统，融合云端 LLM、本地模型与规则引擎，实现高可用、可追溯、人机协同的应急决策。

---

## ✨ 核心特性

- **多智能体异步协作**：EOC 指挥中心 + 4 个专业智能体，基于 Redis 消息总线异步通信
- **三级降级机制**：云 API → Ollama 本地模型 → 规则引擎，极端场景仍可运行
- **历史案例检索**：ChromaDB 向量存储 + Few-shot 学习，提升决策一致性
- **人在回路审核**：LEVEL 1-4 分级审批，高风险决策人工把关
- **决策全链路审计**：SQLite 持久化存储，支持时间/角色/关键词多维度查询
- **多源数据接入**：可扩展的适配器架构，支持 GIS/IoT/社交媒体/热线/气象

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据接入层                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────┐│
│  │  GIS    │  │  IoT    │  │  Social │  │  Hotline││Weather││
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └───┬───┘│
└───────┼────────────┼────────────┼────────────┼────────────┼────┘
        │            │            │            │            │
        └────────────┴────────────┴────────────┴────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│                    消息总线 (Redis Pub/Sub)                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼───────┐   ┌──────▼──────┐   ┌───────▼───────┐
│  EOC 指挥中心 │   │  消防救援   │   │   医疗救援    │
└───────┬───────┘   └──────┬──────┘   └───────┬───────┘
        │                  │                  │
┌───────▼───────┐   ┌──────▼──────┐
│   物流调度    │   │  公共信息    │
└───────────────┘   └─────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        决策支持层                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐        │
│  │  案例检索    │  │  LLM 降级    │  │   决策审计      │        │
│  │  (ChromaDB) │  │  (Fallback)  │  │   (SQLite)      │        │
│  └──────────────┘  └──────────────┘  └─────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
crisisnet/
├── crisisnet_common/         # 公共模块
│   ├── models.py             # 数据模型和消息定义
│   ├── config.py             # 配置管理
│   ├── llm_client.py         # LLM 客户端封装
│   ├── llm_fallback.py       # LLM 降级客户端
│   ├── rule_engine.py        # 规则引擎
│   ├── case_database.py      # 历史案例库
│   ├── data_adapters.py      # 数据适配器
│   ├── social_media_processor.py  # 社交媒体处理
│   ├── human_in_the_loop.py  # 人在回路审核
│   ├── decision_audit.py     # 决策审计
│   └── ...
├── agents/                   # 智能体实现
│   ├── base.py               # 智能体基类
│   ├── eoc.py                # 应急指挥中心
│   ├── fire_rescue.py        # 消防救援
│   ├── medical.py            # 医疗救援
│   ├── logistics.py          # 物流调度
│   └── public_info.py        # 公共信息
├── env_sim/                  # 环境模拟器
│   └── environment.py
├── frontend/                 # 前端
│   └── src/components/
│       └── CommanderPanel.js # 指挥官控制台
├── data/                     # 数据目录
│   └── case_db/              # ChromaDB 数据
├── logs/                     # 日志目录
├── main.py                   # 主程序入口
├── config.yaml               # 配置文件
├── requirements.txt          # 依赖列表
├── INTERVIEW_GUIDE.md        # 面试指南
├── INTERVIEW_CHEAT_SHEET.md  # 面试备忘卡
└── RESUME_DESCRIPTION.md     # 简历描述
```

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- Redis 7+
- (可选) Ollama 本地模型

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动 Redis

使用 Docker 启动（推荐）：

```bash
docker run -d -p 6379:6379 --name crisisnet-redis redis:7
```

或者使用本地安装的 Redis。

### 4. 配置 API 密钥

编辑 `config.yaml`，填入你的 API 密钥。

#### 使用 DeepSeek（推荐）

```yaml
llm:
  base_url: "https://api.deepseek.com/v1"
  api_key: "your_deepseek_api_key_here"

agents:
  eoc:
    llm_model: "deepseek-chat"
  fire_rescue:
    llm_model: "deepseek-chat"
  # ... 其他 agent 也使用 deepseek-chat
```

#### 使用 OpenAI

```yaml
llm:
  base_url: "https://api.openai.com/v1"
  api_key: "your_openai_api_key_here"

agents:
  eoc:
    llm_model: "gpt-4o-mini"
  # ...
```

#### 使用 Ollama 本地模型

首先启动 Ollama 服务并拉取模型：

```bash
ollama pull llama3:8b
```

然后运行时指定参数：

```bash
python main.py --fallback-mode ollama_first
```

### 5. 运行仿真

```bash
# 默认模式（云优先）
python main.py

# 规则引擎模式（无需 API 密钥）
python main.py --fallback-mode rule_only

# 调试模式
python main.py --debug
```

---

## ⚙️ 配置说明

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--config` | 配置文件路径 | `config.yaml` |
| `--debug` | 开启调试日志 | `False` |
| `--fallback-mode` | LLM 降级模式 | `cloud_first` |
| `--use-mock-data` | 使用模拟数据适配器 | `True` |

### LLM 降级模式

| 模式 | 说明 |
|------|------|
| `cloud_only` | 仅使用云 API，失败即报错 |
| `cloud_first` | 优先云 API，失败自动切换 |
| `ollama_first` | 优先本地 Ollama |
| `rule_only` | 仅使用规则引擎 |
| `hybrid` | 混合模式 |

---

## 🤖 智能体分工

| 智能体 | 职责 | 决策间隔 |
|--------|------|----------|
| **EOC** | 全局协调、资源仲裁、优先级设置 | 5 ticks |
| **FireRescue** | 灭火、救援被困人员 | 2 ticks |
| **Medical** | 医疗救援、救护车调度 | 2 ticks |
| **Logistics** | 物资运输、路径规划 | 3 ticks |
| **PublicInfo** | 公告发布、求助处理 | 4 ticks |

---

## 📊 核心模块说明

### 规则引擎

内置 5 类智能体的应急决策模板，基于阈值触发：

```python
# 示例：消防规则
if zone.disaster_intensity > 0.7:
    return deploy_team(zone)
```

### 案例数据库

预置 3 个示例案例（地震/洪水/火灾），支持：

- 语义检索
- 灾害类型过滤
- Few-shot 提示词生成

### 数据适配器

当前提供 Mock 适配器，可轻松扩展：

```python
# 自定义适配器只需继承
class MyAdapter(DataAdapter):
    async def connect(self): ...
    async def fetch_data(self): ...
```

---

## 📖 文档资源

- [RESUME_DESCRIPTION.md](./RESUME_DESCRIPTION.md) - 简历包装，3 个版本可选
- [INTERVIEW_GUIDE.md](./INTERVIEW_GUIDE.md) - 面试指南，含高频问题与答案
- [INTERVIEW_CHEAT_SHEET.md](./INTERVIEW_CHEAT_SHEET.md) - 面试突击备忘卡

---

## 🛣️ 路线图

- [ ] 接入真实 GIS 数据
- [ ] 接入真实 IoT 传感器
- [ ] WebSocket 实时前端
- [ ] 完整的仿真可视化
- [ ] 更多历史案例
- [ ] 多语言支持

---

## 📄 许可证

MIT License

---

## 🙏 致谢

感谢所有贡献者！
