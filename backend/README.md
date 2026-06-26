# 小右博客聊天后端

FastAPI 后端，调 DeepSeek API，提供博客聊天功能。

## 部署到 VPS

### 1. 安装依赖

```bash
cd /path/to/blog/backend
pip install -r requirements.txt
```

### 2. 设置环境变量

```bash
export DEEPSEEK_API_KEY="你的 DeepSeek API Key"
```

### 3. 启动服务（测试）

```bash
python main.py
# 监听 http://0.0.0.0:8000
```

### 4. systemd 服务（长期运行）

创建 `/etc/systemd/system/xiaoyou-chat.service`：

```ini
[Unit]
Description=小右博客聊天 API
After=network.target

[Service]
Type=simple
User=你的用户名
WorkingDirectory=/path/to/blog/backend
Environment="DEEPSEEK_API_KEY=你的key"
ExecStart=/usr/bin/python3 /path/to/blog/backend/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable xiaoyou-chat
sudo systemctl start xiaoyou-chat
```

### 5. Nginx 反向代理

在 blog 的 nginx 配置中添加：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

然后 `sudo nginx -s reload`
