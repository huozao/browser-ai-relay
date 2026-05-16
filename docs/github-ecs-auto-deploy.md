# GitHub 到阿里云 ECS 自动部署指南

本文说明如何把独立项目 `browser-ai-relay` 推送到 GitHub 后，自动构建镜像并部署到阿里云 ECS。

目标仓库：

```text
https://github.com/huozao/browser-ai-relay
```

ECS 目录约定：

```text
/root/browser-ai-relay
```

运行数据目录约定：

```text
/root/browser-ai-relay-data/browser_data
/root/browser-ai-relay-data/logs
```

这个项目不要放进 `/root/AliECS`。它可以参考 AliECS 的自动部署方式，但保持独立目录、独立 compose、独立浏览器 profile。

## 部署结构

流程如下：

1. 你把代码推送到 `huozao/browser-ai-relay` 的 `main`。
2. GitHub Actions 构建镜像：

```text
ghcr.io/huozao/browser-ai-relay:VYYYYMMDDNNN
```

3. GitHub Actions 通过 SSH 登录 ECS。
4. ECS 中 `/root/browser-ai-relay` 拉取最新 `main`。
5. ECS 还原私密配置：

```text
/root/browser-ai-relay/deploy/ecs/release-meta.env
/root/browser-ai-relay/deploy/ecs/runtime.env
```

6. 执行：

```bash
/root/browser-ai-relay/deploy/ecs/deploy.sh <tag>
```

7. `docker compose -p browser-ai-relay` 拉取 GHCR 镜像并启动服务。
8. 只检查 `/healthz` 和 `/browser-status`，不会自动调用 `/chat`。

## GitHub Secrets

进入 GitHub 仓库：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

需要配置：

```text
ECS_HOST
ECS_USER
ECS_SSH_KEY
GHCR_USERNAME
GHCR_TOKEN
```

说明：

- `ECS_HOST`：ECS 公网 IP 或域名，例如 `1.2.3.4`。
- `ECS_USER`：通常是 `root`。
- `ECS_SSH_KEY`：可以登录 ECS 的私钥全文，包含 `-----BEGIN ...-----` 和 `-----END ...-----`。
- `GHCR_USERNAME`：GitHub 用户名或组织可用账号，例如 `huozao`。
- `GHCR_TOKEN`：GitHub Personal Access Token，至少需要 `read:packages`。如果 GHCR package 是私有的，这个必填。

GitHub Actions 推送镜像使用仓库自带的 `GITHUB_TOKEN`，不需要你单独配置 push token。

## ECS 首次准备

SSH 登录 ECS：

```bash
ssh root@你的ECS公网IP
```

确认 Docker 和 Compose 可用：

```bash
docker --version
docker compose version
```

如果 ECS 已经能跑 AliECS，一般这里已经具备 Docker 环境。

克隆项目到固定目录：

```bash
cd /root
git clone https://github.com/huozao/browser-ai-relay.git /root/browser-ai-relay
cd /root/browser-ai-relay
```

创建持久化目录：

```bash
mkdir -p /root/browser-ai-relay-data/browser_data
mkdir -p /root/browser-ai-relay-data/logs
```

创建 ECS 私密配置：

```bash
cp deploy/ecs/release-meta.env.example deploy/ecs/release-meta.env
chmod 600 deploy/ecs/release-meta.env
chmod +x deploy/ecs/*.sh
```

生成 API token 和 VNC 密码：

```bash
openssl rand -hex 32
openssl rand -hex 4
```

编辑：

```bash
nano deploy/ecs/release-meta.env
```

至少修改：

```env
GHCR_BASE=ghcr.io/huozao

API_TOKEN=替换为 openssl rand -hex 32 生成的值
VNC_PASSWORD=替换为 openssl rand -hex 4 生成的 8 位值

HOST_API_BIND=127.0.0.1
HOST_API_PORT=18000
HOST_NOVNC_BIND=127.0.0.1
HOST_NOVNC_PORT=6080

ATTACH_ON_START=false
```

如果 GHCR 镜像是私有包，还要填：

```env
GHCR_USERNAME=你的GitHub用户名
GHCR_TOKEN=具有 read:packages 权限的 PAT
```

不要提交真实的 `release-meta.env`。

`API_TOKEN` 用于 HTTP API 的 `Authorization: Bearer xxx`；`VNC_PASSWORD` 用于 noVNC 登录。两者不能混用。`.env.example` 只是示例，不代表生产真实密码。VNC 协议认证常见限制是只使用前 8 位密码，生产 `VNC_PASSWORD` 建议保持 8 位以内。

## 首次手动部署验证

第一次可以手动跑一次部署脚本，确认 ECS 侧没有环境问题。

先在 GitHub Actions 成功构建出一个 tag 后，使用实际 tag：

```bash
cd /root/browser-ai-relay
deploy/ecs/deploy.sh V20260516001
```

如果只是想先验证 compose 文件：

```bash
docker compose -p browser-ai-relay --env-file deploy/ecs/runtime.env.example \
  -f deploy/ecs/compose.prod.yml \
  config
```

查看容器：

```bash
docker compose -p browser-ai-relay --env-file deploy/ecs/runtime.env \
  -f deploy/ecs/compose.prod.yml \
  ps
```

健康检查：

```bash
curl -fsS http://127.0.0.1:18000/healthz
```

## noVNC 访问方式

不要把 noVNC 暴露公网。生产 compose 默认只绑定：

```text
127.0.0.1:6080
```

从本地电脑建立 SSH 隧道：

```bash
ssh -L 6080:127.0.0.1:6080 -L 18000:127.0.0.1:18000 root@你的ECS公网IP
```

本地浏览器打开：

```text
http://127.0.0.1:6080/vnc.html
```

输入 `VNC_PASSWORD`，在 noVNC 里的 Chrome 手动登录 ChatGPT。

登录完成后附加：

```bash
curl -X POST \
  -H "Authorization: Bearer 你的_API_TOKEN" \
  http://127.0.0.1:18000/browser/attach
```

检查状态：

```bash
curl -H "Authorization: Bearer 你的_API_TOKEN" \
  http://127.0.0.1:18000/browser-status
```

理想状态：

```json
{
  "chrome_running": true,
  "cdp_attached": true,
  "chat_input_found": true,
  "login_status": "probably_logged_in"
}
```

测试文本请求：

```bash
curl -sS \
  -H "Authorization: Bearer 你的_API_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data '{"message":"请只回复 OK"}' \
  http://127.0.0.1:18000/chat
```

## 推送触发自动部署

本地项目如果还不是 Git 仓库，先初始化：

```bash
git init
git branch -M main
git remote add origin https://github.com/huozao/browser-ai-relay.git
```

提交：

```bash
git add .
git commit -m "Add ECS auto deploy pipeline"
```

推送：

```bash
git push -u origin main
```

推送 `main` 后会触发 `.github/workflows/release-deploy.yml`，工作流名称是 `browser-ai-relay-release-deploy`：

- 构建 GHCR 镜像。
- SSH 到 ECS。
- 同步 `/root/browser-ai-relay`。
- 保留 ECS 私密 env。
- 运行 `deploy/ecs/deploy.sh`。
- 运行 `deploy/ecs/post-deploy-smoke.sh`。

也可以在 GitHub Actions 页面手动运行 `browser-ai-relay-release-deploy`，输入版本号：

```text
V20260516001
```

版本号格式必须是：

```text
VYYYYMMDDNNN
```

## 和 AliECS 的关系

AliECS 当前目录是：

```text
/root/AliECS
```

browser-ai-relay 独立目录是：

```text
/root/browser-ai-relay
```

二者不要混放。原因：

- browser-ai-relay 有持久浏览器 profile。
- noVNC 是人工接管入口，安全边界更敏感。
- Chrome 镜像更重，和 AliECS 主站发布节奏不同。
- AliECS 的 backend-api 已使用本机 `127.0.0.1:8000`，browser-ai-relay 使用 `127.0.0.1:18000` 避免冲突。

后续如果需要 AliECS 调用 browser-ai-relay，建议由 AliECS backend-api 通过本机地址调用：

```text
http://127.0.0.1:18000
```

但不要把 browser-ai-relay 直接暴露公网。

## 常见问题

### GitHub Actions 提示 ECS 找不到 `/root/browser-ai-relay`

说明还没做 ECS 首次准备。先 SSH 到 ECS 执行：

```bash
git clone https://github.com/huozao/browser-ai-relay.git /root/browser-ai-relay
```

### GHCR pull unauthorized

检查：

- GitHub repo secrets 是否有 `GHCR_USERNAME`、`GHCR_TOKEN`。
- ECS 的 `release-meta.env` 是否也配置了 `GHCR_USERNAME`、`GHCR_TOKEN`。
- PAT 是否有 `read:packages`。
- GHCR package 是否设为 public。

### noVNC 打不开

确认 SSH 隧道还在：

```bash
ssh -L 6080:127.0.0.1:6080 -L 18000:127.0.0.1:18000 root@你的ECS公网IP
```

确认容器端口：

```bash
docker compose -p browser-ai-relay --env-file /root/browser-ai-relay/deploy/ecs/runtime.env \
  -f /root/browser-ai-relay/deploy/ecs/compose.prod.yml \
  ps
```

如果旧容器显示 `Project=ecs`，新版部署会使用 `Project=browser-ai-relay`。部署脚本会在确认旧容器属于其他 Compose project 时自动移除旧的 `browser-ai-relay` 容器。如果仍然遇到容器名冲突，先确认目标是 browser-ai-relay 容器，再执行：

```bash
docker rm -f browser-ai-relay
```

然后重跑部署。

### 登录失效

打开 noVNC 人工重新登录，然后：

```bash
curl -X POST \
  -H "Authorization: Bearer 你的_API_TOKEN" \
  http://127.0.0.1:18000/browser/attach
```

### 查看日志

```bash
docker compose -p browser-ai-relay --env-file /root/browser-ai-relay/deploy/ecs/runtime.env \
  -f /root/browser-ai-relay/deploy/ecs/compose.prod.yml \
  logs --tail=200 browser-ai-relay
```

持久日志目录：

```text
/root/browser-ai-relay-data/logs
```

debug dump：

```text
/root/browser-ai-relay-data/logs/debug
```
