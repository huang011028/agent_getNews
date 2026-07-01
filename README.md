# 每日 AI 新闻速报 Agent

用 GitHub Actions 定时执行：**抓取新闻 → 筛选 AI 相关 → AI 总结 → 邮件推送**。

> 只关注人工智能 / 大模型 / 机器学习领域，其余主题自动过滤。

## 目录结构

```
agent_getNews/
├── .github/workflows/daily_news.yml  # 定时任务
├── src/
│   ├── config.py       # 配置加载
│   ├── fetch_news.py   # 抓取 RSS
│   ├── ai_filter.py    # AI 相关性过滤
│   ├── summarize.py    # AI 总结
│   ├── render.py       # 邮件渲染
│   └── send_email.py   # SMTP 发送
├── config/
│   ├── sources.yaml    # 新闻源
│   └── keywords.yaml   # AI 关键词 / 过滤策略
├── archive/            # 每日归档
├── main.py             # 主入口
└── requirements.txt
```

## 本地运行

```bash
pip install -r requirements.txt
cp .env.example .env      # 填入你的 API Key 与 SMTP 配置
python main.py
```

### 分模块调试

```bash
python -m src.fetch_news   # 只看抓取结果
python -m src.ai_filter    # 看过滤后结果
python -m src.summarize    # 看总结结果
python -m src.send_email   # 发一封测试邮件
```

## 部署到 GitHub Actions

1. 推送代码到 GitHub 仓库。
2. 在 **Settings → Secrets and variables → Actions** 添加以下 Secrets：

   | 名称 | 说明 |
   | --- | --- |
   | `OPENAI_API_KEY` | DeepSeek API Key（platform.deepseek.com 申请） |
   | `OPENAI_BASE_URL` | DeepSeek 地址 `https://api.deepseek.com` |
   | `OPENAI_MODEL` | 模型名 `deepseek-v4-pro` |
   | `SMTP_HOST` | 邮件服务器，如 `smtp.qq.com` |
   | `SMTP_PORT` | 端口，SSL 用 `465` |
   | `SMTP_USER` | 发件邮箱 |
   | `SMTP_PASS` | 邮箱授权码（非登录密码） |
   | `MAIL_FROM_NAME` | 可选，发件人显示名 |
   | `MAIL_TO` | 收件人，多个用逗号分隔 |

3. 到 **Actions** 页手动触发（Run workflow）验证。
4. 验证通过后，`cron` 会每天北京时间 07:00 自动运行。

> ⚠️ cron 用 UTC 时间，`0 23 * * *` = 北京时间次日 07:00。

## 邮件格式

```
📮 今日 AI 圈核心动态已打包，快报速览

1. 美团发布 LongCat-2.0 万亿参数大模型
2. DeepSeek V4 高峰时段 API 价格翻倍
...

—— 完整链接 ——
[1] https://...
[2] https://...
```

## 自定义

- 改新闻源：编辑 `config/sources.yaml`。
- 改关键词 / 过滤策略：编辑 `config/keywords.yaml`（`keyword` / `semantic` / `hybrid`）。
- 改推送时间：编辑 workflow 里的 `cron`。