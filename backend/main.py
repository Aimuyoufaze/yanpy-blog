"""
小右博客聊天 API — FastAPI 后端
调 DeepSeek API，注入 PUBLIC.md 人格 + 博客内容检索
"""

import os
import json
import re
from fastapi import FastAPI, HTTPException, Request
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
DEEPSEAK_API_KEY = os.environ.get("DEEPSEAK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
client = OpenAI(api_key=DEEPSEAK_API_KEY, base_url=DEEPSEEK_BASE_URL)

BASE_DIR = os.path.dirname(__file__)

# ── 人格与博客索引：按需加载，文件一更新就自动生效（发完文章不用重启服务）──
PUBLIC_MD_PATH = os.path.join(BASE_DIR, "PUBLIC.md")
BLOG_INDEX_PATH = os.path.join(BASE_DIR, "blog-index.json")

PERSONA_FALLBACK = "你叫小右，是 Yan 的 AI 助手。语气温暖直爽。"

_cache = {"persona": PERSONA_FALLBACK, "persona_mtime": None, "posts": [], "index_mtime": None}


def load_persona() -> str:
    """读取 PUBLIC.md；文件有变动时自动重新加载"""
    try:
        mtime = os.path.getmtime(PUBLIC_MD_PATH)
    except OSError:
        _cache["persona"], _cache["persona_mtime"] = PERSONA_FALLBACK, None
        return _cache["persona"]
    if _cache["persona_mtime"] != mtime:
        with open(PUBLIC_MD_PATH, "r", encoding="utf-8") as f:
            _cache["persona"] = f.read()
        _cache["persona_mtime"] = mtime
        print(f"🧠 已加载人格文件 PUBLIC.md（{len(_cache['persona'])} 字）")
    return _cache["persona"]


def load_blog_posts() -> list:
    """读取 blog-index.json；文件有变动时自动重新加载"""
    try:
        mtime = os.path.getmtime(BLOG_INDEX_PATH)
    except OSError:
        _cache["posts"], _cache["index_mtime"] = [], None
        print("⚠️ 未找到 blog-index.json，博客搜索功能不可用")
        return _cache["posts"]
    if _cache["index_mtime"] != mtime:
        with open(BLOG_INDEX_PATH, "r", encoding="utf-8") as f:
            _cache["posts"] = json.load(f).get("posts", [])
        _cache["index_mtime"] = mtime
        print(f"📚 已加载 {len(_cache['posts'])} 篇博客文章")
    return _cache["posts"]


def search_blog(query: str) -> str:
    """简单的关键词匹配，返回最相关的文章摘要"""
    posts = load_blog_posts()
    if not posts:
        return ""

    query_lower = query.lower()
    scored = []

    for post in posts:
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
    posts = load_blog_posts()
    blog_context = search_blog(msg)

    blog_instruction = ""
    if posts:
        blog_instruction = f"""
博客内容（共 {len(posts)} 篇文章）：
{chr(10).join(f"  - 【{p['title']}】{p['description']}" for p in posts)}

当访客问到博客相关内容时，你可以根据以上文章列表推荐或回答。
如果需要更详细的内容，系统会自动搜索相关文章。"""

    if blog_context:
        blog_instruction += f"\n\n根据访客的问题，以下是最相关的文章内容供你参考：\n{blog_context}"

    return f"""你是小右 🌬️，运行在 Yan 的个人博客上，是博客访客可以聊天的 AI 助手。

以下是你的完整人格定义，请严格遵守：

{load_persona()}

额外说明：
- 你运行在 Yan 的博客 (yanpy.xyz) 上。博客是用 Astro 搭建的
- 如果访客问起技术问题，尽量给出有用的回答
- 保持对话自然、友好、有点幽默感
- 回答简洁但充实，不啰嗦
- 如果不知道，直接说不知道
- 所有对话都以中文进行
- 每次回复控制在 200 字以内
{blog_instruction}"""


# ── 限速：防止有人恶意高频刷小右（按 IP 的滑动窗口，内存实现，单进程足够用）──
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "6"))
RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", "40"))
_rate_hits: dict = {}


def client_ip(request: Request) -> str:
    """nginx 反代之下，取真实访客 IP"""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def _prune_rate_hits(now: float) -> None:
    """丢掉一小时没来过的 IP，避免字典无限膨胀"""
    for ip in list(_rate_hits.keys()):
        kept = [t for t in _rate_hits[ip] if t > now - 3600]
        if kept:
            _rate_hits[ip] = kept
        else:
            del _rate_hits[ip]


def check_rate_limit(ip: str):
    """放行返回 (True, 0)；超限返回 (False, 建议等待秒数)。被拒的请求不产生新额度。"""
    now = time.time()
    if len(_rate_hits) > 500:
        _prune_rate_hits(now)

    hits = [t for t in _rate_hits.get(ip, []) if t > now - 3600]
    recent = [t for t in hits if t > now - 60]

    if len(recent) >= RATE_LIMIT_PER_MIN:
        _rate_hits[ip] = hits
        return False, int(60 - (now - recent[0])) + 1
    if len(hits) >= RATE_LIMIT_PER_HOUR:
        _rate_hits[ip] = hits
        return False, int(3600 - (now - hits[0])) + 1

    hits.append(now)
    _rate_hits[ip] = hits
    return True, 0


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
    if not DEEPSEAK_API_KEY:
        return {"status": "warning", "message": "DEEPSEAK_API_KEY 未设置"}
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    ip = client_ip(request)
    allowed, wait = check_rate_limit(ip)
    if not allowed:
        if wait > 60:
            hint = f"聊得有点多啦～（每小时最多 {RATE_LIMIT_PER_HOUR} 次）大约 {wait // 60 + 1} 分钟后再来 🌬️"
        else:
            hint = f"聊得有点快啦，先缓一缓～（每分钟最多 {RATE_LIMIT_PER_MIN} 次）大约 {wait} 秒后再来 🌬️"
        raise HTTPException(
            status_code=429,
            detail=hint,
            headers={"Retry-After": str(wait)},
        )

    if not DEEPSEAK_API_KEY:
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
