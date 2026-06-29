# Contributing to FeedMind / 参与贡献

[English](#english) | [中文](#chinese)

---

<a name="english"></a>
## English

First off, thank you for considering contributing to FeedMind! It's people like you that make open-source software such a great community.

### Local Development Environment

1. **Fork and Clone**
   Fork the repository to your own GitHub account and clone it to your local machine:
   ```bash
   git clone https://github.com/YOUR_USERNAME/news-rss.git
   cd news-rss
   ```

2. **Set up Python Environment**
   We recommend using a virtual environment (e.g., `venv` or `conda`) to manage dependencies.
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Environment Variables**
   FeedMind requires a Gemini API key. Copy the example environment file and set your key:
   ```bash
   cp .env.example .env
   # Edit .env and replace with your actual API key:
   # GEMINI_API_KEY="your-api-key"
   ```

### Running and Debugging

To run the pipeline locally without calling the LLM or saving to the database (which saves tokens and prevents polluting your database), use the `--dry-run` flag:

```bash
python main.py --dry-run
```

To run a full test generation locally:
```bash
python main.py
```
This will fetch feeds, call the Gemini API, update `rss_memory.db`, and place the generated XML files into the `output_feeds/` directory.

### Running Tests

We use `pytest` for automated unit testing. Before submitting a Pull Request, ensure your changes don't break existing functionality and pass code linting by running:

```bash
pytest
ruff check .
```
*(Note: Some tests might require the `.env` file to be properly configured).*

### Submitting a Pull Request

1. Create a new branch for your feature or bug fix: `git checkout -b feature-name`
2. Commit your changes with clear, descriptive commit messages.
3. Push to your fork: `git push origin feature-name`
4. Open a Pull Request against the `main` branch of this repository.

---

<a name="chinese"></a>
## 中文

首先，感谢你考虑为 FeedMind 做出贡献！正是有了你们，开源社区才会如此繁荣。

### 本地开发环境配置

1. **Fork 并克隆（Clone）**
   将本仓库 Fork 到你自己的 GitHub 账号下，然后克隆到本地机器：
   ```bash
   git clone https://github.com/YOUR_USERNAME/news-rss.git
   cd news-rss
   ```

2. **配置 Python 环境**
   推荐使用虚拟环境（如 `venv` 或 `conda`）来隔离依赖。
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows 用户请运行: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **环境变量**
   FeedMind 需要调用 Gemini API。请复制配置模板并填入你的 API Key：
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入你真实的 API 密钥：
   # GEMINI_API_KEY="your-api-key"
   ```

### 本地运行与调试

在本地开发时，如果你不想实际调用大模型（节省 Token）并且不想修改本地数据库，推荐使用 `--dry-run` 模式进行测试：

```bash
python main.py --dry-run
```

进行完整运行：
```bash
python main.py
```
这将会抓取 RSS、调用 Gemini 总结、更新本地 `rss_memory.db`，并将生成的 XML 订阅文件输出到 `output_feeds/` 目录下。

### 运行测试

我们使用 `pytest` 进行自动化单元测试。在提交 PR 之前，请运行测试与代码静态检查，以确保没有破坏现有功能：

```bash
pytest
ruff check .
```
*（注意：部分测试依赖于正确配置的 `.env` 文件）。*

### 提交 Pull Request (PR)

1. 为你的功能或修复创建一个新分支：`git checkout -b feature-name`
2. 提交代码，保持 commit 信息清晰易懂。
3. 推送到你的 Fork 仓库：`git push origin feature-name`
4. 向本仓库的 `main` 分支提交 Pull Request。
