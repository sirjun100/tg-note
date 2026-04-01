# 智能 Joplin 图书管理员

[![CI](https://github.com/martinfou/telegram-joplin/actions/workflows/ci.yml/badge.svg)](https://github.com/martinfou/telegram-joplin/actions/workflows/ci.yml) [🔄 强制部署](https://github.com/martinfou/telegram-joplin/actions/workflows/ci.yml)

**别再把所有事情都记在脑子里了。** 这个 Telegram 机器人将有史以来最强大的两个生产力系统——**GTD（搞定事情）**和**第二大脑（PARA）**——结合成一个单一、流畅的界面，就是你每天都在使用的手机。

发送一条消息，AI 会处理剩下的事情。

<p align="center">
  <img src="docs/images/gtd-second-brain-workflow.png" alt="GTD + 第二大脑：统一的生产力工作流程" width="600">
</p>

---

## 问题所在

你脑子里有想法，便利贴上有任务，文章收藏了又忘记，会议笔记分散在各个应用中，隐约觉得自己忘了什么重要的事情。

**你没有记忆问题。你有系统问题。**

你的大脑是用来**产生**想法的，不是用来**储存**想法的。但大多数工具都强迫你做决定：*这该放哪儿？什么文件夹？什么标签？这是任务还是笔记？* 所以你最终把所有东西都堆在一个地方——或者更糟，哪里都不放。

## 解决方案：GTD + 第二大脑，自动处理

这个机器人将两种经过验证的方法结合在一起，让 AI 来处理组织工作：

| 系统 | 作用 | 工具 | 回答的问题 |
|--------|-------------|------|------------------------|
| **GTD**（搞定事情） | 管理你的*行动* | Google Tasks | "接下来我该做什么？" |
| **第二大脑**（PARA） | 管理你的*知识* | Joplin | "关于这个我知道什么？" |

**GTD** 让你保持前进——每个项目都有具体的下一步行动，没有事情会漏掉。

**第二大脑** 让你保持思考——每个想法、参考资料和见解都被捕获、组织，并在你需要时可以找到。

在一起，它们意味着你永远不会失去一个想法*并且*你总是知道接下来该做什么。

---

## 它是如何工作的

打开 Telegram。发送一条消息。就是这样。

**你说：** *"和 Sarah 开会——她想把发布日期改到 3 月 15 日，我需要更新时间线并告诉设计团队"*

**机器人创建：**
- 在 Projects 文件夹中的一个 **Joplin 笔记**，包含会议细节、关键决策和上下文
- 一个 **Google 任务**："将发布时间线更新到 3 月 15 日"
- 一个 **Google 任务**："告诉设计团队新的发布日期"

标签自动应用。由 AI 选择文件夹。提取行动项目并准备勾选。

### 更多示例

| 你发送 | 发生什么 |
|----------|-------------|
| *"我需要在 6 月前更新护照"* | 创建带有截止日期的 Google 任务 |
| *一篇有趣文章的 URL* | 带有摘要、要点和标签的 Joplin 笔记 |
| *"食谱：Mike 的烧烤调料——2 汤匙辣椒粉，1 汤匙红糖..."* | Resources/🍽️ Recipe 中的食谱笔记，带有食谱标签 |
| *"想法：如果这个应用程序也能追踪习惯呢"* | 捕获在收件箱中以便后续处理 |
| `/braindump` | 引导式 15 分钟 GTD 头脑清空，将你的大脑清空到有组织的笔记和任务中 |
| `/task 周日给妈妈打电话` | 单个 Google 任务——不需要笔记 |

---

## CODE 工作流程：从信息到知识

机器人遵循《建立第二大脑》中的 **CODE** 方法：

### 捕获

向机器人发送任何内容——想法、URL、会议笔记、食谱、想法、书籍亮点。不用担心它去哪里。只要捕获它。

### 组织

AI 使用 **PARA** 方法自动归档你的笔记：

- **项目** — 有截止日期的目标（发布网站、学吉他、计划假期）
- **领域** — 持续的责任（健康、财务、职业、家庭）
- **资源** — 参考资料（读书笔记、食谱、操作指南、速查表）
- **归档** — 已完成或不活跃的项目

无需手动归档。无需决策疲劳。AI 读取你的笔记并把它放在应该去的地方。

### 提炼

`/reorg_enrich` 命令为你的笔记添加 AI 生成的元数据——摘要、关键要点、优先级级别和建议的标签。未来的你能更快找到东西。

### 表达

你有组织的知识转化为行动。`/report_daily` 将来自 Joplin 和 Google Tasks 的最高优先级项目聚合到一个早晨简报中。你总是知道今天什么重要。

---

## 你能做什么

### 当你不堪重负时进行头脑清空

运行 `/braindump`，机器人就会变成一个 GTD 教练。它会问有针对性的问题，把你脑子里的每一个未结事项都拉出来——那个烦人的差事，你一直拖延的电子邮件，你在淋浴时的想法。

最后，你会在 Joplin 中得到一个干净的摘要笔记，在 Google Tasks 中得到具体的任务。你的脑子空了。你的系统拥有一切。

### 永远不会再失去参考资料

粘贴一个 URL，机器人会获取文章，提取关键内容，检测是否是食谱，生成摘要，并使用智能标签将其归档到正确的文件夹中。几个月后，你真的会找到它。

### 10 秒内获得晨间优先级

每日报告将你的高优先级 Joplin 笔记、即将到来的 Google Tasks 和待处理项目汇集到一条消息中。无需在应用间切换。无需担心你忘记了什么。

### 斯多葛日记

`/stoic morning` 引导你进行意图设定。`/stoic evening` 引导你进行反思。机器人将你的日记条目保存为结构化笔记——建立一个没有摩擦的练习。

### 重新组织你的整个知识库

Joplin 中已经有数百个笔记了？`/reorg_init` 命令创建一个 PARA 文件夹结构，AI 会将你现有的笔记分类并迁移到其中。多年积累的笔记，几分钟内组织好。

---

## 为什么这种组合有效

大多数生产力工具只解决*一个*问题。待办事项应用不会帮助你记住你学到了什么。笔记应用不会告诉你接下来该做什么。你最终在应用间切换、重复信息并失去上下文。

这个机器人不同：

- **一个输入** — Telegram 消息，你已经在使用的同一个应用
- **两个系统** — GTD 用于行动，第二大脑用于知识
- **零组织** — AI 处理文件夹、标签和任务提取
- **始终可用** — 你的手机总是随身携带；在当下捕获

结果：**你对系统的思考更少，对生活的思考更多。**

---

## 开始使用

### 你需要什么

- 一个 Telegram 账户
- [Joplin](https://joplinapp.org/)（免费、开源的笔记应用）
- 一个 AI 提供商 API 密钥（推荐 DeepSeek——快速且实惠）
- 可选：用于 Google Tasks 集成的 Google 账户

### 快速设置

```bash
git clone <repository-url>
cd telegram-joplin
cp .env.example .env    # 添加你的 API 密钥
./setup.sh              # 创建 venv，安装依赖
python main.py          # 机器人启动
```

或者使用 Docker：

```bash
cp .env.example .env    # 添加你的 API 密钥
docker-compose up -d
```

### 云部署（Fly.io）

机器人在 Fly.io 上运行，**空闲时零成本**——机器在消息之间休眠，当你给机器人发短信时会在约 10 秒内唤醒。有关详细信息，请参阅[部署指南](docs/for-users/README.md)。

### Google Tasks（可选）

启用 Google Tasks 集成以获得自动任务提取：

1. 创建一个启用了 Tasks API 的 Google Cloud 项目
2. 将 OAuth 凭据添加到你的 `.env`
3. 在机器人中运行 `/authorize_google_tasks`

**项目同步**（可选）：将 Joplin 项目文件夹映射到 Google Tasks 中的父任务。为项目创建的任务在父任务下显示为子任务。使用 `/tasks_toggle_project_sync` 启用；有关详细信息，请参阅[项目同步](docs/for-users/project-sync.md)。

---

## 文档

| 受众 | 指南 |
|----------|-------|
| **用户** | [用户指南](docs/for-users/README.md) — 设置、配置、日常使用、[项目同步](docs/for-users/project-sync.md) |
| **GTD + 第二大脑** | [完整工作流程指南](docs/for-users/gtd-second-brain-workflow.md) — 何时创建任务与笔记、项目演练、每周回顾 |
| **PARA 决策** | [东西放哪儿](docs/para-where-to-put.md) — 项目 vs 领域 vs 资源 vs 归档 |
| **开发者** | [开发者指南](docs/for-developers/README.md) — 架构、代码库、贡献 |
| **业务分析师** | [BA 指南](docs/for-business-analyst/README.md) — 功能、路线图、需求 |

---

## 使用技术构建

- **Telegram Bot API** 通过 [python-telegram-bot](https://python-telegram-bot.org/)
- **Joplin** 通过 Web Clipper API — 你的笔记保持本地和私密
- **Google Tasks API** — OAuth 2.0 集成
- **AI/LLM** — OpenAI、DeepSeek 或 Ollama（本地，无需云）
- **Fly.io** — 零成本无服务器部署

---

*"你的头脑是用来产生想法的，不是用来储存它们的。"* — David Allen，《搞定事情》

---

---

# Intelligent Joplin Librarian

[![CI](https://github.com/martinfou/telegram-joplin/actions/workflows/ci.yml/badge.svg)](https://github.com/martinfou/telegram-joplin/actions/workflows/ci.yml) [🔄 Force Deploy](https://github.com/martinfou/telegram-joplin/actions/workflows/ci.yml)

**Stop carrying everything in your head.** This Telegram bot combines two of the most powerful productivity systems ever created — **Getting Things Done (GTD)** and the **Second Brain (PARA)** — into a single, frictionless interface you already use every day: your phone.

Send a message. The AI figures out the rest.

<p align="center">
  <img src="docs/images/gtd-second-brain-workflow.png" alt="GTD + Second Brain: The Unified Productivity Workflow" width="600">
</p>

---

## The Problem

You have ideas in your head, tasks on sticky notes, articles bookmarked and forgotten, meeting notes scattered across apps, and a vague sense that you're forgetting something important.

**You don't have a memory problem. You have a system problem.**

Your brain is for *having* ideas, not *holding* them. But most tools force you to decide: *Where does this go? What folder? What tag? Is this a task or a note?* So you end up dumping everything in one place — or worse, nowhere at all.

## The Solution: GTD + Second Brain, on Autopilot

This bot brings together two proven methodologies and lets AI handle the organizing:

| System | What it does | Tool | The question it answers |
|--------|-------------|------|------------------------|
| **GTD** (Getting Things Done) | Manages your *actions* | Google Tasks | "What should I do next?" |
| **Second Brain** (PARA) | Manages your *knowledge* | Joplin | "What do I know about this?" |

**GTD** keeps you moving — every project has a concrete next action, nothing falls through the cracks.

**Second Brain** keeps you thinking — every idea, reference, and insight is captured, organized, and findable when you need it.

Together, they mean you never lose a thought *and* you always know what to do next.

---

## How It Works

Open Telegram. Send a message. That's it.

**You say:** *"Meeting with Sarah — she wants to move the launch to March 15, I need to update the timeline and tell the design team"*

**The bot creates:**
- A **Joplin note** in your Projects folder with the meeting details, key decisions, and context
- A **Google Task**: "Update launch timeline to March 15"
- A **Google Task**: "Tell design team about new launch date"

Tags applied automatically. Folder chosen by AI. Action items extracted and ready to check off.

### More examples

| You send | What happens |
|----------|-------------|
| *"I need to renew my passport before June"* | Google Task created with deadline |
| *A URL to an interesting article* | Joplin note with summary, key points, and tags |
| *"Recipe: Mike's BBQ rub — 2 tbsp paprika, 1 tbsp brown sugar..."* | Note in Resources/🍽️ Recipe with recipe tag |
| *"Idea: what if the app could track habits too"* | Note captured in Inbox for later processing |
| `/braindump` | Guided 15-minute GTD mind-sweep that empties your brain into organized notes and tasks |
| `/task Call mom about Sunday dinner` | Single Google Task — no note needed |

---

## The CODE Workflow: From Information to Knowledge

The bot follows the **CODE** method from Building a Second Brain:

### Capture

Send anything to the bot — thoughts, URLs, meeting notes, recipes, ideas, book highlights. Don't worry about where it goes. Just capture it.

### Organize

AI automatically files your notes using the **PARA** method:

- **Projects** — Goals with deadlines (Launch website, Learn guitar, Plan vacation)
- **Areas** — Ongoing responsibilities (Health, Finance, Career, Family)
- **Resources** — Reference material (Book notes, recipes, how-tos, cheat sheets)
- **Archive** — Completed or inactive items

No manual filing. No decision fatigue. The AI reads your note and puts it where it belongs.

### Distill

The `/reorg_enrich` command adds AI-generated metadata to your notes — summaries, key takeaways, priority levels, and suggested tags. Your future self finds things faster.

### Express

Your organized knowledge feeds into action. The `/report_daily` aggregates your highest-priority items from both Joplin and Google Tasks into a single morning briefing. You always know what matters today.

---

## What You Can Do

### Brain Dump When You're Overwhelmed

Run `/braindump` and the bot becomes a GTD coach. It asks targeted questions to pull every open loop out of your head — that nagging errand, the email you keep putting off, the idea you had in the shower.

At the end, you get a clean summary note in Joplin and concrete tasks in Google Tasks. Your head is empty. Your system has everything.

### Never Lose a Reference Again

Paste a URL and the bot fetches the article, extracts the key content, detects if it's a recipe, generates a summary, and files it in the right folder with smart tags. Months later, you'll actually find it.

### Morning Priorities in 10 Seconds

The daily report pulls together your high-priority Joplin notes, upcoming Google Tasks, and pending items into one message. No app-hopping. No wondering what you forgot.

### Stoic Journaling

`/stoic morning` guides you through intention-setting. `/stoic evening` walks you through reflection. The bot saves your journal entries as structured notes — building a practice without friction.

### Reorganize Your Entire Knowledge Base

Already have hundreds of notes in Joplin? The `/reorg_init` command creates a PARA folder structure, and the AI classifies and migrates your existing notes into it. Years of accumulated notes, organized in minutes.

---

## Why This Combination Works

Most productivity tools solve *one* problem. A to-do app doesn't help you remember what you learned. A note-taking app doesn't tell you what to do next. You end up switching between apps, duplicating information, and losing context.

This bot is different:

- **One input** — Telegram messages, the same app you already use
- **Two systems** — GTD for actions, Second Brain for knowledge
- **Zero organizing** — AI handles folders, tags, and task extraction
- **Always available** — your phone is always with you; capture happens in the moment

The result: **you think less about your system and more about your life.**

---

## Getting Started

### What You Need

- A Telegram account
- [Joplin](https://joplinapp.org/) (free, open-source note-taking app)
- An AI provider API key (DeepSeek recommended — fast and affordable)
- Optionally: a Google account for Google Tasks integration

### Quick Setup

```bash
git clone <repository-url>
cd telegram-joplin
cp .env.example .env    # add your API keys
./setup.sh              # creates venv, installs dependencies
python main.py          # bot is live
```

Or with Docker:

```bash
cp .env.example .env    # add your API keys
docker-compose up -d
```

### Cloud Deployment (Fly.io)

The bot runs on Fly.io with **zero cost when idle** — the machine sleeps between messages and wakes in ~10 seconds when you text the bot. See [deployment guide](docs/for-users/README.md) for details.

### Google Tasks (Optional)

Enable Google Tasks integration to get automatic task extraction:

1. Create a Google Cloud project with the Tasks API enabled
2. Add OAuth credentials to your `.env`
3. Run `/authorize_google_tasks` in the bot

**Project sync** (optional): Map Joplin project folders to parent tasks in Google Tasks. Tasks created for a project appear as subtasks under the parent. Enable with `/tasks_toggle_project_sync`; see [Project Sync](docs/for-users/project-sync.md) for details.

---

## Documentation

| Audience | Guide |
|----------|-------|
| **Users** | [User Guide](docs/for-users/README.md) — setup, configuration, daily usage, [project sync](docs/for-users/project-sync.md) |
| **GTD + Second Brain** | [Complete Workflow Guide](docs/for-users/gtd-second-brain-workflow.md) — when to create a task vs a note, project walkthroughs, weekly reviews |
| **PARA Decisions** | [Where Things Go](docs/para-where-to-put.md) — Projects vs Areas vs Resources vs Archive |
| **Developers** | [Developer Guide](docs/for-developers/README.md) — architecture, codebase, contributing |
| **Business Analysts** | [BA Guide](docs/for-business-analyst/README.md) — features, roadmap, requirements |

---

## Built With

- **Telegram Bot API** via [python-telegram-bot](https://python-telegram-bot.org/)
- **Joplin** via Web Clipper API — your notes stay local and private
- **Google Tasks API** — OAuth 2.0 integration
- **AI/LLM** — OpenAI, DeepSeek, or Ollama (local, no cloud needed)
- **Fly.io** — zero-cost serverless deployment

---

*"Your mind is for having ideas, not holding them."* — David Allen, Getting Things Done
