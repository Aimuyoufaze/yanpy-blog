---
title: '舆情监测与智能研判 Agent — 课程设计进行时'
description: '从零搭建一套舆情监测 Agent 系统，覆盖数据采集、情感分析、走势追踪、预警研判全流程。目前项目已进入 Week 2，基础设施搭建完成，MVP 原型就绪。'
pubDate: 'Jul 3 2026'
---

<img src="/images/blogtest.jpg" alt="舆情监测项目截图" style="border-radius: 12px; border: 2px solid #000; box-shadow: 5px 5px 0 #A8D5E2;">

*项目初期的一些工作记录*

## 项目背景

这是本学期的一门课程设计，我和 10 人团队一起从零搭建一套**舆情监测与智能研判 Agent 系统**。项目周期约 4-5 周，目标是实现"自动采集 → 情感分析 → 走势追踪 → 预警研判"全流程智能化。

系统提供 **Web Dashboard** 和 **对话式舆情助手** 两大入口，面向媒体监测、政务舆情、企业品牌监测等场景。

---

## 技术栈一览

选了这套全家桶：

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + ECharts 5 + Ant Design |
| 后端 | FastAPI + Celery + Redis |
| AI | LangChain / LangGraph + DeepSeek API |
| 数据库 | PostgreSQL + Elasticsearch |
| 爬虫 | Scrapy + RSS |
| 部署 | Docker + GitHub Actions |

---

## 目前完成的工作（Week 2）

### ✅ 数据采集

- **B站爬虫** 已部署，用 asyncpg 直连 PostgreSQL 入库
- 通用写入函数 `insert_article()` / `insert_articles()` 已封装
- RSS 订阅模块开发中

### ✅ 数据库

- 课题组服务器 **PostgreSQL 16** 部署完成
- `public_sentiment` 库，`articles` 表（字段：id, author, title, content, time, platform, direction, score, keyword, parent_keyword）
- 支持远程连接（`sentiment_user` 用户）

### ✅ 情感分析与规则引擎

- **rule_engine.py** 改造成 LangChain `@tool`，整合情绪/高危/愤怒词典
- **stage_alert.py** 同样接入 Agent 工具链
- Agent prompt 已扩展为 6 步流程 + 综合研判

### ✅ 爬虫接入 & 数据导入

- 独立 `import_crawled_data.py` 模块，支持增量写入
- 密码和 API Key 通过 `.env` 管理，不进 Git

### ✅ 课题组服务器

服务器已到位，基本环境全部配置完成。

---

## 正在做的（Week 2-3）

- **前端 Dashboard**：React + ECharts 的趋势图、词云、预警看板
- **对话式舆情助手**：基于 LangChain Agent，用户可以用自然语言查询舆情
- **话题聚类**：BERTopic 接入，从采集数据中自动发现热点话题
- **预警系统**：阈值 + LLM 双重研判，推送结构化预警报告

---

## 一点感想

这是我第一次以 PM 身份带一个完整项目，从需求拆解、分工、技术选型到进度追踪，每一步都是学习。

Agent 系统的核心思路其实很简洁：**把 LLM 作为推理引擎，围绕它搭一圈工具（爬虫、分析器、数据库查询、报告生成器），让 Agent 自主编排流程。** 数据进来了，Agent 自己决定要不要分析、要不要预警、拿什么格式输出。

后面几周会陆续更新进展。
