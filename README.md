# GitHub Explore 每日归档

Playwright 使用独立的 Microsoft Edge 登录资料读取 Explore 页面；Codex 每日任务逐个阅读仓库并生成中文分析，最终自动提交到本仓库。

```sh
npm ci
node scripts/collect.mjs --login
npm run collect
npm run extract
```

第一次命令打开专用浏览器，手动登录 GitHub 后关闭该窗口；后续命令以后台模式读取页面，并在 `staging/` 输出正文、HTML、页面状态、截图和仓库清单。

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

完整流程需要 Codex 桌面应用的每日任务和可用的已登录浏览器资料。登录资料仅保存在被忽略的本地目录，不会提交 Cookie 或密码。

已创建每日调度「GitHub Explore 每日推荐归档」（ID：github-explore），默认北京时间每天 09:00，在当前任务中执行。运行时需保持电脑开启、桌面应用运行且浏览器连接可用。可在应用的定时任务中调整时间或暂停。

手动执行：让 Codex 按本项目 `workflow.md` 运行一次。已有分析 JSON 可直接发布：

```sh
npm run publish
```

运行记录按时间分别存储，不覆盖历史。`blocked` 表示采集未完成，不能作为当天推荐日报。
