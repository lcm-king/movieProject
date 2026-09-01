# MovieRec · AI 电影推荐与评价系统

> 独立全栈开发 · 千人千面的电影推荐
>
> 基于用户历史评分构建类型偏好画像，融合**置信度加权推荐算法 + Elasticsearch 全文检索 + Dify AI 智能问答**，实现完整的电影社区功能。

## ✨ 项目亮点

- **个性化推荐算法**：置信度加权（`平均分 × sqrt(评分次数)`）综合评分与类型匹配度生成推荐列表，附带可解释的推荐理由
- **ES 全文检索**：Elasticsearch 实现电影全文检索，支持中文分词、多字段排序、高亮显示，毫秒级响应
- **AI 智能问答**：接入 Dify 平台，基于电影知识库（`movies_knowledge_base.csv`）回答电影相关问题
- **完整用户体系**：JWT 认证 + 多角色权限（普通用户 / 管理员），支持收藏、评分、评论完整社区功能
- **管理后台**：电影信息管理、用户管理、数据看板

## 核心功能

| 模块 | 说明 |
|------|------|
| 用户系统 | 注册 / 登录（JWT）、个人中心、评分偏好画像 |
| 电影浏览 | 列表、详情、ES 全文检索（中文分词 + 高亮）|
| 推荐系统 | 置信度加权算法生成个性化推荐，带推荐理由 |
| 社区互动 | 评分、评论、收藏 |
| AI 问答 | 基于电影知识库的智能问答（Dify）|
| 管理后台 | 电影 / 用户管理、数据统计 |

## 推荐算法

```text
score = 平均分 × sqrt(评分次数)   # 置信度加权，防止"少数高分"虚高

综合推荐 = 类型偏好匹配度 × 权重 + score 归一化
```

- 用户评分越多、评分次数越多的电影，置信度越高
- 结合用户历史评分的类型偏好画像，实现"千人千面"
- 每条推荐附带可解释理由（"因为您喜欢 X 类型，且这部电影评分较高"）

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | FastAPI + SQLAlchemy + Pydantic |
| 数据 | MySQL、Elasticsearch（全文检索）|
| AI | Dify（智能问答，基于电影知识库）|
| 前端 | HTML5 + CSS3 + JavaScript（原生，无框架）|
| 认证 | JWT + 多角色权限 |

## 项目结构

```text
movieProject/
├── movie_recommend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── routers/         # users/movies/ratings/recommendations/comments/admin/ai
│   │   ├── models.py        # ORM 模型
│   │   ├── schemas.py       # Pydantic 模型
│   │   ├── dify_client.py   # Dify AI 问答接入
│   │   ├── crud.py          # 数据访问
│   │   └── static/          # 前端页面（HTML/JS/CSS）
│   ├── run.py               # 启动入口
│   └── requirements.txt
└── movies_knowledge_base.csv  # 电影知识库（AI 问答数据源）
```

## 快速开始

```bash
cd movie_recommend
pip install -r requirements.txt
# 配置 .env（MySQL / Elasticsearch / Dify 连接信息）
python run.py
```

- 访问：`http://127.0.0.1:8000`
- Swagger 文档：`http://127.0.0.1:8000/docs`
