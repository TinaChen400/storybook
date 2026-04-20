# 📖 Interactive AI Storybook: Project Development Guide

This document provides a comprehensive overview of the design philosophy, technical architecture, and implementation history of the Interactive AI Storybook platform. It serves as the primary "Source of Truth" for developers maintaining or extending the system.

---

## 1. Introduction & Design Philosophy (The "Why")

### Core Goal
The project aims to transform traditional static storybooks into interactive, bilingual learning tools using AI. Instead of manual data entry, the system uses OCR to "see" the page and automatically generate interactive hotspots.

### Why this Architecture?
- **Separation of Concerns**: We use a **Micro-service Architecture** (even in a local dev environment) to separate high-demand AI tasks (Python) from business logic (Kotlin) and the interactive UI (Vanilla JS).
- **AI-First UX**: The "Zero-Click" automation (Auto-OCR 1.5s after page flip) is designed for children, removing the friction of manual scanning buttons.
- **Stateless Intelligence**: The OCR service is stateless, allowing it to be scaled independently or swapped with cloud-based OCR services without touching the frontend logic.

---

## 2. System Architecture & Data Flow

### Service Map
| Service | Technology | Port | Role |
| :--- | :--- | :--- | :--- |
| **Frontend** | Vanilla JS / PDF.js | 5500 | Main交互界面, TTS, Canvas 渲染 |
| **Backend** | Kotlin / Spring Boot | 8080 | 业务逻辑, MySQL/Redis 管理, 资源存储 |
| **AI Service** | Python / FastAPI | 8001 | PaddleOCR 图像识别与跨栏合并算法 |
| **Database** | MySQL 8.0 | 3307 | 书籍元数据、热点坐标、词汇表持久化 |

### The Lifecycle of a Page
1. **Render**: User flips a page; `pdf.js` renders to a canvas.
2. **Analyze**: If no hotspots exist, `app.js` sends the canvas image to the AI Service.
3. **Merge**: AI Service runs OCR and applies a **Column-Aware Merging Algorithm** to group sentences.
4. **Persist**: Results are sent to the Backend for MySQL storage.
5. **Interactive**: User clicks a hotspot; `SpeechSynthesis` provides bilingual audio.

---

## 3. Environment & Dependencies

### Infrastructure
- **MySQL 8.0**: Required for `HOTSPOTS` and `VOCABULARY` tables.
- **Redis**: Recommended for page metadata caching (optional but implemented in Gradle).

### Backend (Kotlin/JVM 21)
- `spring-boot-starter-data-jpa`: Database ORM.
- `spring-boot-starter-web`: API layer.
- `mysql-connector-j`: DB Driver.
- **Upgrade Note**: Spring Boot can be safely upgraded; Java versions should stay 17+.

### AI Service (Python 3.10)
- `fastapi`: API framework.
- `paddleocr==2.7.3`: **CRITICAL**. Pins for stability; OCR results vary significantly between versions.
- `pillow==10.3.0`: Image processing.

---

## 4. API Documentation

### Book Management
- `GET /api/books`: List all books.
- `GET /api/books/{id}`: Get full book hierarchy (including pages/hotspots).
- `POST /api/books/upload`: Import PDF and create structure.
- `DELETE /api/books/{id}`: Clean up files and DB records.

### Sync & Intelligence
- `POST /api/books/{id}/sync-page?pageNumber=X`: Update/Save hotspots for a specific page.
- `POST /api/books/{id}/rotation?angle=X`: Update PDF viewing angle.

---

## 5. The "Hacker's Guide" (Hidden Pitfalls & Fixes)

This section documents "weird" code segments left to solve specific compatibility or UX issues.

### 5.1 The "Flicker Guard" (`app.js`)
```javascript
if (now - state.lastRenderTime < 300) return;
```
- **Why**: When resizing or rapid-flipping, the library grid would "flash" and re-fetch images, causing high CPU usage and poor UX. This debounce ensures smooth rendering.

### 5.2 Intra-Column Merging (`main.py`)
- **Quirk**: Standard OCR returns text blocks in reading order, often mixing text from left and right columns in children's books.
- **Fix**: We implemented a `merge_blocks` algorithm that clusters blocks based on **Center X coordinates** first (Column Detection) before merging them vertically. This is essential for 2-column children's book layouts.

### 5.3 Event Delegation for Dynamic Elements
- **Quirk**: New books added to the library wouldn't respond to clicks if listeners were attached during initialization.
- **Fix**: The `el.bookGrid.onclick` uses **Event Delegation**. We listen on the container and use `e.target.closest('.book-card')` to identify which book was clicked, even for items created 1 second ago.

### 5.4 Spring Boot Multipart Limits
- **Quirk**: Default upload limit is ~1MB.
- **Fix**: `application.properties` explicitly sets `max-file-size=500MB`. Children's books with high-res illustrations are frequently 50-100MB+.

---

## 6. Development History & Technical Pivots

### Phase 1: The Static Prototype
- **Status**: Completed.
- **Goal**: Basic PDF viewer with hardcoded `books.json`.
- **Constraint**: No data persistence; everything lost on refresh.

### Phase 2: AI Automation (The OCR Pivot)
- **Status**: Completed.
- **Shift**: Switched from Tesseract (Legacy) to **PaddleOCR**.
- **Result**: Drastic improvement in accuracy for short, stylized children's text.

### Phase 3: The Cloud Migration
- **Status**: Completed.
- **Shift**: Introduced the Kotlin Backend and MySQL.
- **Result**: Data now persists across devices and sessions.

### Phase 4: UX & Edge Cases (Current)
- **Status**: Active.
- **Focus**: Fixing image errors, optimizing bulk scans, and vocabulary review.

---

## 7. Deployment & Operations

### Quick Start (Local Docker)
```powershell
cd storybookv2\dev-env
docker compose up -d
```

### Static File Management
- PDFs and Page Images are stored in `backend-kotlin/uploads/`.
- **Warning**: Ensure this directory has write permissions if running outside Docker.
