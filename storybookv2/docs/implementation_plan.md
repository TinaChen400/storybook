# Finalized Professional Full-Stack AI Storybook Architecture

We are building a state-of-the-art interactive reading system using the most modern industry tools. This will be a multi-service project (Monorepo) to ensure clean separation of concerns.

## Technical Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Frontend** | **Next.js (TypeScript)** | Interactive UI, Canvas, Real-time sync |
| **Backend** | **Kotlin (Spring Boot)** | Business logic, MySQL/Redis management |
| **AI Service** | **Python (FastAPI)** | OCR, LLM Integration, Podcast synthesis |
| **Database** | **MySQL 8.0** | Persistent storage for books and vocabulary |
| **Cache** | **Redis** | Speed optimization for page metadata |
| **DevOps** | **Docker + GitHub Actions** | Professional deployment and environment management |

## Project Structure

```text
stroybook-v2/
├── frontend/           # Next.js + TypeScript
├── backend-kotlin/     # Spring Boot + Kotlin
├── service-ai/         # Python (AI Logic)
├── dev-env/            # Docker Compose & MySQL configs
└── docs/               # Project Documentation (You are here)
```

## Implementation Roadmap

### Phase 1: The Foundation (Current Step)
- [x] Set up **Docker Compose** for MySQL and Redis.
- [x] Design the **MySQL Schema** (Books, Pages, Hotspots, Vocabulary).
- [ ] Initialize the **Kotlin (Spring Boot)** project.

### Phase 3: Frontend-Backend Integration (The Bridge)

In this phase, we will connect the existing interactive reader to the new Kotlin backend.

### 3.1 Enable CORS in Spring Boot
The frontend and backend will likely run on different ports (e.g., 5500 vs 8080). We must allow cross-origin requests.

- [ ] Add `@CrossOrigin` to Controllers or a global Configuration.

### 3.2 Update Frontend (app.js)
Modify the interactive reader's core logic to persist data.

- [ ] Add a "Save to Vocabulary" functionality in the translation/annotation popup.
- [ ] Implement `fetch()` calls to `POST http://localhost:8080/api/vocabulary`.

### 3.3 Verify End-to-End
1. Annotate a word in the browser.
2. Click "Save".
3. Verify data appears in the database via `/api/vocabulary`.

### Phase 2: Core Persistence
- [ ] Implement Book/Page API in Kotlin.
- [ ] Connect Kotlin to MySQL and Redis.
- [ ] Establish the Unique ID (UUID) system for every box.

... (Simplified for the user's reference file)
