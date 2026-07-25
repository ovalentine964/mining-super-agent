# 02 — Team Structure & Organization

> Engineering Council Document #2
> Author: Engineering Manager (Council Member 2)
> Date: 2026-07-25

---

## 1. Big Tech Reference: How Top AI Teams Are Structured

### Google DeepMind / Google AI
| Layer | Structure |
|-------|-----------|
| Research | PhD-heavy, paper-driven, long-horizon bets |
| Applied ML | Bridges research → product, owns model serving |
| Platform/SRE | Infra, compute orchestration, monitoring |
| Product Eng | Frontend, APIs, integration |
| Data | Data pipelines, labeling ops, quality |
| Responsible AI | Safety, bias audits, red-teaming |

Key trait: **Extreme specialization.** Each person owns a narrow slice. Coordination happens through design docs and weekly cross-team syncs.

### OpenAI
| Layer | Structure |
|-------|-----------|
| Research | Core model training, RLHF, capability research |
| Safety | Alignment, red-teaming, policy |
| Applied | API platform, plugins, tool use |
| Product | ChatGPT, enterprise, consumer UX |
| Infra | GPU clusters, distributed training, serving |

Key trait: **Research-led.** Product teams serve research output. Heavy iteration speed.

### Anthropic
| Layer | Structure |
|-------|-----------|
| Research | Constitutional AI, interpretability, capability |
| Safety | Alignment stress-testing, evaluations |
| Platform | API, model serving, developer tools |
| Product | Claude consumer/enterprise experience |
| Ops | Scaling, reliability, compliance |

Key trait: **Safety-first culture.** Every feature goes through safety review before launch.

---

## 2. Ideal Team Structure (Big Tech Style)

If Valentine had unlimited budget, the Mining Super-Agent would need:

```
┌─────────────────────────────────────────────┐
│              CTO / Technical Lead            │
│                (Valentine)                   │
└──────────┬──────────┬──────────┬────────────┘
           │          │          │
    ┌──────┴──┐ ┌─────┴────┐ ┌──┴───────┐
    │ AI/ML   │ │ Platform │ │ Product  │
    │ Team    │ │ Team     │ │ Team     │
    │ (1-2)   │ │ (1-2)    │ │ (1-2)    │
    └─────────┘ └──────────┘ └──────────┘
    ┌─────────┐ ┌──────────┐
    │ Data    │ │ Security │
    │ Team    │ │ + QA     │
    │ (1)     │ │ (0.5+0.5)│
    └─────────┘ └──────────┘
```

**Total headcount for "ideal":** 6-8 people.

| Team | Size | Owns |
|------|------|------|
| AI/ML Team | 1-2 | Model selection, fine-tuning, inference pipeline, prompt engineering |
| Platform Team | 1-2 | API layer, database, CI/CD, monitoring, infrastructure |
| Product Team | 1-2 | Mobile app, Telegram bot, UX design, user feedback loop |
| Data Team | 1 | Data pipeline, flywheel analytics, knowledge base, data quality |
| Security Team | 0.5 | Security audits, compliance, threat modeling |
| QA Team | 0.5 | Test automation, regression, performance monitoring |

---

## 3. Reality Check: Solo Developer Constraints

**Year 1 Budget: $400-800 total.**
- $0 for salaries (all sweat equity)
- $400-800 for: domains, hosting, API costs, tools
- All software must be free/open-source

**Valentine is one person.** That means he wears every hat. The question is: which hats are most important, and what can be automated away?

---

## 4. Solo Developer Hat-Wearing Strategy

### The Hat Stack (Priority Order)

```
Priority 1 — MUST DO MANUALLY
├── CTO / Technical Architecture
├── AI/ML Engineer (model selection, prompt engineering)
├── Backend Engineer (API, database)
└── Product decisions (what to build, what to cut)

Priority 2 — CAN PARTIALLY AUTOMATE
├── Mobile App (cross-platform framework, templates)
├── Telegram Bot (bot frameworks, existing libraries)
├── Data Pipeline (automated scrapers, scheduled jobs)
└── DevOps (CI/CD templates, free hosting tiers)

Priority 3 — AUTOMATE OR DEFER
├── QA (automated testing, CI checks)
├── Security (dependency scanning, OWASP checklists)
├── Documentation (auto-generated from code)
└── Analytics (free-tier dashboards)
```

### Time Allocation (Solo Developer)

| Activity | % of Time | Notes |
|----------|-----------|-------|
| Core AI/ML | 35% | Model selection, fine-tuning, inference optimization |
| Backend/Platform | 30% | API, database, infrastructure |
| Product/Mobile | 20% | App development, bot, UX |
| Data/Ops | 10% | Pipeline, monitoring, analytics |
| Security/QA | 5% | Checklists, automated scans |

---

## 5. What Can Be Automated (Zero-Human Solutions)

| Function | Automation Strategy |
|----------|-------------------|
| **CI/CD** | GitHub Actions (free) — automated builds, tests, deployment |
| **Testing** | Pytest + Jest — automated test suites run on every commit |
| **Security** | Dependabot + Snyk free tier — dependency vulnerability scanning |
| **Monitoring** | Grafana + Prometheus (free) — dashboards, alerting |
| **Documentation** | Auto-generated from code comments and API schemas |
| **Analytics** | Plausible (self-hosted, free) or Umami — privacy-first analytics |
| **Code Review** | AI-assisted review (use your own AI to review code!) |
| **Data Pipeline** | Cron jobs + automated scrapers — no human in the loop |

**Net effect:** Automation can replace ~1.5 FTE worth of work. Valentine + good automation = a team of 2-3.

---

## 6. Recruitment Plan: The First 1-2 Cofounders

### Cofounder #1: AI/ML Engineer (Recruit First)

**Why first:** This is the core differentiator. Without strong AI, the product is just another mining dashboard.

**Skills needed:**
- Python, PyTorch/TensorFlow
- LLM fine-tuning (LoRA, QLoRA, RLHF)
- RAG systems, vector databases
- Model serving and inference optimization
- Mining domain knowledge (nice to have)

**Profile:**
- 3-5 years ML experience
- Comfortable with full-stack when needed
- Startup mindset — can wear multiple hats
- Values shipping over perfection

**How to find:**
- Mining + AI meetups/conferences
- GitHub contributors to mining ML projects
- LinkedIn search: "machine learning" + "mining" OR "geology"
- University mining engineering departments with AI research

### Cofounder #2: Full-Stack + Mobile Engineer (Recruit Second)

**Why second:** Once the AI works, you need someone to make it accessible — the app, the bot, the API.

**Skills needed:**
- React Native or Flutter (mobile)
- Node.js or Python (backend API)
- PostgreSQL/database design
- Telegram Bot API
- Basic DevOps (Docker, CI/CD)

**Profile:**
- 3-5 years full-stack experience
- Product-minded (cares about UX, not just code)
- Can handle both frontend and backend
- Comfortable with rapid prototyping

**How to find:**
- Startup communities (Indie Hackers, YC forums)
- Open-source mining tool contributors
- Tech meetups in mining regions (Perth, Vancouver, Johannesburg)

### What Valentine Keeps (Even After Recruiting)

| Role | Valentine's Ownership | Why |
|------|----------------------|-----|
| CTO | Always | Vision, architecture decisions |
| Product | Always | Domain expert, knows the users |
| Data | Initially | Needs to understand the flywheel |
| Security | Initially | Small enough to own personally |

---

## 7. Communication & Coordination

### Solo Phase (Months 1-6)

**Tools (all free):**
| Tool | Purpose |
|------|---------|
| GitHub | Code, issues, project boards |
| Discord (private server) | Async communication (even solo — future-proof) |
| Google Docs / Notion free | Design docs, decisions |
| GitHub Actions | CI/CD pipeline |

**Rhythms:**
- **Daily:** Write a short log in `memory/YYYY-MM-DD.md` (what was done, what's next)
- **Weekly:** Review GitHub project board, update priorities
- **Monthly:** Architecture review — is the design still sound?

### Small Team Phase (Months 6-12, with cofounders)

**Add:**
| Tool | Purpose |
|------|---------|
| Discord channels | `#ai-ml`, `#platform`, `#product`, `#general` |
| GitHub PRs | All code changes go through review |
| Weekly sync | 30-min video call — demo, blockers, priorities |
| Bi-weekly retro | What worked, what didn't, what to change |

**Decision-making framework:**
```
Small decisions (< 1 day of work):
  → Make the call, document in PR/commit

Medium decisions (1-5 days):
  → Write a short design doc, get async feedback

Large decisions (> 5 days or architectural):
  → Full design doc, team discussion, consensus required
```

### Scaling Communication (When Team Grows to 4-6)

| Practice | Frequency | Purpose |
|----------|-----------|---------|
| Standup (async) | Daily | What did you do? What's next? Blockers? |
| Sprint planning | Bi-weekly | Pick work for next 2 weeks |
| Demo day | Bi-weekly | Show what you built |
| 1:1s | Weekly | Individual alignment, growth |
| Architecture review | Monthly | Technical debt, design changes |
| Retrospective | Monthly | Process improvement |

---

## 8. Phase-Based Team Evolution

### Phase 1: Solo Builder (Months 0-6)
```
Team: Valentine (1 person)
Focus: MVP — core AI, basic API, Telegram bot
Automation: Maximum — CI/CD, automated testing, monitoring
Hats: All of them
```

### Phase 2: Founding Team (Months 6-12)
```
Team: Valentine + 1-2 cofounders (2-3 people)
Focus: Mobile app, real users, data flywheel
Structure: Everyone does everything, but with primary domains
Hats: Shared, but assigned
```

### Phase 3: Small Team (Months 12-18)
```
Team: 3-5 people
Focus: Scale, quality, multiple products
Structure: Clear team boundaries emerge
  - AI/ML (1-2)
  - Platform + Product (1-2)
  - Data + Ops (1)
Hats: Specializing
```

### Phase 4: Growth (Months 18+)
```
Team: 5-10 people
Focus: Enterprise features, compliance, growth
Structure: Formal teams with leads
  - AI/ML Team (2-3)
  - Platform Team (2)
  - Product Team (2)
  - Data Team (1)
  - Security/QA (1)
Hats: Dedicated roles
```

---

## 9. Key Principles

1. **Automation over headcount.** Every manual process is a candidate for automation before hiring.
2. **Generalists over specialists** (early). The first 3 people should all be able to ship end-to-end.
3. **Domain expertise is non-negotiable.** Mining knowledge > pure tech skill for cofounder #1.
4. **Async-first communication.** Document decisions. Write things down. Don't rely on tribal knowledge.
5. **Hire for slope, not intercept.** Find people who learn fast, not people who already know everything.
6. **Security is everyone's job** until you're big enough for a dedicated person.

---

## 10. Summary

| Question | Answer |
|----------|--------|
| How many teams? | 1 team of 1, growing to 3-4 teams by Month 18 |
| Who does what? | Valentine = everything initially; recruit AI/ML first |
| How do they coordinate? | GitHub + Discord + async docs |
| What can be automated? | CI/CD, testing, security scanning, monitoring, analytics |
| First hire? | AI/ML engineer with mining domain knowledge |
| Second hire? | Full-stack + mobile engineer, product-minded |
| Biggest risk? | Burnout — Valentine must automate ruthlessly to survive |

---

*Council Member 2 signing off. The structure scales from 1 to 10. Start lean, automate everything, recruit deliberately.*
