# AGENTS.md

## 项目目标

`browser-ai-relay` 的最终目标是在阿里云 ECS 上稳定运行一个个人用的文本转发服务。

主架构是：容器内由 supervisor 常驻启动普通 Google Chrome，Chrome 显示在 Xvfb/noVNC 中供人工登录，FastAPI 通过本地 CDP (`127.0.0.1:9222`) 附加控制同一个浏览器。

第一版只做文本问答闭环：FastAPI 接收文本问题，浏览器中打开 ChatGPT，自动输入问题，等待回复完成，读取最后一条 assistant 回复，并返回 JSON。

默认采用 manual-first 流程：容器启动后只启动 Chrome/noVNC/API，不自动附加 CDP；用户必须先通过 noVNC 人工完成登录和验证，再调用 `/browser/attach`。

## 禁止事项

- 不做账号池、多用户共享系统、数据库、复杂 TUI。
- 不做 DALL-E、文件上传、图片输入、图片下载、tool calling、streaming。
- 不把 noVNC 或 CDP 端口直接暴露到公网。

## 开发原则

- ECS 可行性优先：如果 ECS 上 noVNC 里的普通 Chrome 无法人工完成登录和验证，应暂停继续开发 API/selector，先重新评估方案。
- 登录页、Cloudflare 验证页、二次验证页必须人工处理；后端不要自动点击验证、自动刷新验证页或尝试挑战破解。
- `ATTACH_ON_START` 默认保持 `false`，除非明确需要本地诊断，不要改成默认自动附加。
- Host Chrome/CDP 只能作为本地诊断工具，不能作为最终方案。
- 最小闭环优先，不要恢复参考项目里的复杂功能。
- 只做文本问答；不要加入文件上传、图片输入、图片下载或 DALL-E。
- 可以保留有助于浏览器稳定访问和稳定读取回复的辅助能力，例如持久 profile、headful/noVNC、锁文件清理、轻量延迟、hover click、viewport jitter、可配置 stealth 兼容补丁。
- selector 必须集中在 `src/browser/selectors.py`。
- `/chat` 失败时必须保存 debug 文件，方便后续修 selector 或 detector。
- 所有说明、README、面向用户的维护说明都用中文。
- 如果真实 ChatGPT 登录无法自动验证，必须明确说明。

## 修改后验证

- 修改 Python 代码后必须运行 `pytest`。
- 涉及 Docker、Compose、端口、volume、环境变量或启动脚本时，必须运行 `docker compose config`。
- 如果 Docker 环境允许，涉及 Docker 修改后尽量运行 `docker compose build`。
