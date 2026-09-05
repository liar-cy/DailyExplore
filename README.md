# GitHub Explore 每日归档

Playwright 从本机 Microsoft Edge 默认配置读取并解密 GitHub 登录 Cookie，只在采集进程内存中注入浏览器；Codex 每日任务逐个阅读个性化推荐仓库并生成中文分析，最终自动提交到本仓库。Cookie 明文不会写入项目文件或日志。

```sh
npm ci
node scripts/collect.mjs --login
npm run collect
npm run extract
```

确保普通 Microsoft Edge 已登录 GitHub；后续命令以后台模式复用该登录 Cookie，并在 `staging/` 输出正文、HTML、页面状态、截图和仓库清单。macOS 首次读取 Edge 钥匙串时可能要求确认访问权限。

普通 Edge 连接模式：

```sh
npm run edge:start
npm run collect:edge
```

`edge:start` 由 Edge 自己打开一个允许本机调试的窗口。先在该窗口人工登录 GitHub；`collect` 随后通过 `127.0.0.1:9222` 连接并读取页面。调试接口只监听本机。Chromium 不允许对正在使用的默认资料目录直接开启调试，因此这里用 `.edge-cdp-profile/` 保存登录，无法直接复用当前普通 Edge 的默认资料。

使用 Codex 每日调度，通过浏览器插件读取已登录 GitHub 的 Explore 页面，逐个阅读推荐仓库并生成中文 Markdown 日报和 JSON 归档。

- `workflow.md`：采集、总结及失败处理流程。
- `scripts/archive.py`：无第三方依赖的 Python 3.9+ 归档脚本。
- `reports/日期/运行时间/report.md`：可阅读日报。
- `reports/日期/运行时间/data.json`：结构化记录。

完整流程需要 Codex 桌面应用的每日任务，以及普通 Microsoft Edge 中有效的 GitHub 登录状态。

已创建 Codex 项目任务「GitHub Explore 每日推荐归档」（ID：github-explore-2），默认北京时间每天 09:00 执行。运行时需保持电脑开启、Codex 桌面应用运行且专用浏览器资料已登录 GitHub。可在应用的定时任务中调整时间或暂停。

手动执行：让 Codex 按本项目 `workflow.md` 运行一次。已有分析 JSON 可直接发布：

```sh
npm run publish
```

运行记录按时间分别存储，不覆盖历史。`blocked` 表示采集未完成，不能作为当天推荐日报。
