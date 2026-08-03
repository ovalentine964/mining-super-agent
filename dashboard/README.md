# Sovereign Resource DAO Dashboard

TypeScript + React + Vite dashboard for the Sovereign Resource DAO.

## Stack

- **React 18** + **TypeScript**
- **Vite** (dev server + production build)
- **wagmi + viem** — Polygon wallet connection
- **@tanstack/react-query** — data fetching with auto-refresh
- **recharts** — price charts
- **WebSocket** — real-time updates from FastAPI backend

## Development

```bash
npm install
npm run dev
```

Dashboard runs at `http://localhost:3000` with API proxy to `http://localhost:8000`.

## Production Build

```bash
npm run build
```

Output goes to `dist/` — ready for GitHub Pages deployment.

## API Endpoints Expected

| Endpoint | Description |
|----------|-------------|
| `GET /api/prices` | Mineral prices (gold, copper, silver) |
| `GET /api/extractions` | Extraction records |
| `GET /api/royalties` | Royalty distribution summary |
| `GET /api/proposals` | Governance proposals |
| `POST /api/proposals/:id/vote` | Vote on a proposal |
| `GET /api/fairness-index` | Extraction Fairness Index |
| `GET /api/satellite-alerts` | Satellite monitoring alerts |
| `WS /ws` | Real-time updates (JSON `{ type: "prices" }` etc.) |

## Bilingual

Toggle between English (EN) and Swahili (SW) via the header button.
