# 用户文档

## 开始使用

Telegram-Joplin 机器人帮助你使用 AI 从 Telegram 消息在 Joplin 中创建有组织的笔记。

### 前提条件

- Telegram 账户
- 已安装并运行 Joplin 笔记应用
- AI 服务的 API 密钥（推荐 DeepSeek）

## 安装

### 自动化设置（推荐）

1. **下载项目**
   ```bash
   git clone <repository-url>
   cd telegram-joplin
   ```

2. **运行设置脚本**
   ```bash
   ./setup.sh
   ```

3. **配置环境**
   - 编辑创建的 `.env` 文件
   - 添加你的 API 密钥和设置

4. **测试安装**
   ```bash
   source activate.sh
   python test_setup.py
   ```

5. **启动机器人**
   ```bash
   python main.py
   ```

### 手动设置

1. 安装 Python 3.9+
2. 安装依赖：`pip install -r requirements.txt`
3. 配置 `.env` 文件
4. 运行测试并启动机器人

## 配置

### 必需设置

创建一个 `.env` 文件，包含：

```env
# Telegram 机器人令牌（从 @BotFather 获取）
TELEGRAM_BOT_TOKEN=your_bot_token_here

# 你的 Telegram 用户 ID（从 @userinfobot 获取）
ALLOWED_TELEGRAM_USER_IDS=123456789

# AI 提供商（选择一个）
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_key

# Joplin（从 Web Clipper 设置获取令牌）
JOPLIN_WEB_CLIPPER_TOKEN=your_joplin_token

# 语言：en（英语）或 zh（中文）
LANGUAGE=en
```

### 可选设置

```env
# 调试日志
DEBUG=true

# 自定义端口
OLLAMA_BASE_URL=http://localhost:11434
JOPLIN_WEB_CLIPPER_PORT=41184
```

## 使用

### 基本工作流程

1. **发送一条消息**给你的机器人，描述你想要记录的内容
2. **AI 处理**你的消息并建议文件夹和标签
3. **自动创建笔记**在 Joplin 中
4. **返回确认**，包含文件夹名称

### 示例消息

```
"关于新网站项目的客户会议笔记"
"巧克力曲奇食谱 - 使用黑巧克力"
"想法：在应用设置中添加深色模式切换"
"书籍推荐：James Clear 的《原子习惯》"
```

### 澄清过程

如果你的消息不清楚，机器人会要求澄清：

```
机器人：我需要更多关于这应该放在哪个文件夹的信息。
这是什么类型的内容？（工作/个人/项目/等）
```

回复额外的详细信息。

### 文件夹组织

机器人自动从你现有的 Joplin 文件夹中选择：

- **00-Inbox**：临时笔记，快速捕获
- **01-Projects**：活跃项目和任务
- **02-Areas**：责任领域
- **03-Resources**：参考资料
- **04-Archive**：已完成项目（避免使用）

### 标签

笔记会根据内容自动标记。常见标签包括：
- AI、project、meeting、recipe、idea、book 等。

## 故障排除

### 机器人没有响应

1. 检查机器人是否正在运行：`python main.py`
2. 验证 Telegram 令牌是否正确
3. 检查用户 ID 是否在允许列表中

### Joplin 连接问题

1. 确保 Joplin 正在运行
2. 在 Joplin 设置中启用 Web Clipper
3. 验证 API 令牌
4. 检查防火墙是否允许端口 41184

### AI 不工作

1. 验证 API 密钥是否正确设置
2. 检查互联网连接
3. 尝试配置中的不同 AI 提供商

### 常见错误

- **"未授权"**：你的 Telegram ID 不在允许列表中
- **"Joplin 无法访问"**：Joplin 未运行或 Web Clipper 已禁用
- **"无效消息"**：消息太短或包含无效字符

## 高级功能

### 自定义文件夹

在 Joplin 中添加你自己的文件夹——机器人会学会使用它们。

### 多个用户

将多个用户 ID 添加到 `ALLOWED_TELEGRAM_USER_IDS`（逗号分隔）。

### 不同的 AI 提供商

在以下之间切换：
- **DeepSeek**：推荐，速度/成本的良好平衡
- **OpenAI**：GPT 模型，需要 API 密钥
- **Ollama**：本地模型，无 API 成本

## 项目同步（Joplin ↔ Google Tasks）

启用后，项目同步将 Joplin 项目文件夹映射到 Google Tasks 中的父任务。你为项目创建的任务在正确的父任务下显示为子任务。有关以下内容，请参阅[项目同步](project-sync.md)：

- 项目同步做什么以及如何启用它
- 文件夹命名和配置
- 命令：`/tasks_toggle_project_sync`、`/tasks_sync_projects`、`/tasks_reset_project_sync`
- 常见问题的[故障排除](project-sync-troubleshooting.md)

## 工作流程指南

有关如何一起使用 Google Tasks 和 Joplin 的完整指南，请参阅[GTD + 第二大脑工作流程](gtd-second-brain-workflow.md)，包括：

- 何时创建任务 vs 笔记
- 完整的项目演练（带有"学习演唱和声"示例）
- 东西放哪儿的决策框架
- 每周回顾过程
- 常见场景的快速参考

## 测试

- **项目同步冒烟测试** — 运行 `./scripts/smoke_project_sync.sh` 进行自动化测试。有关手动生产验证步骤，请参阅[scripts/smoke_project_sync.md](../../scripts/smoke_project_sync.md)。

## 支持

对于问题：
1. 检查控制台输出中的日志
2. 验证配置
3. 使用 `python test_setup.py` 进行测试
4. 检查 GitHub 问题以了解已知问题

## 安全

- 只有授权的 Telegram 用户可以使用机器人
- 消息被安全处理
- API 密钥存储在本地 `.env` 文件中
- 没有用户数据发送到外部服务

---

---

# User Documentation

## Getting Started

The Telegram-Joplin bot helps you create organized notes in Joplin from your Telegram messages using AI.

### Prerequisites

- Telegram account
- Joplin note-taking app installed and running
- API keys for AI service (DeepSeek recommended)

## Installation

### Automated Setup (Recommended)

1. **Download the project**
   ```bash
   git clone <repository-url>
   cd telegram-joplin
   ```

2. **Run setup script**
   ```bash
   ./setup.sh
   ```

3. **Configure environment**
   - Edit the created `.env` file
   - Add your API keys and settings

4. **Test installation**
   ```bash
   source activate.sh
   python test_setup.py
   ```

5. **Start the bot**
   ```bash
   python main.py
   ```

### Manual Setup

1. Install Python 3.9+
2. Install dependencies: `pip install -r requirements.txt`
3. Configure `.env` file
4. Run tests and start bot

## Configuration

### Required Settings

Create a `.env` file with:

```env
# Telegram Bot Token (get from @BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Your Telegram User ID (get from @userinfobot)
ALLOWED_TELEGRAM_USER_IDS=123456789

# AI Provider (choose one)
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_key

# Joplin (get token from Web Clipper settings)
JOPLIN_WEB_CLIPPER_TOKEN=your_joplin_token
```

### Optional Settings

```env
# Debug logging
DEBUG=true

# Custom ports
OLLAMA_BASE_URL=http://localhost:11434
JOPLIN_WEB_CLIPPER_PORT=41184
```

## Usage

### Basic Workflow

1. **Send a message** to your bot describing what you want to note
2. **AI processes** your message and suggests folder and tags
3. **Note created** automatically in Joplin
4. **Confirmation** sent back with folder name

### Example Messages

```
"Meeting notes from client call about new website project"
"Recipe for chocolate chip cookies - use dark chocolate"
"Idea: Add dark mode toggle to the app settings"
"Book recommendation: 'Atomic Habits' by James Clear"
```

### Clarification Process

If your message is unclear, the bot will ask for clarification:

```
Bot: I need more information about what folder this should go in.
What type of content is this? (work/personal/project/etc.)
```

Reply with additional details.

### Folder Organization

The bot automatically chooses from your existing Joplin folders:

- **00-Inbox**: Temporary notes, quick captures
- **01-Projects**: Active projects and tasks
- **02-Areas**: Areas of responsibility
- **03-Resources**: Reference materials
- **04-Archive**: Completed items (avoided)

### Tagging

Notes are automatically tagged based on content. Common tags include:
- AI, project, meeting, recipe, idea, book, etc.

## Troubleshooting

### Bot Not Responding

1. Check if bot is running: `python main.py`
2. Verify Telegram token is correct
3. Check user ID is in allowed list

### Joplin Connection Issues

1. Ensure Joplin is running
2. Enable Web Clipper in Joplin settings
3. Verify API token
4. Check firewall allows port 41184

### AI Not Working

1. Verify API key is set correctly
2. Check internet connection
3. Try different AI provider in config

### Common Errors

- **"Not authorized"**: Your Telegram ID not in allowed list
- **"Joplin not accessible"**: Joplin not running or Web Clipper disabled
- **"Invalid message"**: Message too short or contains invalid characters

## Advanced Features

### Custom Folders

Add your own folders in Joplin - the bot will learn to use them.

### Multiple Users

Add multiple user IDs to `ALLOWED_TELEGRAM_USER_IDS` (comma-separated).

### Different AI Providers

Switch between:
- **DeepSeek**: Recommended, good balance of speed/cost
- **OpenAI**: GPT models, requires API key
- **Ollama**: Local models, no API costs

## Project Sync (Joplin ↔ Google Tasks)

When enabled, project sync maps Joplin project folders to parent tasks in Google Tasks. Tasks you create for a project appear as subtasks under the correct parent. See [Project Sync](project-sync.md) for:

- What project sync does and how to enable it
- Folder naming and configuration
- Commands: `/tasks_toggle_project_sync`, `/tasks_sync_projects`, `/tasks_reset_project_sync`
- [Troubleshooting](project-sync-troubleshooting.md) for common issues

## Workflow Guide

See [GTD + Second Brain Workflow](gtd-second-brain-workflow.md) for a complete guide on using Google Tasks and Joplin together, including:

- When to create a task vs a note
- Full project walkthroughs (with the "Learn to Sing Harmonies" example)
- Decision framework for where things go
- Weekly review process
- Quick reference for common scenarios

## Testing

- **Project sync smoke test** — Run `./scripts/smoke_project_sync.sh` for automated tests. See [scripts/smoke_project_sync.md](../../scripts/smoke_project_sync.md) for manual production verification steps.

## Support

For issues:
1. Check logs in console output
2. Verify configuration
3. Test with `python test_setup.py`
4. Check GitHub issues for known problems

## Security

- Only authorized Telegram users can use the bot
- Messages are processed securely
- API keys stored locally in `.env` file
- No user data sent to external services
