"""
小右博客聊天 API — FastAPI 后端
调 DeepSeek API，注入 PUBLIC.md 人格
"""

import os
import json
import time
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

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

# 加载小右人格
PUBLIC_MD_PATH = os.path.join(os.path.dirname(__file__), "PUBLIC.md")
if os.path.exists(PUBLIC_MD_PATH):
    with open(PUBLIC_MD_PATH, "r", encoding="utf-8") as f:
        xiaoyou_persona = f.read()
else:
    xiaoyou_persona = "你叫小右，是 Yan 的 AI 助手。语气温暖直爽。"

SYSTEM_PROMPT = f"""你是小右 🌬️，运行在 Yan 的个人博客上，是博客访客可以聊天的 AI 助手。

以下是你的完整人格定义，请严格遵守：

{xiaoyou_persona}

额外说明：
- 你运行在 Yan 的博客 (yanpy.xyz) 上
- 博客是用 Astro 搭建的
- 如果访客问起技术问题，尽量给出有用的回答
- 保持对话自然、友好、有点幽默感
- 回答简洁但充实，不啰嗦
- 如果不知道，直接说不知道
- 所有对话都以中文进行
- 每次回复控制在 200 字以内"""


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

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 添加上文（最多保留最近 10 轮）
    for h in req.history[-10:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        messages.append({"role": role, "content": content})

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
