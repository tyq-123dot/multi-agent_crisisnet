<<<<<<< HEAD
# CrisisNet

CrisisNet 是一个基于多智能体的城市灾害应急响应仿真系统。

## 项目结构

```
crisisnet/
├── crisisnet_common/     # 公共模块
│   ├── models.py         # 数据模型和消息定义
│   ├── llm_client.py     # LLM 客户端封装
│   └── config.py         # 配置管理
├── agents/               # 智能体实现
│   ├── base.py           # 智能体基类
│   ├── eoc.py            # 应急指挥中心智能体
│   ├── fire_rescue.py    # 消防救援智能体
│   ├── medical.py        # 医疗救援智能体
│   ├── logistics.py      # 物流智能体
│   └── public_info.py    # 公共信息智能体
├── env_sim/              # 环境模拟器
│   └── environment.py    # 环境模拟实现
├── logs/                 # 日志目录
├── data/                 # 数据目录
├── main.py               # 主程序入口
├── config.yaml           # 配置文件
└── requirements.txt      # 依赖列表
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Redis

使用 Docker 启动 Redis：

```bash
docker run -d -p 6379:6379 --name crisisnet-redis redis:7
```

或者使用本地安装的 Redis。

### 3. 配置 API 密钥

编辑 `config.yaml`，填入你的 API 密钥。

#### 使用 DeepSeek (推荐)
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

### 4. 运行仿真

```bash
python main.py
```

开启调试模式：

```bash
python main.py --debug
```

### 5. 测试模式 (无需 API 密钥)

使用 Mock LLM 快速测试系统：

```bash
python test_simulation.py
```

## 系统架构

CrisisNet 由以下组件组成：

- **环境模拟器**：负责模拟灾害发展、更新世界状态、生成随机事件
- **消息总线**：基于 Redis Pub/Sub，实现智能体间的异步通信
- **多智能体**：
  - EOC（应急指挥中心）：全局协调、资源分配、冲突仲裁
  - FireRescue（消防）：灭火、救援被困人员
  - Medical（医疗）：治疗伤员、协调医疗资源
  - Logistics（物流）：调度物资运输
  - PublicInfo（公共信息）：发布公告、转发求救信息

## 配置说明

参考 `config.yaml` 中的详细配置选项。
=======
# multi-agent_crisisnet
CrisisNet - 城市灾害多智能体应急响应系统  
>>>>>>> c52d6dd1735a197a7b66633a046af25096caffa2
