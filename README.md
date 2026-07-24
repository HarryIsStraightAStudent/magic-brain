# 魔法大脑 Magic Brain 🧠✈️🚄

> AI 交通套利搜索引擎 — 4 Agent 协作 + 真实联网票价 + 3D 地球路径可视化
>
> GOAI Global Open-source AI Challenge · Track 02 Boundless Agents

## 故事

从上海去香港，高铁直达 ¥966。但坐动卧到深圳（¥507）再过关到香港（¥60），全程只要 ¥567 —— **省 ¥399（41%）**。

导航 App 只做"最快路径"，OTA 只卖"直达库存"，没人做"多模态中转套利"。魔法大脑把这种"人肉摸索省钱路线"自动化了。

## 核心特性

- 🤖 **4 Agent 协作闭环**：意图理解 → 任务规划 → 工具调用 → 结果解释（GLM-4.7）
- 🌐 **真实联网票价**：Playwright 渲染携程火车票/机票页，提取真实车次+票价（非编造）
- 🗺️ **3D 地球路径**：Three.js 真实地球，火车贴地、飞机大圆弧，换乘点标注
- 💰 **多目标套利**：多目标 Dijkstra 在价格/时间/换乘间优化，省钱/省时间双模式
- 📍 **任意城市可搜**：本地数据秒回 + 联网抓取兜底，覆盖全国

## 快速开始

```bash
git clone https://github.com/HarryIsStraightAStudent/magic-brain.git
cd magic-brain

# 1. 虚拟环境 + 依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

# 2. 配置 GLM API Key
cp .env.example .env
# 编辑 .env 填入 GLM_API_KEY

# 3. 启动
uvicorn api:app --reload --port 8000
# 浏览器打开 http://localhost:8000
```

## 技术架构

```
┌─────────────────────────────────────────┐
│  前端 (Three.js + Tailwind)              │
│  3D 地球 · 毛玻璃 UI · Agent 思考可视化   │
└────────────────┬────────────────────────┘
                 │ HTTP
┌────────────────┴────────────────────────┐
│  FastAPI 服务 (api.py)                   │
│  /api/agent · /api/search · /api/geo     │
├─────────────────────────────────────────┤
│  Agent 层 (agents/)                      │
│  pipeline.py  4 Agent 流水线             │
│  llm.py       GLM-4.7 客户端(Anthropic)  │
│  fare_fetch.py 携程票价抓取(Playwright)  │
├─────────────────────────────────────────┤
│  引擎层 (engine/)                        │
│  graph.py     多模态交通图               │
│  search.py    多目标 Dijkstra            │
│  arbitrage.py 套利分析                   │
│  loader.py    数据加载                   │
├─────────────────────────────────────────┤
│  数据层 (data/)                          │
│  routes/ baselines/  核实线路            │
│  geo.json  cities + 89城市经纬度         │
└─────────────────────────────────────────┘
```

### Agent 闭环

| Agent | 职责 | 实现 |
|-------|------|------|
| 🧠 意图理解 | 解析起终点/偏好/约束 | GLM-4.7 |
| 📋 任务规划 | 拆解搜索步骤 | GLM-4.7 |
| 🔧 工具调用 | 查真实票价 + 本地搜索 | Playwright 抓携程 + Dijkstra |
| 💡 结果解释 | 生成自然语言回复 | GLM-4.7 |

## 真实数据来源

| 数据 | 来源 | 说明 |
|------|------|------|
| 火车票价 | 携程火车票页（Playwright 渲染）| 真实车次+座位价，可追溯 |
| 机票价格 | 携程机票页 | 最低价参考 |
| 本地核实线路 | 12306 实测 | 上海→香港等 5 城对 |
| 城市经纬度 | 公开地理数据 | 89 城市/口岸/枢纽 |

**不编造**：联网未查到时诚实告知，建议去 12306/携程查询。

## API

| 端点 | 说明 |
|------|------|
| `GET /` | 前端页面 |
| `GET /api/health` | 健康检查 |
| `GET /api/cities` | 可查城市 |
| `GET /api/geo` | 城市经纬度 |
| `GET /api/search?origin=SHA&destination=HKG` | 本地搜索 |
| `POST /api/agent` | 4 Agent 流水线（联网） |

启动后访问 `http://localhost:8000/docs` 看交互式 API 文档。

## 项目结构

```
magic-brain/
├── agents/              # 多 Agent 层
│   ├── pipeline.py      # 4 Agent 流水线
│   ├── llm.py           # GLM 客户端
│   └── fare_fetch.py    # 携程票价抓取
├── engine/              # 核心引擎（纯标准库）
│   ├── graph.py         # 多模态交通图
│   ├── search.py        # 多目标 Dijkstra
│   ├── arbitrage.py     # 套利分析
│   └── loader.py        # 数据加载
├── data/                # 数据集
│   ├── routes/ baselines/
│   ├── geo.json         # 经纬度+航点
│   └── INDEX.md         # 数据索引
├── web/index.html       # 前端（3D 地球 + 毛玻璃）
├── api.py               # FastAPI 服务
├── cli.py               # CLI 工具
├── tests/test_engine.py # 回归测试
├── docs/                # 初赛材料
│   ├── INTRO.md         # 作品简介
│   ├── PITCH_DECK.md    # PPT 内容稿
│   ├── COMPLIANCE.md    # 合规说明
│   └── 魔法大脑-方案PPT.pptx
└── scripts/build_ppt.py # PPT 生成脚本
```

## 开放 / 复用贡献

| 组件 | 复用价值 |
|------|---------|
| 多模态交通图引擎 | 纯标准库，可独立用于任意路径规划 |
| 4 Agent 流水线 | 意图→规划→工具→解释，可复用于其他工具调用场景 |
| 携程票价抓取 | Playwright 渲染抓取范式，可适配其他票务站 |
| 真实交通数据集 | 核实线路 + 89 城市经纬度 |

MIT License · 欢迎贡献

## 运行证据

- CLI：`python3 cli.py 上海 香港` → D941 ¥567 vs G99 ¥966 省 41%
- 回归测试：`python3 -m unittest tests.test_engine` → 6 项全过
- 联网抓取：上海→乌鲁木齐 Z40 硬座¥376、飞机¥890（携程实时）

## 安全合规

详见 [docs/COMPLIANCE.md](docs/COMPLIANCE.md)。要点：
- 定位出行规划辅助，不订票、不替代 OTA
- 联网结果标注"以购票平台为准"
- 无账号、无数据存储、无追踪
- GLM 可迁移（Qwen/DeepSeek），第三方依赖完整披露

## License

MIT
