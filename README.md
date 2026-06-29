<div align="center">
  <img src="assets/logo.jpg" alt="FeedMind Logo" width="200"/>
  <h1>FeedMind</h1>
  <p>An intelligent, AI-powered RSS aggregator and summarizer.</p>
  <p>
    <a href="https://github.com/howerhe/feedmind/actions/workflows/feedmind.yml"><img src="https://img.shields.io/github/actions/workflow/status/howerhe/feedmind/feedmind.yml?branch=main" alt="Build Status"></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python Version"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  </p>
</div>

[English](#english) | [中文](#chinese)

---

<a name="english"></a>
## English

### Overview

FeedMind is a Python-based RSS pipeline that automatically fetches your favorite feeds, deduplicates stories, and uses Google's Gemini AI to generate engaging, concise summaries. It then outputs the results as standard RSS XML feeds, allowing you to read AI-curated news in your favorite RSS reader.

### Features

- **AI Summarization:** Condense lengthy articles or forum threads into 300-word (configurable) highlights.
- **Smart Deduplication:** Groups identical or follow-up news items across multiple sources into a single event.
- **Discourse Forum Support:** Specifically tuned to scrape Discourse forums by fetching complete thread JSONs to summarize OP + replies.
- **Highly Configurable:** Toggle aggregation, summarization, and custom prompts on a per-topic basis using `config.yaml`.
- **System Alerts:** If a feed source goes down or times out, FeedMind automatically injects an error report directly into your RSS feed.

### GitHub Actions Automation (Zero-Cost Hosting)

You can run FeedMind completely for free using GitHub Actions and GitHub Pages!
This repository includes a `.github/workflows/feedmind.yml` workflow which automatically:
1. Runs the script twice a day.
2. Calls the Gemini API to generate summaries.
3. Deploys the generated XML files to GitHub Pages.

**To use this:**
1. Fork this repository.
2. Go to **Settings > Secrets and variables > Actions** in your fork and add a repository secret named `GEMINI_API_KEY`. You can also add `GEMINI_MODEL` as an environment variable to override the default model.
3. Enable GitHub Pages in your repo settings (deploying from GitHub Actions).
4. Enjoy your automated, free AI RSS feed!

### Local Development & Setup

If you want to run or develop FeedMind locally:

1. **Clone & Install Dependencies:**
   ```bash
   git clone https://github.com/howerhe/feedmind.git
   cd feedmind
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY and GEMINI_MODEL (optional)
   ```
3. **Run the Pipeline:**
   ```bash
   python main.py
   ```
   *Note: Use `python main.py --dry-run` to preview the pipeline (skips LLM calls and DB saves).*

For more details on contributing or running tests, please see [CONTRIBUTING.md](CONTRIBUTING.md).

### Configuration

Edit `config.yaml` to define your topics and rules. You can override metadata (title, link, description) or tweak the LLM instructions (`prompt`) for each feed.

```yaml
topics:
  - name: "China News"
    title: "中国新闻"
    description: "中外媒体中国新闻每日精华"
    aggregate: true
    summarize: true
    feeds:
      - "https://rsshub.app/zaobao/realtime/china"
      - "https://plink.anyfeeder.com/nytimes/cn"
      - "https://plink.anyfeeder.com/bbc/cn"
```

### License

This project is licensed under the [MIT License](LICENSE).

---

<a name="chinese"></a>
## 中文

### 概览

FeedMind 是一个基于 Python 的 RSS 处理流水线，它会自动抓取你关注的 RSS 源，去重相关新闻，并使用 Google 的 Gemini 模型生成生动、简洁的摘要。最终，它将处理结果输出为标准的 RSS XML 文件，让你可以在任何喜欢的 RSS 阅读器中阅读由 AI 精选的新闻。

### 核心特性

- **AI 智能总结：** 将长篇文章或长篇论坛帖子压缩提炼为 300 字（可配置）的精华摘要。
- **智能去重：** 跨信源识别并聚合相同或后续跟进的新闻事件。
- **Discourse 论坛支持：** 专门优化抓取 Discourse 论坛（通过提取完整帖子的 JSON 数据，合并总结主贴与高赞回复）。
- **高度可配置：** 可通过 `config.yaml` 为每个主题单独切换是否聚合、是否总结，并支持自定义 Prompt。
- **系统告警机制：** 如果某个 RSS 源宕机或超时，FeedMind 会自动在你的最终 RSS 订阅中注入一条报错信息，方便你及时发现。

### GitHub Actions 自动化部署（零成本托管）

你可以借助 GitHub Actions 和 GitHub Pages 完全免费地运行 FeedMind！
本项目内置了 `.github/workflows/feedmind.yml` 工作流，它会自动：
1. 每天定时运行两次抓取脚本。
2. 调用 Gemini API 生成摘要。
3. 将生成的 XML 订阅文件自动部署到 GitHub Pages。

**使用方法：**
1. Fork 本仓库。
2. 在你 Fork 的仓库中进入 **Settings > Secrets and variables > Actions**，添加一个名为 `GEMINI_API_KEY` 的 Repository Secret。你也可以按需添加 `GEMINI_MODEL` 环境变量来指定模型。
3. 在仓库设置中开启 GitHub Pages 功能（选择从 GitHub Actions 部署）。
4. 享受你专属的、免费的全自动 AI RSS 订阅流！

### 本地开发与环境搭建

如果你希望在本地运行或开发 FeedMind：

1. **克隆代码并安装依赖：**
   ```bash
   git clone https://github.com/howerhe/feedmind.git
   cd feedmind
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **配置环境变量：**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件并添加你的 GEMINI_API_KEY 和 GEMINI_MODEL（可选）
   ```
3. **运行流水线：**
   ```bash
   python main.py
   ```
   *注意：使用 `python main.py --dry-run` 可以在不消耗大模型 Token 和不写入数据库的情况下预览处理结果。*

有关代码贡献或运行测试的更多详细信息，请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

### 配置说明

你可以编辑 `config.yaml` 文件来定义你的主题（topics）和规则。你还可以为每个 feed 覆盖元数据（如标题、链接、描述）或微调大模型的指令（`prompt`）。

```yaml
topics:
  - name: "China News"
    title: "中国新闻"
    description: "中外媒体中国新闻每日精华"
    aggregate: true
    summarize: true
    feeds:
      - "https://rsshub.app/zaobao/realtime/china"
      - "https://plink.anyfeeder.com/nytimes/cn"
      - "https://plink.anyfeeder.com/bbc/cn"
```

### 开源协议

本项目采用 [MIT License](LICENSE) 协议进行开源。
