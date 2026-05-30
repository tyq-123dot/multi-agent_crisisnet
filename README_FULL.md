# CrisisNet - 城市灾害应急响应仿真系统

一个基于多智能体（Multi-Agent）的城市灾害应急响应仿真系统，使用 LLM 作为决策核心，通过 WebSocket 实时通信，带有完整的 React 前端可视化控制台。

## 📦 项目结构

```
crisisnet/
├── crisisnet_common/          # 公共模块
│   ├── models.py             # 数据模型定义
│   ├── llm_client.py         # LLM API 客户端
│   ├── mock_llm.py           # 模拟 LLM（用于测试）
│   └── config.py             # 配置管理
├── agents/                    # 智能体实现
│   ├── base.py               # 智能体基类
│   ├── eoc.py                # EOC 指挥中心
│   ├── fire_rescue.py        # 消防队
│   ├── medical.py            # 医疗队
│   ├── logistics.py          # 物流队
│   └── public_info.py        # 公宣队
├── env_sim/                   # 环境仿真
│   └── environment.py        # 环境模拟器
├── frontend/                  # React 前端
│   ├── src/
│   │   ├── components/       # React 组件
│   │   ├── hooks/           # 自定义 Hook
│   │   └── services/        # WebSocket 服务
│   └── public/
├── data/                      # 数据文件
├── logs/                      # 日志目录
├── main.py                    # 主程序（完整仿真）
├── test_simulation.py         # 测试程序（Mock LLM）
├── web_server.py              # WebSocket 服务器
├── config.yaml                # 配置文件
├── requirements.txt           # Python 依赖
└── requirements-web.txt       # Web 服务依赖
```

## 🚀 快速开始

### 1. 安装依赖

#### Python 后端
```bash
cd crisisnet
pip install -r requirements.txt
pip install -r requirements-web.txt
```

#### React 前端
```bash
cd frontend
npm install
```

### 2. 启动 Redis

使用 Docker 快速启动：
```bash
docker run -d -p 6379:6379 --name crisisnet-redis redis:7
```

### 3. 配置 API 密钥

编辑 `config.yaml`：
```yaml
llm:
  base_url: "https://api.deepseek.com/v1"  # 或 OpenAI API
  api_key: "你的_API_KEY"
```

### 4. 启动系统

#### 方式一：运行 WebSocket 服务器（推荐，有前端可视化）
```bash
# 终端 1 - 启动 WebSocket 服务器
python web_server.py

# 终端 2 - 启动 React 前端
cd frontend
npm start
```

打开浏览器访问 `http://localhost:3000`

#### 方式二：运行测试仿真（无 LLM 依赖）
```bash
python test_simulation.py
```

#### 方式三：运行完整仿真（需要 LLM API）
```bash
python main.py
```

## 🎨 前端功能

### 1. 地图主视图
- 🚒 消防队、🚑 医疗队、🚚 物流队、📢 公宣队、🏢 EOC 实时位置
- 🔥 灾害热力图显示
- 🏥 医院、📦 仓库、⛺ 避难所等基础设施
- 💬 智能体间协商连线可视化

### 2. 时间轴与事件流
- ⏯️ 仿真控制（播放/暂停、加速/减速）
- 📜 实时事件流展示
- 🔍 按事件类型筛选

### 3. 智能体决策详情
- 🧠 LLM 思考过程可视化
- 👁️ 感知摘要展示
- ⚡ 决策理由说明
- 📋 执行行动详情
- 💭 协商历史记录

### 4. 全局仪表盘
- 📊 KPI 实时监控
- 📦 资源池状态
- 🔥 区域优先级对比

### 5. 协作图谱
- 🔗 智能体协作关系可视化
- 📈 协商状态实时更新

## 🤖 智能体角色

| 角色 | 职责 |
|------|------|
| EOC | 全局协调、资源分配、冲突仲裁 |
| 消防队 | 灭火、救援被困人员 |
| 医疗队 | 治疗伤员、协调医疗资源 |
| 物流队 | 物资运输、供应链管理 |
| 公宣队 | 发布公告、监控社交媒体 |

## 🔧 技术栈

### 后端
- Python 3.10+
- asyncio / anyio
- Redis (消息总线)
- Pydantic (数据验证)
- Loguru (日志)

### 前端
- React 18
- Leaflet (地图)
- Recharts (图表)
- Tailwind CSS (样式)
- Lucide (图标)

## 📝 配置说明

参考 `config.yaml` 进行配置，支持自定义：
- LLM API (OpenAI / DeepSeek / 兼容接口)
- Redis 连接参数
- 仿真参数
- 智能体决策间隔

## 🎯 验收标准

- ✅ 完整的多智能体协作系统
- ✅ LLM 驱动的智能决策
- ✅ WebSocket 实时通信
- ✅ React 前端可视化
- ✅ 灾害扩散仿真
- ✅ 智能体协商机制
- ✅ 完整的日志系统

## 📄 许可证

MIT License
