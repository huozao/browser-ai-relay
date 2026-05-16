# browser-ai-relay 排查手册

本文只针对独立部署的 `browser-ai-relay`。AliECS 主站仍使用 `/root/AliECS`，本项目默认使用 `/root/browser-ai-relay` 和 `/root/browser-ai-relay-data`。

## 访问入口

生产部署默认只绑定本机地址，不开放公网端口。

SSH 隧道：

```bash
ssh -L 6080:127.0.0.1:6080 -L 18000:127.0.0.1:18000 root@ECS_IP
```

noVNC 地址：

```text
http://127.0.0.1:6080/vnc.html
```

browser-ai-relay API 地址：

```text
http://127.0.0.1:18000
```

容器内 API 仍监听 `8000`，生产宿主机映射为 `127.0.0.1:18000->8000`，避免和 AliECS backend-api 的 `127.0.0.1:8000` 冲突。

## 密码和 token 区分

- `API_TOKEN`：只用于 HTTP API，例如 `Authorization: Bearer xxx`。
- `VNC_PASSWORD`：只用于 noVNC 页面登录。
- noVNC 密码不是 API token，不要用 `API_TOKEN` 登录 noVNC。
- `.env.example` 只是本地示例，不代表生产真实密码。
- 生产 noVNC 密码以实际部署 env 为准：`release-meta.env`、`runtime.env` 或容器内 `VNC_PASSWORD`。
- VNC_PASSWORD 如果超过 8 位，VNC 认证可能只使用前 8 位。建议生产 `VNC_PASSWORD` 使用 8 位以内随机字符串。

不要把真实 `API_TOKEN`、`VNC_PASSWORD`、`GHCR_TOKEN` 粘贴到公开 issue、PR、聊天或日志里。

## 查询当前容器

查看运行容器：

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'
```

查看容器归属哪个 Docker Compose project：

```bash
docker inspect browser-ai-relay --format '{{json .Config.Labels}}' | python3 -m json.tool
```

重点看：

```text
com.docker.compose.project
com.docker.compose.service
com.docker.compose.project.working_dir
com.docker.compose.project.config_files
```

如果 `docker compose ps` 为空，但 `docker ps` 能看到 `browser-ai-relay`，说明你可能不在真实 compose project 下，或者 compose project name 不同。应以 `docker inspect` 的 compose labels 为准。

GitHub Actions 自动部署时，ECS 上 `/root/browser-ai-relay` 应作为部署 checkout 使用，不建议手动修改 tracked 文件。新版 workflow 在同步 `origin/main` 前会把 tracked 本地修改保存到 git stash，避免 `git pull --ff-only` 被 `deploy/ecs/*.sh` 等本地改动阻塞。私有配置仍只应放在 ignored 文件里，例如 `deploy/ecs/release-meta.env`。

新的生产部署脚本会显式使用：

```text
COMPOSE_PROJECT_NAME=browser-ai-relay
docker compose -p browser-ai-relay ...
```

旧部署如果显示 `Project=ecs`，通常是历史版本从 `deploy/ecs` 目录名推导出来的 project name。

## 查询实际环境变量

以下命令会输出敏感变量是否存在。不要把真实值发到公共地方；如需粘贴给排障，只保留长度或手动打码。

```bash
docker exec browser-ai-relay printenv | grep -E 'VNC_PASSWORD|API_TOKEN|API_PORT|NOVNC_PORT|HOST_API_PORT|HOST_NOVNC_PORT'
```

含义：

- `VNC_PASSWORD`：noVNC 登录密码来源。
- `API_TOKEN`：API Authorization token 来源。
- `API_PORT=8000`：容器内 API 端口。
- 生产宿主机 API 端口通常是 `18000`，来自 compose 映射，不一定出现在容器环境变量里。

## 查询日志

```bash
docker exec browser-ai-relay tail -n 100 /app/logs/x11vnc.log
docker exec browser-ai-relay tail -n 100 /app/logs/novnc.log
docker exec browser-ai-relay tail -n 100 /app/logs/api.log
```

如果启动时 `VNC_PASSWORD` 超过 8 位，容器启动日志应出现：

```text
WARNING: VNC_PASSWORD is longer than 8 chars; VNC authentication may only use the first 8 chars.
```

该警告不会打印完整密码。

## 生产 compose 操作

生产部署目录：

```bash
cd /root/browser-ai-relay
```

查看生产 compose：

```bash
docker compose -p browser-ai-relay \
  --env-file /root/browser-ai-relay/deploy/ecs/runtime.env \
  -f /root/browser-ai-relay/deploy/ecs/compose.prod.yml \
  ps
```

健康检查：

```bash
curl -fsS http://127.0.0.1:18000/healthz
```

浏览器状态：

```bash
curl -H "Authorization: Bearer 你的_API_TOKEN" \
  http://127.0.0.1:18000/browser-status
```

## 从旧 Project=ecs 迁移

旧版本可能创建了 `Project=ecs` 的 `browser-ai-relay` 容器。迁移到显式 `Project=browser-ai-relay` 时，如果部署报容器名冲突，可手动删除旧容器后重新部署：

```bash
docker rm -f browser-ai-relay
cd /root/browser-ai-relay
deploy/ecs/deploy.sh V实际版本号
```

删除前先确认它确实是 browser-ai-relay 容器，不要对 AliECS 主站服务执行删除。

## 与 AliECS 的端口边界

AliECS：

```text
127.0.0.1:8080 -> public-web
127.0.0.1:8081 -> admin-ui
127.0.0.1:8000 -> backend-api
```

browser-ai-relay：

```text
127.0.0.1:6080  -> noVNC
127.0.0.1:18000 -> API
```

不要修改安全组开放 `6080` 或 `18000`。只通过 SSH 隧道访问 noVNC 和 API。
