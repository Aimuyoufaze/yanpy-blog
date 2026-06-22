---
title: 'InterviewMate — 用 AI 模拟面试，让面试练习不再焦虑'
description: '一个基于 DeepSeek API 的 AI 模拟面试平台，支持导师画像提取与多类型面试官，专为考研/保研/留学面试设计。'
pubDate: 'Jun 22 2026'
heroImage: '../../assets/interviewmate-screenshot.png'
---

![InterviewMate 界面截图](/images/interviewmate-screenshot.png)

## 为什么做这个项目？

考研、保研、留学面试——对很多人来说是既重要又焦虑的环节。

真实的面试场景下，你不知道导师会问什么，不知道怎么组织回答，也不知道自己的表现到底怎么样。找同学模拟，双方都尴尬；找老师帮忙，又不好意思频繁打扰。

**InterviewMate 的出发点很简单：让 AI 扮演面试官，帮你低成本、高频次地练习面试。**

> **在线体验：** [https://interviewmate-t1lk.onrender.com](https://interviewmate-t1lk.onrender.com)

## 核心功能

### 🎭 4 种面试官人格

不同的导师风格不同，面试体验也应该不同。InterviewMate 提供了四种面试官类型：

- **😤 严厉型** — 严格追问细节，不容易给好评，模拟压力面试场景
- **😊 温和型** — 鼓励式引导，会给提示，适合第一轮熟悉流程
- **🔍 追问型** — 连环追问，测试知识深度与临场反应
- **🧠 苏格拉底型** — 通过反问引导思考，考验逻辑与表达能力

### 🎯 导师画像提取（核心功能）

这是 InterviewMate 最有特色的功能。输入导师姓名和所在机构，系统会：

1. **自动搜索** ArXiv 论文（最多 15 篇）
2. **爬取** Google Scholar、维基百科、个人主页等公开信息
3. **分析** 所有文本内容，用 DeepSeek 提取导师的研究方向、学术风格、代表性工作
4. **生成** 结构化的导师画像
5. **持久化** 存入 SQLite 数据库，下次可以直接使用

之后你可以选择该导师作为面试官，面试方向设为「该教授自身专业」，AI 就会基于导师的真实研究背景来提问。

### 🎙️ 语音输入

集成了百度语音识别（STT）和本地语音识别，可以直接用语音回答，更接近真实面试体验。

## 技术架构

InterviewMate 采用了简单但务实的技术选型：

**后端：** FastAPI + DeepSeek API + SQLite  
**前端：** 纯 HTML/CSS/JavaScript（无框架依赖）  
**搜索引擎：** ArXiv API + Google Scholar 爬虫  
**部署：** 一键启动脚本 / Render 云平台

![InterviewMate 系统架构图](/images/interviewmate-arch.svg)

选择纯 HTML 前端而不是 React/Vue，是因为这个项目面向的是需要快速上手的学生用户——越简单越好，不用装 node_modules，不用学框架，打开就能用。

## 技术亮点

### ✨ 导师搜索与画像蒸馏

`persona.py` 是整个项目最核心的模块（~620 行）。它的工作流程是：

1. 搜索 ArXiv 获取论文元数据
2. 并行下载论文摘要和全文
3. 搜索 Google Scholar 获取引用信息
4. 爬取个人主页和公开资料
5. 将所有材料交给 DeepSeek 分析
6. 生成标准化的导师画像 JSON

这套流程把"找到导师信息 → 理解导师研究 → 生成面试官"做到了半自动化。

### ✨ 面试引擎设计

`interview.py`（~280 行）维护了面试的对话状态机：
- **开场** — 面试官自我介绍 + 说明面试方向
- **提问** — 根据导师画像 + 对话历史生成下一个问题
- **追问** — 根据回答内容进行深度追问（严厉型会追更多）
- **评价** — 每个回答后给出结构性反馈
- **结束** — 总结表现，给出改进建议

### ✨ 4 种人格的实现

不同面试官类型的差异，其实是通过 System Prompt 的温度参数和角色设定来实现的，没有复杂的算法。这恰好说明了一个道理：**用好 Prompt，能做出很自然的多模态 AI 产品**。

## 开发过程中的经验

### 搜索引擎的坑

爬取 Google Scholar 是最头疼的部分。反爬机制严格，频繁请求会被封 IP。解决方式是：控制请求频率 + 设置合理的 User-Agent + 使用学术 API 作为备选。

### DeepSeek API 的成本控制

导师画像提取需要处理大量文本（论文摘要 + 网页内容），如果每次重复请求会浪费 API 额度。解决方案：
- 导师画像一旦生成就存入 SQLite
- 使用相同的 API Key，用缓存避免重复调用
- 控制每次传入的文本量，避免超出 token 限制

### 语音识别的兼容性

百度 STT 需要网络，本地 STT 精度不如云端。最终采用双轨设计：默认走百度 API，网络不可用时自动降级到本地模型。

## 如何体验

项目已部署在 Render 云平台：
➡️ **[interviewmate-t1lk.onrender.com](https://interviewmate-t1lk.onrender.com)**

也可以本地运行：

```bash
git clone https://github.com/aimuyoufaze/InterviewMate.git
cd InterviewMate/backend
# 配置 DeepSeek API Key
cp .env.example .env
# 编辑 .env 填入你的 Key
pip install -r requirements.txt
cd ..
bash start.sh
```

打开浏览器访问 `http://localhost:8000` 即可。

（需要自己准备 DeepSeek 的 API Key，免费额度足够个人使用了。）

## 总结

InterviewMate 是一个小而完整的 AI Agent 应用。它不算复杂，但它展示了 AI Agent 的典型模式：**感知（搜索导师信息）→ 推理（分析画像）→ 行动（模拟面试）→ 反馈（评价回答）**。

对于正在准备面试的同学，这可能是最有性价比的练习工具了。而对我来说，这个项目的最大价值在于：**验证了"LLM + 信息检索"这种 Agent 模式在真实场景中是可行的、有用的。**

后面打算加的功能：
- 更多导师信息来源（知网、ResearchGate）
- 面试录音回放与分析
- 多语言面试支持（英文面试模拟）
- 面试表现评分与趋势追踪
