# Mining Super-Agent — Multi-Agent System

Council-approved, production-ready multi-agent system for mining intelligence in Kenya.

## Architecture

```
Orchestrator (Nemotron 3 Ultra)
├── Geological (Llama 405B) — rock analysis, deposit models
├── Satellite (Llama 405B) — Sentinel-2 alteration mapping
├── Mineral ID (Llama 8B) — photo-based mineral ID (EfficientNet-B4)
├── Market (Llama 8B) — commodity prices, trends
├── Legal (Llama 405B) — Kenya Mining Act 2016 compliance
├── Financial (Llama 405B) — NPV/IRR, CAPEX/OPEX
├── Community (Llama 8B) — stakeholder engagement, FPIC
├── Exploration (Llama 405B) — drilling programs, surveys
├── QC (Llama 8B) — cross-validation, consistency checks
└── Quantum (Llama 8B) — PennyLane/Qiskit quantum ML
```

## Key Design Decisions

1. **OpenAI function calling protocol** — NOT regex tool calling
2. **Pydantic schema validation** — all tool arguments validated
3. **Permission allowlists** — least privilege per agent
4. **Calibrated confidence** — never hardcoded 0.8
5. **Quantum + classical fallback** — every quantum op has classical backup

## Quick Start

```python
from src.main import MiningSuperAgent

agent = MiningSuperAgent()
result = await agent.analyze("Is there gold in Nyatike, Migori?")
```

## File Structure

```
src/
├── agents/
│   ├── base.py           — Base agent class (OpenAI function calling)
│   ├── orchestrator.py   — Routes to specialist agents
│   ├── geological.py     — Rock analysis, deposit models
│   ├── satellite.py      — Sentinel-2 alteration mapping
│   ├── mineral_id.py     — Photo mineral ID (EfficientNet-B4)
│   ├── market.py         — Commodity prices
│   ├── legal.py          — Kenya Mining Act 2016
│   ├── financial.py      — NPV/IRR, CAPEX/OPEX
│   ├── community.py      — Stakeholder engagement
│   ├── exploration.py    — Drilling programs
│   ├── qc.py             — Quality control
│   └── quantum.py        — Quantum ML (PennyLane/Qiskit)
├── tools/
│   ├── registry.py       — Plug-and-play tool system
│   ├── geological.py     — GemPy, SimPEG, Mindat
│   ├── satellite.py      — Sentinel-2, Planetary Computer
│   ├── market.py         — yfinance, Finnhub, Alpha Vantage
│   └── quantum.py        — PennyLane, Qiskit Aer
├── config/
│   ├── agents.yaml       — Agent definitions
│   └── tools.yaml        — Tool definitions
└── main.py               — Entry point
```

## Confidence Rules

| Agent | Max Confidence | Reason |
|-------|---------------|--------|
| Mineral ID (photo) | 65% | Photos unreliable for mineral ID |
| Satellite | 75% | Remote sensing has limitations |
| Market (prediction) | 60% | Price prediction inherently uncertain |
| Geological | 85% | Interpretation, not observation |
| Quantum | 80% | Quantum advantage but still probabilistic |
# Trigger CI build
