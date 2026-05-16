# browser-ai-relay

`browser-ai-relay` 是一个面向阿里云 ECS 的个人文本转发服务。它不再把 Playwright 启动的浏览器作为主路径，而是在容器里常驻启动一个普通 Google Chrome，通过 noVNC 人工登录 ChatGPT，再由 FastAPI 通过本地 CDP 附加控制同一个浏览器。

核心目标只有一个：**ECS 上可以人工登录、持久保存登录状态，并稳定完成文本问答闭环**。

## 主架构

容器内进程由 `supervisord` 管理：

- `Xvfb`：虚拟显示器。
- `x11vnc`：把 Xvfb 显示转成 VNC。
- `noVNC`：通过浏览器访问 VNC。
- `google-chrome-stable`：普通 Chrome 常驻运行，使用 `/app/browser_data` 持久 profile。
- `FastAPI`：默认不自动附加 Chrome；登录完成后通过 `http://127.0.0.1:9222` 连接 Chrome CDP，执行文本输入和回复读取。

Chrome 由 supervisor 启动，而不是由 Playwright 启动。这样 noVNC 中用于登录的浏览器和 API 自动化控制的浏览器是同一个实例。

默认流程是 manual-first：

1. 容器启动普通 Chrome、noVNC 和 API。
2. 你先通过 noVNC 在 ECS 里的 Chrome 中手动处理登录、Cloudflare 验证或二次验证。
3. 登录完成后调用 `POST /browser/attach`。
4. 再调用 `/chat` 或 `/v1/chat/completions`。

## 功能范围

第一版只做：

- `GET /healthz`
- `GET /browser-status`
- `POST /browser/attach`
- `POST /browser/detach`
- `POST /chat`
- `POST /v1/chat/completions` 的最小纯文本兼容格式
- 单并发
- 失败 debug dump
- browser profile 持久化

第一版不做：

- 文件上传
- 图片输入
- 图片下载
- DALL-E
- tool calling
- streaming
- 数据库
- 多用户共享

## 环境变量

复制配置：

```bash
cp .env.example .env
```

ECS 主模式应保持：

```env
BROWSER_MODE=ecs_cdp
CDP_URL=http://127.0.0.1:9222
ATTACH_ON_START=false
BROWSER_PROFILE_DIR=/app/browser_data
DEBUG_DIR=/app/logs/debug
```

`ATTACH_ON_START=false` 是 ECS 主路径。它的意思是：API 启动时不主动连接 Chrome，不主动接触登录页或验证页。

`.env.example` 只是示例，不代表生产真实密码。生产值以 ECS 上的 `deploy/ecs/release-meta.env`、`deploy/ecs/runtime.env` 或容器内实际环境变量为准。

注意区分：

- `API_TOKEN`：只用于 API 请求头 `Authorization: Bearer xxx`。
- `VNC_PASSWORD`：只用于 noVNC 页面登录。
- noVNC 密码不是 `API_TOKEN`，不要用 API token 登录 noVNC。
- VNC 协议认证常见限制是只使用前 8 位密码，建议 `VNC_PASSWORD` 使用 8 位以内随机字符串。

本地如果 `8000` 被占用，可以只改宿主机端口：

```env
API_PORT=18000
```

容器内 FastAPI 仍固定监听 `8000`。

本地 compose 默认也只绑定 `127.0.0.1`。不要把 `HOST_NOVNC_BIND` 改成 `0.0.0.0` 后暴露到公网或不可信网络。

## ECS 快速验证

如果要使用 GitHub Actions 自动构建并部署到 ECS，请先看：

```text
docs/github-ecs-auto-deploy.md
```

在 ECS 上完成生产部署后验证：

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'
curl http://127.0.0.1:18000/healthz
```

不要把 noVNC 裸露到公网。推荐从本机建立 SSH 隧道：

```powershell
ssh -L 6080:127.0.0.1:6080 -L 18000:127.0.0.1:18000 root@你的ECS公网IP
```

然后本机浏览器打开：

```text
http://127.0.0.1:6080/vnc.html
```

输入 `VNC_PASSWORD`，在 noVNC 里的 Chrome 中手动登录 ChatGPT。

刚启动、尚未附加时，状态应类似：

```bash
curl -H "Authorization: Bearer 你的_API_TOKEN" http://127.0.0.1:18000/browser-status
```

```json
{
  "chrome_running": true,
  "cdp_attached": false,
  "login_status": "not_attached"
}
```

登录完成后再附加：

```bash
curl -X POST -H "Authorization: Bearer 你的_API_TOKEN" http://127.0.0.1:18000/browser/attach
curl -H "Authorization: Bearer 你的_API_TOKEN" http://127.0.0.1:18000/browser-status
```

理想结果：

```json
{
  "browser_started": true,
  "chrome_running": true,
  "cdp_attached": true,
  "chat_input_found": true,
  "login_status": "probably_logged_in"
}
```

再重启验证 profile 持久化：

```bash
docker compose -p browser-ai-relay --env-file /root/browser-ai-relay/deploy/ecs/runtime.env -f /root/browser-ai-relay/deploy/ecs/compose.prod.yml restart
sleep 30
curl -H "Authorization: Bearer 你的_API_TOKEN" http://127.0.0.1:18000/browser-status
```

重启后需要再次 `POST /browser/attach`。如果 attach 后仍保持 `probably_logged_in`，说明 profile 持久化有效，ECS 路线才值得继续。

## 本地 Docker 验证

本地也可以跑同一套架构：

```powershell
Copy-Item .env.example .env
docker compose up -d --build
curl http://localhost:8000/healthz
```

如果本地 `8000` 被占用，把 `.env` 的 `API_PORT` 改成 `18000`，然后访问：

```powershell
curl http://localhost:18000/healthz
```

noVNC：

```text
http://localhost:6080/vnc.html
```

登录完成后附加浏览器：

```powershell
Invoke-RestMethod -Uri http://localhost:8000/browser/attach `
  -Method Post `
  -Headers @{ Authorization = 'Bearer 你的_API_TOKEN' }
```

## API 测试

普通聊天：

```powershell
$body = @{ message = '你好，用一句话回复我' } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri http://localhost:8000/chat `
  -Method Post `
  -Headers @{ Authorization = 'Bearer 你的_API_TOKEN' } `
  -ContentType 'application/json' `
  -Body $body
```

OpenAI-compatible 最小格式：

```powershell
$body = @{
  model = 'browser-chatgpt'
  messages = @(@{ role = 'user'; content = '你好' })
} | ConvertTo-Json -Depth 5 -Compress

Invoke-RestMethod -Uri http://localhost:8000/v1/chat/completions `
  -Method Post `
  -Headers @{ Authorization = 'Bearer 你的_API_TOKEN' } `
  -ContentType 'application/json' `
  -Body $body
```

## Debug 文件

`/chat` 失败时会在 `logs/debug/时间戳/` 下保存：

- `screenshot.png`
- `page.html`
- `current_url.txt`
- `selector_report.json`
- `error_trace.txt`

后续修 selector 或 detector 时，优先看：

- `src/browser/selectors.py`
- `src/browser/detector.py`
- `src/browser/chatgpt_page.py`

## 可行性判断

如果 ECS 上 noVNC 里的 Chrome 在未附加 CDP 的状态下仍无法人工登录 ChatGPT，或者重启并重新 attach 后无法保留登录状态，应暂停继续开发 API/selector，先重新评估 ECS IP、地域、浏览器环境或账号状态。这个项目的成功标准不是本地能跑，而是 ECS 上能稳定登录和运行。

## 排查

生产排查入口见：

```text
docs/troubleshooting.md
```

重点命令：

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'
docker inspect browser-ai-relay --format '{{json .Config.Labels}}' | python3 -m json.tool
docker exec browser-ai-relay printenv | grep -E 'VNC_PASSWORD|API_TOKEN|API_PORT|NOVNC_PORT|HOST_API_PORT|HOST_NOVNC_PORT'
docker exec browser-ai-relay tail -n 100 /app/logs/x11vnc.log
docker exec browser-ai-relay tail -n 100 /app/logs/novnc.log
docker exec browser-ai-relay tail -n 100 /app/logs/api.log
```

如果 `docker compose ps` 为空，但 `docker ps` 能看到容器，优先用 `docker inspect` 查看 `com.docker.compose.project` 和 `com.docker.compose.project.config_files`，确认真实 compose 来源。
