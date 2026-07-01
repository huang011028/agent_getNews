# 每日 AI 新闻抓取 · 总结 · 邮件推送 Agent 框架设计

> 目标:用 **GitHub Actions** 定时(每天)自动执行 —— 抓取新闻 → **筛选出 AI 相关内容** → AI 总结 → 邮件推送。全程无需自己维护服务器。
>
> 🎯 **核心定位**:只关注 **人工智能 / 大模型 / 机器学习** 领域的新闻,其余主题一律过滤掉。

---

## 一、整体流程

```
graph TB
    A[GitHub Actions 定时触发] --> B[抓取新闻]
    B --> C[清洗 / 去重]
    C --> D[AI 相关性过滤]
    D --> E[调用 AI 总结]
    E --> F[生成邮件内容]
    F --> G[SMTP 发送邮件]
    G --> H[可选: 归档到仓库/存储]
```

1. **定时触发**:GitHub Actions 的 `schedule` (cron) 每天定点运行。
2. **抓取新闻**:优先订阅 AI 垂直 RSS 源 / 新闻 API,也可从综合源抓取后再过滤。
3. **清洗去重**:过滤无效内容、按标题/链接去重、截断过长正文。
4. **AI 相关性过滤**:核心环节 —— 只保留与 AI/大模型/机器学习相关的新闻(关键词 + 可选语义判断)。
5. **AI 总结**:调用大模型 API 对筛选后的 AI 新闻做摘要、分类、提炼要点。
6. **生成邮件**:把总结渲染成 HTML/纯文本邮件模板。
7. **邮件推送**:用 SMTP(如 QQ 邮箱、Gmail、企业邮箱)发送。
8. **可选归档**:把每日结果写入仓库 `archive/` 或推送到 Notion/数据库。

---

## 二、技术选型

| 模块 | 推荐方案 | 备选 |
| --- | --- | --- |
| 运行环境 | GitHub Actions (Ubuntu runner) | 本地 cron / 云函数 |
| 语言 | Python 3.11+ | Node.js |
| 新闻来源 | AI 垂直 RSS(见下表)| NewsAPI(`q=AI`)/ 聚合数据 / 网页爬取 |
| 抓取库 | `requests` + `feedparser` | `httpx` / `playwright` |
| **AI 相关性过滤** | 关键词匹配(快、免费) | 大模型语义判断(准、更花 token) |
| AI 总结 | DeepSeek V4 Pro（OpenAI 兼容）| OpenAI / 通义千问 / 本地模型 |
| 邮件发送 | `smtplib` + `email` | SendGrid / Resend API |
| 配置管理 | GitHub Secrets | `.env`(本地) |

---

## 三、目录结构

```
agent_getNews/
├── .github/
│   └── workflows/
│       └── daily_news.yml       # GitHub Actions 定时任务配置
├── src/
│   ├── fetch_news.py            # 抓取新闻(RSS/API)
│   ├── ai_filter.py             # ⭐ AI 相关性过滤(关键词/语义)
│   ├── summarize.py             # 调用 AI 总结
│   ├── send_email.py            # SMTP 发送邮件
│   ├── render.py                # 邮件模板渲染
│   └── config.py                # 读取环境变量/配置
├── config/
│   ├── sources.yaml             # AI 新闻源列表(RSS 地址等)
│   └── keywords.yaml            # ⭐ AI 关键词/过滤规则
├── archive/                     # 每日归档(可选)
├── main.py                      # 主入口:串联全流程
├── requirements.txt             # Python 依赖
├── .env.example                 # 本地环境变量示例
└── README.md
```

---

## 四、核心模块说明

### 1. AI 新闻源配置 `config/sources.yaml`
> 优先选用 AI 垂直媒体,可最大限度减少后续过滤成本。
```yaml
sources:
  # —— AI 垂直源(强相关,推荐)——
  - name: 机器之心
    type: rss
    url: https://www.jiqizhixin.com/rss
  - name: MIT Tech Review - AI
    type: rss
    url: https://www.technologyreview.com/topic/artificial-intelligence/feed
  - name: Hugging Face Blog
    type: rss
    url: https://huggingface.co/blog/feed.xml
  - name: Google AI Blog
    type: rss
    url: https://blog.google/technology/ai/rss/
  # —— 综合源(需过滤,可选)——
  - name: 36氪
    type: rss
    url: https://36kr.com/feed
    needs_filter: true       # 综合源:抓取后必须过 AI 过滤
max_items_per_source: 15     # 每个源最多取几条
```

### 2. AI 关键词配置 `config/keywords.yaml`
```yaml
# 命中任一关键词即视为 AI 相关(不区分大小写)
include:
  - AI
  - 人工智能
  - 大模型
  - 机器学习
  - 深度学习
  - 神经网络
  - LLM
  - GPT
  - 生成式
  - AIGC
  - 大语言模型
  - Transformer
  - 多模态
  - 智能体
  - Agent
# 命中即排除(减少误伤,如"AI 换脸诈骗"这类噪声可按需调整)
exclude: []
# 过滤策略:keyword(仅关键词) | semantic(仅大模型判断) | hybrid(先关键词再语义兜底)
strategy: hybrid
```

### 3. 抓取 `src/fetch_news.py`
- 读取 `sources.yaml`,遍历 RSS 源。
- 用 `feedparser` 解析,提取 `title / link / summary / published`。
- 按发布时间过滤(只取最近 24h),按 link 去重。

### 4. ⭐ AI 相关性过滤 `src/ai_filter.py`(核心)
- 读取 `keywords.yaml`,对每条新闻的 `标题 + 摘要` 做判断。
- **keyword 策略**:命中 `include` 且不命中 `exclude` → 保留。快、零成本。
- **semantic 策略**:把标题批量丢给大模型,问"是否属于 AI 领域",返回布尔。准、花 token。
- **hybrid 策略(推荐)**:先关键词粗筛;对"疑似但没命中关键词"的再用语义兜底。
- 标记来源为 `needs_filter: true` 的综合源**必过**此环节;AI 垂直源可跳过或轻过。
- 输出:只含 AI 相关新闻的列表。

### 5. 总结 `src/summarize.py`
- 把**过滤后的** AI 新闻拼成 prompt。
- 调用 AI API,要求严格按下方「邮件输出格式规范」产出:
  - 一句吸睛导语开头(如「今日 AI 圈核心动态已打包,快报速览」)。
  - 编号快报列表,每条**一句话标题**(公司/产品 + 核心事件,不超过 30 字)。
  - 每条关联原文链接(供末尾链接区引用)。
- 返回结构化文本(Markdown / HTML)。

### 6. 邮件 `src/send_email.py` + `src/render.py`
- `render.py`:将总结转成 HTML 邮件模板(标题如「每日 AI 速报 · YYYY-MM-DD」),严格遵循「邮件输出格式规范」。
- `send_email.py`:用 `smtplib` 通过 SMTP 服务器发送。

#### ⭐ 邮件输出格式规范(目标范式)
邮件正文分三部分:**导语 → 编号快报速览 → 完整链接列表**。示例:

```
📮 今日 AI 圈核心动态已打包,快报速览

1. 美团发布 LongCat-2.0 万亿参数大模型,全程国产算力训练
2. DeepSeek V4 Pro/V4 Flash 高峰时段 API 价格翻倍
3. Anthropic Claude 正式上线微软 Azure 平台
4. 优艾智合具身智能系列新品发布,拟 3 年赋能 10000 个工业现场
5. 韩国宣布巨额芯片与 AI 新投资计划

—— 完整链接 ——
[1] https://example.com/longcat-2
[2] https://example.com/deepseek-v4
[3] https://example.com/claude-azure
[4] https://example.com/youai-robot
[5] https://example.com/korea-chip-ai
```

**规范要点**:
- 导语一句话,营造"打包速览"氛围。
- 快报用数字编号,每条一句话,突出**主体 + 事件**,控制在一行内。
- 链接区与快报**编号一一对应**,放在正文末尾统一列出。
- HTML 版:快报编号加粗,链接可点击(`<a href>`),整体简洁清爽。

### 7. 主入口 `main.py`
```
fetch → dedup → ai_filter → summarize → render → send → (archive)
```
> 若某天过滤后无 AI 新闻,可选择不发信或发送「今日无 AI 相关更新」。

---

## 五、GitHub Actions 配置要点

`.github/workflows/daily_news.yml`
```yaml
name: Daily AI News Agent
on:
  schedule:
    - cron: '0 23 * * *'   # UTC 23:00 = 北京时间 07:00
  workflow_dispatch:        # 支持手动触发
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASS: ${{ secrets.SMTP_PASS }}
          MAIL_TO: ${{ secrets.MAIL_TO }}
```

> ⚠️ cron 用的是 **UTC 时间**,需减 8 小时换算北京时间。

---

## 六、需要配置的 Secrets(GitHub 仓库 Settings → Secrets)

| 名称 | 说明 |
| --- | --- |
| `OPENAI_API_KEY` | AI 模型 API Key |
| `SMTP_HOST` | 邮件服务器,如 `smtp.qq.com` |
| `SMTP_USER` | 发件邮箱账号 |
| `SMTP_PASS` | 邮箱授权码(非登录密码) |
| `MAIL_TO` | 收件人邮箱(可多个,逗号分隔) |

---

## 七、实施步骤(建议顺序)

1. **搭骨架**:建目录 + `requirements.txt` + `.env.example`。
2. **抓取模块**:先跑通 AI 垂直源 RSS 抓取,本地打印结果。
3. **过滤模块**:实现 `ai_filter.py`,先用 keyword 策略验证过滤效果。
4. **总结模块**:接入 AI API,验证摘要质量。
5. **邮件模块**:本地用测试邮箱跑通 SMTP 发送。
6. **串联主流程**:`main.py` 打通全链路,本地端到端测试。
7. **接入 Actions**:提交 workflow,配置 Secrets,手动触发验证。
8. **开定时**:确认 cron 时间,上线每日自动运行。
9. **迭代优化**:调优关键词 / 引入语义过滤、去重记录、失败重试、归档等。

---

## 八、后续可扩展方向

- 🎯 AI 子领域细分标签(大模型 / AI 芯片 / 自动驾驶 / AIGC...)
- 🧠 过滤策略升级:关键词 → 语义向量 / 大模型判断,提升准确率
- 🔁 失败重试与错误告警(发送失败时通知)
- 🗂 历史归档 + 全文检索
- 📱 多渠道推送(微信/Telegram/飞书 Webhook)
- ⭐ 关键词权重排序,突出重磅 AI 事件

---

*本文档为框架规划,下一步可按「实施步骤」逐个模块落地实现。*