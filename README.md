# 🚀 AI-Powered LinkedIn Content Generation System

An autonomous multi-agent AI system built with **CrewAI** that researches the latest AI & Data Science trends, analyzes technical developments, generates professional LinkedIn content, refines it into a natural human voice, and automatically delivers the final publication-ready content to Slack.

The goal is to help experienced AI Engineers and Data Scientists consistently publish high-quality LinkedIn content without spending hours researching and writing.

---

## ✨ Features

- 🔍 Researches the latest AI, Data Science, LLM, RAG, Agentic AI, MLOps, and GenAI topics
- 🌐 Searches only credible sources using Serper
- 📖 Extracts and summarizes technical articles
- 🧠 Performs technical analysis of industry developments
- ✍️ Generates multiple LinkedIn post variations
- 🎯 Rewrites content into a natural, experienced practitioner voice
- ✅ Removes AI-generated sounding text and repetitive phrasing
- 📚 Includes source references
- 💬 Generates a first comment to boost engagement
- 🖼️ Suggests infographic/carousel ideas
- 📤 Automatically sends the final content package to Slack

---

# 🏗️ Architecture

```
                    User Topic
                         │
                         ▼
            AI Trend Researcher
                         │
                         ▼
      Technical Content Strategist
                         │
                         ▼
        LinkedIn Content Creator
                         │
                         ▼
        Personal Brand Editor
                         │
                         ▼
          Slack Publisher
                         │
                         ▼
                 Slack Channel
```

---

# 🤖 AI Agents

## 1. AI Trend Researcher

Responsible for researching the latest developments.

Responsibilities

- Search trusted sources
- Read technical articles
- Gather supporting evidence
- Ignore broken or inaccessible URLs
- Avoid hallucinated information

Output

- AI research report
- Source URLs
- Key insights

---

## 2. Technical Content Strategist

Transforms research into technical insights.

Responsibilities

- Analyze patterns
- Explain technical significance
- Identify trends
- Produce practitioner-level insights

Output

- Technical analysis
- Key takeaways
- Content angles

---

## 3. LinkedIn Content Creator

Creates engaging professional content.

Responsibilities

- Convert research into posts
- Produce multiple writing styles
- Keep content educational
- Avoid generic AI marketing language

Output

- Educational post
- Opinion post
- Practitioner insight post

---

## 4. Personal Brand Editor

Final editorial review.

Responsibilities

- Fact checking
- Remove repetition
- Improve readability
- Humanize writing
- Improve hooks
- Improve flow
- Preserve technical accuracy

Output

Publication-ready LinkedIn content.

---

## 5. Slack Publisher

Delivers the final output.

Responsibilities

- Receive final content
- Send to Slack
- No rewriting
- No summarization

Output

Slack notification confirming successful delivery.

---

# 🧩 Workflow

```
Research Topic
      │
      ▼
Search Internet
      │
      ▼
Read Articles
      │
      ▼
Technical Analysis
      │
      ▼
Create LinkedIn Posts
      │
      ▼
Editorial Review
      │
      ▼
Publish to Slack
```

---

# 🛠 Tech Stack

- Python 3.12+
- CrewAI
- OpenAI GPT-4o
- Serper API
- ScrapeWebsiteTool
- Slack Incoming Webhooks
- dotenv

---

# 📂 Project Structure

```
content_creation/

│
├── agents/
│   ├── ai_trend_researcher.jsonc
│   ├── technical_content_strategist.jsonc
│   ├── linkedin_content_creator.jsonc
│   ├── personal_brand_editor.jsonc
│   └── slack_publisher.jsonc
│
├── tools/
│   └── send_to_slack.py
│
├── crew.jsonc
├── .env
├── pyproject.toml
└── README.md
```

---

# ⚙️ Installation

Clone the repository

```bash
git clone <repo-url>
cd content_creation
```

Create virtual environment

```bash
python -m venv .venv
```

Activate

Windows

```bash
.venv\Scripts\activate
```

Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -e .
```

---

# 🔑 Environment Variables

Create a `.env` file.

```env
OPENAI_API_KEY=your_openai_key

SERPER_API_KEY=your_serper_key

SLACK_WEBHOOK_URL=your_slack_webhook
```

---

# ▶️ Run

```bash
crewai run
```

---

# 📤 Example Output

The system automatically generates:

- Research summary
- Technical insights
- 3 LinkedIn post options
- Suggested first comment
- Carousel/infographic idea
- Relevant hashtags
- Source links
- Slack notification

---

# 🎯 Future Improvements

- LinkedIn API publishing
- Image generation for carousels
- Multi-platform publishing (X, Medium, Dev.to)
- Notion integration
- Scheduled posting
- Analytics dashboard
- Content history database
- Vector database for previous posts
- Topic deduplication
- Human approval workflow
- n8n integration
- Email notifications

---

# 👨‍💻 Author

**Muzamal Ali**
AI Engineer | Data Scientist
