# 小右博客聊天后端

FastAPI 后端，调 DeepSeek API，提供博客聊天功能。

## 部署到 VPS

### 1. 安装依赖

```bash
cd /var/www/yanpy.xyz/backend
python3 -m pip install -r requirements.txt
```

### 2. 设置环境变量

```bash
export DEEPSEAK_API_KEY="你的 DeepSeek API Key"
```

> ⚠️ 注意变量名就是 `DEEPSEAK_API_KEY`（少一个 `E`）—— 代码里是这么读的历史拼写，不要"顺手改正"，改了就读不到 key。

### 3. 启动服务（测试）

```bash
python main.py
# 监听 http://0.0.0.0:8000
```

### 4. systemd 服务（长期运行）

现网的服务名是 **`xiaoyou-blog.service`**（早前文档里写成 `xiaoyou-chat`，是错的）：

```ini
[Unit]
Description=小右博客聊天 API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/yanpy.xyz/backend
Environment="DEEPSEAK_API_KEY=你的key"
ExecStart=/usr/bin/python3 /var/www/yanpy.xyz/backend/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable xiaoyou-blog
sudo systemctl start xiaoyou-blog
```

运维常用：

```bash
systemctl restart xiaoyou-blog          # 改了 main.py 之后必须重启
systemctl status xiaoyou-blog --no-pager -l
journalctl -u xiaoyou-blog -n 40 --no-pager
```

> `main.py` 会按 mtime **热加载** `PUBLIC.md`（人格）和 `blog-index.json`（文章索引），
> 所以**发新文章、改人格都不用重启**，只有改 `main.py` 本身才需要。

### 5. Nginx 反向代理

在 blog 的 nginx 配置（`/etc/nginx/conf.d/yanpy.xyz.conf`，443 的 server 块）中添加：

```nginx
# API 代理
location ^~ /backend/ {
    return 404;      # backend/ 就在网站根目录下，必须屏蔽，否则 main.py 等源码可被公开下载
}

location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

然后 `sudo nginx -t && sudo systemctl reload nginx`。

> 这段 `location ^~ /backend/` 已经于 2026-10-14 在服务器上配置并验证过（`/backend/*` 返回 404）。
> 它的存在很重要：CI 每次部署都会把整个 `backend/` 同步到网站根目录 `/var/www/yanpy.xyz/backend/`，
> 也就是"仓库里有什么，公网就能下载什么"。
