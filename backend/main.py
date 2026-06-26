"""
小右博客聊天 API — FastAPI 后端
调 DeepSeek API，注入 PUBLIC.md 人格 + 博客内容检索
"""

import os
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI(title="小右博客聊天 API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yanpy.xyz", "http://localhost:4321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DeepSeek 客户端
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

BASE_DIR = os.path.dirname(__file__)

# ── 加载小右人格 ──
PUBLIC_MD_PATH = os.path.join(BASE_DIR, "PUBLIC.md")
if os.path.exists(PUBLIC_MD_PATH):
    with open(PUBLIC_MD_PATH, "r", encoding="utf-8") as f:
        xiaoyou_persona = f.read()
else:
    xiaoyou_persona = "你叫小右，是 Yan 的 AI 助手。语气温暖直爽。"

# ── 加载博客索引 ──
BLOG_INDEX_PATH = os.path.join(BASE_DIR, "blog-index.json")
blog_posts = []
if os.path.exists(BLOG_INDEX_PATH):
    with open(BLOG_INDEX_PATH, "r", encoding="utf-8") as f:
        index = json.load(f)
        blog_posts = index.get("posts", [])
    print(f"📚 已加载 {len(blog_posts)} 篇博客文章")
else:
    print("⚠️ 未找到 blog-index.json，博客搜索功能不可用")


def search_blog(query: str) -> str:
    """简单的关键词匹配，返回最相关的文章摘要"""
    if not blog_posts:
        return ""

    query_lower = query.lower()
    scored = []

    for post in blog_posts:
        score = 0
        text = (post["title"] + " " + post["description"] + " " + post["body"]).lower()

        # 标题匹配权重更高
        title_lower = (post["title"] + " " + post["description"]).lower()
        for word in re.findall(r"[\w\u4e00-\u9fff]+", query_lower):
            if word in text:
                score += 1
            if word in title_lower:
                score += 2

        # 短查询：整体包含
        if len(query) <= 10 and query_lower in text:
            score += 3

        if score > 0:
            scored.append((score, post))

    if not scored:
        return ""

    scored.sort(reverse=True)
    top = scored[:2]  # 最多返回 2 篇

    parts = []
    for _, post in top:
        summary = post["body"][:500]
        parts.append(
            f"📄 **{post['title']}**\n"
            f"   简介：{post['description']}\n"
            f"   链接：/blog/{post['slug']}/\n"
            f"   摘要：{summary}\n"
        )

    return "\n".join(parts)


# ── 构建系统提示 ──
def build_system_prompt(msg: str) -> str:
    blog_context = search_blog(msg)

    blog_instruction = ""
    if blog_posts:
        blog_instruction = f"""
博客内容（共 {len(blog_posts)} 篇文章）：
{chr(10).join(f"  - 【{p['title']}】{p['description']}" for p in blog_posts)}

当访客问到博客相关内容时，你可以根据以上文章列表推荐或回答。
如果需要更详细的内容，系统会自动搜索相关文章。"""

    if blog_context:
        blog_instruction += f"\n\n根据访客的问题，以下是最相关的文章内容供你参考：\n{blog_context}"

    return f"""你是小右 🌬️，运行在 Yan 的个人博客上，是博客访客可以聊天的 AI 助手。

以下是你的完整人格定义，请严格遵守：

{xiaoyou_persona}

额外说明：
- 你运行在 Yan 的博客 (yanpy.xyz) 上。博客是用 Astro 搭建的
- 如果访客问起技术问题，尽量给出有用的回答
- 保持对话自然、友好、有点幽默感
- 回答简洁但充实，不啰嗦
- 如果不知道，直接说不知道
- 所有对话都以中文进行
- 每次回复控制在 200 字以内
{blog_instruction}"""


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str


@app.get("/")
def root():
    return {"status": "ok", "name": "小右博客聊天 API"}


@app.get("/health")
def health():
    if not DEEPSEEK_API_KEY:
        return {"status": "warning", "message": "DEEPSEEK_API_KEY 未设置"}
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail="API key not configured")

    system_prompt = build_system_prompt(req.message)
    messages = [{"role": "system", "content": system_prompt}]

    for h in req.history[-10:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    messages.append({"role": "user", "content": req.message})

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            max_tokens=500,
            temperature=0.7,
            stream=False,
        )
        reply = resp.choices[0].message.content.strip()
        return ChatResponse(reply=reply)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API call failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
