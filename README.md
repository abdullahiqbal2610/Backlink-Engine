# 🚀 Gaper Backlink AI Engine

A fully autonomous, AI-driven engine for generating high-quality backlinks and establishing thought leadership across multiple developer platforms.

## 🌟 Features

- **Discovery Engine**: Automatically discovers trending topics, questions, and discussions via SERP queries and RSS feeds.
- **LLM Pipeline Worker**: 
  - Analyzes discovered content for relevance.
  - Retrieves technical context using a RAG (Retrieval-Augmented Generation) store via ChromaDB.
  - Drafts high-quality, contextual responses using advanced LLMs.
- **Execution Router**: 
  - Automatically posts drafted content to target platforms.
  - Supports **Type A** (API-based) platforms like Dev.to and GitHub Gists.
  - Supports **Type B** (Browser-based) platforms like Medium using Playwright Stealth.
- **Admin Dashboard**: Fast API/Next.js-based dashboard to manually review and approve drafts, view historical posts, monitor system health, and track real-time analytics with Chart.js.
- **Autonomous Mode**: A single flip-switch in the dashboard UI (or `.env`) to go full autopilot.
- **Google Sheets Integration**: Automatically logs every successfully published backlink in real-time, extracting the exact live URL and the account used to post it.
- **Smart Contextual Backlinks**: Dynamically embeds diverse `gaper.io` URLs (`/blogs`, `/ai-agent-development-company`, etc.) organically within plain-text technical content to bypass spam filters and maximize SEO footprint.

## 🛠️ Architecture

- **PostgreSQL**: Stores persistent state for threads, platforms, and results.
- **Redis**: Handles task queues (`discovery_queue`, `review_queue`, `posting_queue`) for asynchronous execution.
- **ChromaDB**: Vector database for RAG context retrieval.
- **Playwright**: Automates browser sessions with stealth plugins for strict platforms, featuring robust slide-in drawer and Javascript fallback selectors.
- **Google Sheets API**: Uses service account credentials for seamless background tracking.

## 🚀 Getting Started

### Prerequisites

- Docker (for PostgreSQL & Redis)
- Python 3.11+
- Node.js (for the Dashboard)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/abdullahiqbal2610/Gaper-Backlink-Engine.git
   cd Gaper-Backlink-Engine
   ```

2. **Set up the environment:**
   The codebase uses an automated environment switching system across branches:
   - Create a `.env.local` file for your local database/redis connections (used on `main` branch).
   - Create a `.env.cloud` file for your cloud/Neon/Upstash connections (used on `branch1` deployed version).
   - **Magic Git Hook**: A post-checkout git hook automatically copies the correct file into `.env` whenever you switch between `main` and `branch1`. You never have to manually edit database variables!

   *Note: Ensure all API keys (Gemini, Dev.to, etc.) are present in both `.env.local` and `.env.cloud`.*
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   cd dashboard
   npm install
   cd ..
   ```

### Running the Engine

You can start the entire stack (Database, Queues, Workers, and Dashboard) with a single click:

**Windows:**
Double-click `start_all.bat` or run it from the terminal:
```bash
start_all.bat
```

Access the Admin Dashboard at: `http://localhost:8000`

## 🧠 Supported Platforms
- **Hashnode** (Playwright Stealth - Full article publishing with Drafts Dashboard integration)
- **Medium** (Playwright Stealth)
- **Dev.to** (API)
- **GitHub Gists** (API)
- **Reddit** (Playwright - Optional)

## 🍪 Cookie Management for Browser Platforms
For platforms that require browser automation (Hashnode, Medium, Reddit), you must provide session cookies.
1. Install the **Cookie-Editor** extension (by cgagnier) in Chrome.
2. Log in to the target platform (e.g., hashnode.com).
3. Click the extension, click **Export -> Export as JSON**.
4. Save the copied JSON into the `browser_profiles/` folder (e.g., `browser_profiles/hashnode_cookies.json`).
If the automation fails with a login redirect error, simply re-export the latest cookies.

## 🔒 Security
All browser session cookies and tokens are safely stored in the local `browser_profiles/` directory and are heavily `.gitignore`d. Do not commit these files to version control.
