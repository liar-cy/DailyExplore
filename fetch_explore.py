#!/usr/bin/env python3
"""抓取 GitHub Explore 主页推荐仓库并生成 Markdown 报告。

用法: python3 fetch_explore.py [-o output.md]
"""
import argparse
import datetime as dt
import html as htmllib
import json
import os
import re
import urllib.request

EXPLORE_URL = "https://github.com/explore"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

CARD_RE = re.compile(r'<article[^>]*>.*?</article>', re.S)


def fetch(url: str, cookie: str = "") -> str:
    headers = dict(HEADERS)
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def is_logged_in(page: str) -> bool:
    """页面 hydro 埋点里 logged_in:true 表示是登录用户的个性化页面。"""
    return 'logged_in:true' in page


def first(pattern: str, text: str, group=1):
    m = re.search(pattern, text)
    return htmllib.unescape(m.group(group)).strip() if m else ""


def parse_cards(page: str) -> list[dict]:
    repos = []
    for card in CARD_RE.findall(page):
        if 'click_context&quot;:&quot;REPOSITORY_CARD' not in card:
            continue
        owner = first(r'click_target&quot;:&quot;OWNER&quot;.*?href="/([^/"]+)"', card)
        name = first(r'click_target&quot;:&quot;REPOSITORY&quot;.*?href="/[^"]+/([^"?#]+)"', card)
        if not name:
            continue
        repos.append({
            "owner": owner,
            "name": name,
            "full_name": f"{owner}/{name}",
            "url": f"https://github.com/{owner}/{name}",
            "category": first(r'<h2[^>]*>\s*(?:<span.*?</span>)?\s*([\w\s]+?)\s*</h2>', card),
            "description": first(r'<p class="color-fg-muted mb-0"[^>]*>(.*?)</p>', card),
            "language": first(r'itemprop="programmingLanguage">([^<]+)<', card),
            "stars": first(r'aria-label="([\d,]+) users? starred this repository"', card).replace(",", ""),
            "updated": first(r'<relative-time datetime="([^"]+)"', card),
        })
    # 去重保持顺序
    seen, out = set(), []
    for r in repos:
        if r["full_name"] not in seen:
            seen.add(r["full_name"])
            out.append(r)
    return out


def enrich_from_api(repos: list[dict]) -> None:
    """用 GitHub 公共 API 补全描述/star 数（无 token 限流 60 次/小时）。"""
    for r in repos:
        if r["description"]:
            continue
        try:
            req = urllib.request.Request(
                f"https://api.github.com/repos/{r['full_name']}",
                headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.load(resp)
            r["description"] = data.get("description") or ""
            r["stars"] = str(data.get("stargazers_count", ""))
            r["language"] = r["language"] or (data.get("language") or "")
            r["topics"] = ", ".join(data.get("topics", []))
        except Exception:
            pass


def render_md(repos: list[dict]) -> str:
    today = dt.date.today().isoformat()
    lines = [
        f"# GitHub Explore 推荐仓库 · {today}",
        "",
        f"> 数据来源: [github.com/explore]({EXPLORE_URL})，共 {len(repos)} 个仓库。",
        "",
        "| 仓库 | 语言 | Stars | 简介 |",
        "| --- | --- | --- | --- |",
    ]
    for r in repos:
        desc = r["description"].replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| [{r['full_name']}]({r['url']}) "
            f"| {r.get('language') or '-'} "
            f"| {r['stars'] or '-'} "
            f"| {desc or '-'} |")
    lines.append("")
    lines.append("## 详细介绍")
    lines.append("")
    for i, r in enumerate(repos, 1):
        meta = [f"分类: {r['category']}"] if r.get("category") else []
        meta += [x for x in [
            f"[仓库主页]({r['url']})",
            f"语言: {r['language']}" if r.get("language") else "",
            f"Stars: {int(r['stars']):,}" if r.get("stars") else "",
            f"更新: {r['updated'][:10]}" if r.get("updated") else "",
        ] if x]
        lines.append(f"### {i}. [{r['full_name']}]({r['url']})")
        if meta:
            lines.append("")
            lines.append("- " + " · ".join(meta))
        if r["description"]:
            lines.append("")
            lines.append(r["description"])
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="explore_repos.md")
    ap.add_argument("--html-file", type=argparse.FileType("r", encoding="utf-8"),
                    help="解析浏览器已经保存的 HTML，不再发起网页请求")
    ap.add_argument("--json-output", help="同时输出供 Codex 分析的仓库清单 JSON")
    ap.add_argument("-c", "--cookie", default="",
                    help="GitHub 登录 Cookie，如 user_session=xxx。也可用环境变量 GH_COOKIE")
    ap.add_argument("--raw", action="store_true",
                    help="把原始 HTML 保存到 /tmp/explore.html 便于调试")
    args = ap.parse_args()

    cookie = args.cookie or os.environ.get("GH_COOKIE", "")
    page = args.html_file.read() if args.html_file else fetch(EXPLORE_URL, cookie)
    if args.raw:
        with open("/tmp/explore.html", "w", encoding="utf-8") as f:
            f.write(page)
    repos = parse_cards(page)
    if not repos:
        raise SystemExit("未解析到推荐仓库卡片，页面结构可能已变化")
    if cookie and not is_logged_in(page):
        print("警告: Cookie 未生效，当前抓取的是未登录的公共推荐页", file=__import__("sys").stderr)
    enrich_from_api(repos)
    if args.json_output:
        payload = {
            "observed_at": dt.datetime.now().astimezone().isoformat(),
            "source": EXPLORE_URL,
            "logged_in": is_logged_in(page),
            "repositories": repos,
        }
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
    md = render_md(repos)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"OK: 解析到 {len(repos)} 个推荐仓库 -> {args.output}")


if __name__ == "__main__":
    main()
