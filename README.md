# Marketing Craft

> AI智能营销内容生成器 - 一键生成小红书/短视频/SEO/广告文案

## ✨ 功能特性

### 🎯 8大营销技能

| 技能 | 说明 |
|------|------|
| ❤️ 小红书种草文 | 生成小红书风格种草笔记，吸睛标题+痛点+亮点+标签 |
| 🎬 短视频脚本 | 生成短视频脚本，含hook、台词、画面描述、BGM建议 |
| 🔍 SEO优化文章 | 生成SEO优化文章，含标题结构、关键词布局、meta建议 |
| 📢 广告创意 | 生成多版本广告文案，含主副标题、CTA、A/B测试建议 |
| 🏷️ 产品描述 | 生成电商产品描述，含卖点、参数、场景、FAQ |
| 📧 邮件营销 | 生成营销邮件，含主题行、正文、CTA、P.S. |
| 🔗 社媒内容 | 生成社交媒体帖子，适配微信公众号/微博/抖音等平台 |
| 📊 营销方案 | 生成完整营销方案，含市场分析、渠道策略、预算分配 |

### 🔧 技术特性

- **FastAPI 后端**：高性能异步 API
- **LLM 集成**：支持多种大语言模型
- **PWA 支持**：可安装为桌面/移动应用
- **响应式前端**：Tailwind CSS，移动端友好
- **技能引擎**：可扩展的技能架构

## 🚀 快速开始

### 环境要求

- Python 3.9+
- LLM API Key（OpenAI / 其他兼容接口）

### 安装运行

```bash
# 克隆仓库
git clone https://github.com/hpennn/marketing-craft.git
cd marketing-craft

# 安装依赖
pip install -r backend/requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 LLM API Key

# 启动服务
cd backend
python main.py
```

访问 `http://localhost:8000` 即可使用。

## 📁 项目结构

```
marketing-craft/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── routers/             # API 路由
│   ├── skills/
│   │   ├── engine.py        # 技能引擎
│   │   ├── llm_client.py    # LLM 客户端
│   │   ├── registry.py      # 技能注册中心
│   │   └── preset/          # 预置技能
│   │       ├── xiaohongshu.py
│   │       ├── video_script.py
│   │       ├── seo_article.py
│   │       ├── ad_copy.py
│   │       ├── product_desc.py
│   │       ├── email_marketing.py
│   │       ├── social_media.py
│   │       └── marketing_plan.py
│   └── ...
├── frontend/
│   ├── index.html           # 单页应用
│   ├── manifest.json        # PWA 配置
│   ├── sw.js                # Service Worker
│   └── icons/               # 应用图标
└── README.md
```

## 📄 License

MIT
