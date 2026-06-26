"""构建博客文章索引"""
import os
import re
import json
from pathlib import Path

BLOG_DIR = Path(__file__).parent.parent / "src" / "content" / "blog"
OUTPUT_DIR = Path(__file__).parent
OUTPUT_FILE = OUTPUT_DIR / "blog-index.json"

def parse_mdx(filepath):
    """解析 MDX 文件，提取 frontmatter 和正文"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取 frontmatter（--- 之间的 YAML）
    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not fm_match:
        return None

    fm_text = fm_match.group(1)
    body = content[fm_match.end():]

    # 解析简单的 YAML 字段
    metadata = {}
    for line in fm_text.strip().split("\n"):
        m = re.match(r"^(\w+):\s*['\"]?(.*?)['\"]?\s*$", line)
        if m:
            metadata[m.group(1)] = m.group(2)
        else:
            m2 = re.match(r"^(\w+):\s*(.*)$", line)
            if m2:
                metadata[m2.group(1)] = m2.group(2)

    # 清理正文：去掉代码块标记、图片链接等
    # 保留纯文本内容用于搜索
    body_clean = re.sub(r"```[\s\S]*?```", "", body)  # 去掉代码块
    body_clean = re.sub(r"!\[.*?\]\(.*?\)", "", body_clean)  # 去掉图片
    body_clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", body_clean)  # 链接保留文字
    body_clean = re.sub(r"#{1,6}\s*", "", body_clean)  # 去掉标题标记
    body_clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", body_clean)  # 去掉粗体
    body_clean = re.sub(r"\*([^*]+)\*", r"\1", body_clean)  # 去掉斜体
    body_clean = re.sub(r"^\s*[-*+]\s+", "", body_clean, flags=re.MULTILINE)  # 列表标记
    body_clean = re.sub(r"^\s*\d+\.\s+", "", body_clean, flags=re.MULTILINE)  # 数字列表
    body_clean = re.sub(r"\n{3,}", "\n\n", body_clean)  # 多余空行
    body_clean = body_clean.strip()

    slug = filepath.stem  # 文件名作为 slug

    return {
        "slug": slug,
        "title": metadata.get("title", slug),
        "description": metadata.get("description", ""),
        "pubDate": metadata.get("pubDate", ""),
        "body": body_clean[:3000],  # 限制长度，避免超 token
    }


def build_index():
    posts = []
    for f in sorted(BLOG_DIR.glob("*.md")):
        print(f"  📄 {f.name}")
        post = parse_mdx(f)
        if post:
            posts.append(post)

    index = {
        "total": len(posts),
        "posts": posts,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 索引已生成：{OUTPUT_FILE}")
    print(f"   共 {len(posts)} 篇文章")

if __name__ == "__main__":
    build_index()
