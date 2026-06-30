# Findings & Decisions

## Requirements
- Python 脚本爬取起点三大榜单（月票榜、畅销榜、阅读榜）
- GitHub Actions 每周自动运行
- App 端展示热门推荐，支持网络加载 + 本地 fallback

## Research Findings

### 起点移动端榜单 URL
| 榜单 | URL |
|------|-----|
| 月票榜 | `https://m.qidian.com/rank/yuepiao/` |
| 畅销榜 | `https://m.qidian.com/rank/hotsales/` |
| 阅读榜 | `https://m.qidian.com/rank/readindex/` |

### HTML 结构（CSS Module 类名会变，DOM 层级稳定）
- 列表项：`.y-list__item` 或 `li` 元素
- 书名：`h2` 标签
- 作者：`._subTitle_xxx` 的第一个 text node
- 分类：`._subTitle_xxx` 中 `em` 之后的 sibling
- 简介：`._bookDesc_xxx`
- 封面：`img[data-src]`（懒加载属性）
- 书籍链接：`a[href*="/book/"]`
- 月票数：`._authorBox_xxx` 第一个 `span`
- 畅销榜 badge：`.rank-badge` 或 `._rank_xxx`

### 策略
- 用 `a[href*="/book/"]` + `img[data-src*="bookcover"]` 做属性匹配，不依赖 class 名
- `data-src` 开头是 `//` 协议相对路径，Python 补成 `https:`
- 月票榜 URL 每月变化（`/202606/`），基础路径会自动重定向

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Python 3 + requests + BeautifulSoup | SSR 页面，无需 JS 渲染 |
| User-Agent 设置为移动端 UA | 绕过桌面版反爬 |
| time.sleep(1) 频率控制 | 每周一次的任务，安全不触发限流 |
| JSON 输出到 docs/rankings.json | 便于 GitHub Pages 或 raw.githubusercontent.com 访问 |
| 使用 CSS 属性选择器而非 class 名 | CSS Module hash 会变，属性选择器稳定 |
| .gitignore 中不忽略 docs/*.json | 需要提交到仓库供 App 拉取 |

## Resources
- 起点月票榜: https://m.qidian.com/rank/yuepiao/
- 起点畅销榜: https://m.qidian.com/rank/hotsales/
- 起点阅读榜: https://m.qidian.com/rank/readindex/
