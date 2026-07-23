# 魔法大脑 Magic Brain 🧠✈️🚄

> 交通套利搜索引擎 — 输入起终点，自动发现更便宜的中转线路。
>
> GOAI Global Open-source AI Challenge · Track 02 Boundless Agents

## 故事

从上海去香港。高铁直达 **¥966**，飞机最便宜 ¥696。
但坐 D941 动卧到深圳（**¥507**），再走罗湖过关 + 港铁到尖沙咀（¥60），全程只要 **¥567** ——
**比高铁直达省 ¥399 (41%)**，还能在卧铺上睡一觉省一晚酒店。

魔法大脑把这种"人肉摸索省钱路线"的能力，做成自动化的 AI 搜索引擎。

## Demo 截图

```
┌─────────────────────────────────────┐
│  🎉 你能省                          │
│     ¥399   (41% ↓)                  │
│     比高铁直达 西九龙 便宜           │
├─────────────────────────────────────┤
│  ⭐ D941 二等卧  ¥567                │
│     3段 · 2次换乘 · 13小时9分       │
│     [推荐省钱] [13小时9分]          │
├─────────────────────────────────────┤
│  直达基准对比                        │
│  ✈️ 飞机直达           ¥696         │
│  🚄 高铁直达 西九龙    ¥966         │
└─────────────────────────────────────┘
```

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/HarryIsStraightAStudent/magic-brain.git
cd magic-brain

# 2. 建虚拟环境 + 装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" pydantic

# 3a. CLI 体验 (无需额外依赖)
python3 cli.py 上海 香港

# 3b. Web 体验
uvicorn api:app --reload --port 8000
# 浏览器打开 http://localhost:8000
```

## 现状 (W1 · 2026-07-23)

- [x] 多模态交通图模型（飞机/高铁/卧铺/地铁/步行过关）
- [x] 多目标 Dijkstra 搜索引擎（价格 + 时间 + 换乘 + 舒适度加权）
- [x] 套利分析模块（vs 直达基准，算省钱额）
- [x] 真实数据集（上海→香港，来源 12306 实测）+ 4 条种子线路
- [x] CLI 冒烟测试通过
- [x] FastAPI 服务 + 旅行温暖风前端（浏览器可点）
- [x] 回归测试 6 项

## 路线图

- [ ] **W2**: 多 Agent 协作（GLM 意图解析 + 数据采集 + 解释）
- [ ] **W2**: Stitch 设计稿替换临时前端
- [ ] **W3**: 扩充数据集至 30 条线路（含已核实数据）
- [ ] **W3**: 实时增量票价（Agent 上网查询）
- [ ] **决赛**: 长期开源贡献，社区线路众包

## 项目结构

```
magic-brain/
├── engine/              # 核心引擎 (纯标准库)
│   ├── graph.py         # 多模态交通图
│   ├── search.py        # 多目标 Dijkstra
│   ├── arbitrage.py     # 套利分析 (省钱对比)
│   └── loader.py        # JSON 数据加载
├── data/
│   ├── cities.json      # 城市 code 体系
│   ├── routes/          # 中转省钱路径
│   ├── baselines/       # 直达基准
│   └── INDEX.md         # 数据集索引 + 核实状态
├── web/index.html       # 前端 (旅行温暖风)
├── cli.py               # 命令行工具
├── api.py               # FastAPI 服务
└── tests/test_engine.py # 回归测试
```

## 技术栈

| 层 | 选型 |
|----|------|
| 语言 | Python 3.11+ |
| 引擎 | 纯标准库自写图算法（开源价值） |
| LLM | GLM-4.5 (智谱，国产开源) |
| Web | FastAPI + 静态前端 |
| 数据 | JSON 数据集（前期）→ SQLite（后期） |

## 核心洞察

普通地图导航（高德/百度/Google）只做"最快路径"。
OTA（携程/飞猪）只卖"直达库存"。
**没有人做"多模态中转套利"** —— 这是魔法大脑的位置。

## API

| 端点 | 说明 |
|------|------|
| `GET /` | 前端页面 |
| `GET /api/health` | 健康检查 |
| `GET /api/cities` | 可查城市列表 |
| `GET /api/search?origin=SHA&destination=HKG&weight=price` | 搜索套利路径 |

启动后访问 `http://localhost:8000/docs` 查看交互式 API 文档。

## License

MIT (待定)
