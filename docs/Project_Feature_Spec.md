# 📑 Project Functional Specification & Status Report | 项目功能规格与现状报告

This document provides a professional, bilingual overview of the Interactive AI Storybook project's functional design, technical implementation, and current development status.

这份文档提供了互动 AI 绘图项目的专业中英文功能设计、技术实现及当前开发现状概览。

---

## 1. Library Management | 绘本库管理

| Feature | 功能描述 | Interaction | 交互逻辑 | Status | 现状 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PDF Import** | Import local PDF documents into the cloud library. | User selects file -> POST to Kotlin -> File saved to `/uploads` -> DB updated. | 用户选择文件 -> POST 到 Kotlin -> 文件保存至目录 -> 更新数据库。 | Implemented (Stable) | 已实现 (稳定) |
| **Grid View** | Visual overview of all imported books. | Frontend GET `/api/books` -> Render cards -> Dynamic path handling. | 前端获取书籍列表 -> 渲染横卡 -> 动态路径处理。 | Implemented (Stable) | 已实现 (稳定) |
| **Cover Generation** | Automatic detection of Page 1 as the book cover. | Backend serves `page_001.jpg` from the book folder. | 后端从书籍文件夹中提供第一张图作为封面。 | Implemented | 已实现 |
| **Book Deletion** | Complete removal of book files and records. | User clicks delete -> DELETE to Kotlin -> File cleanup -> Refresh grid. | 用户点击删除 -> DELETE 到 Kotlin -> 文件清理 -> 刷新网格。 | Implemented | 已实现 |
| **Large File Support** | Handling books over 100MB. | Configured via Spring `Multipart` settings (500MB). | 通过 Spring Multipart 配置（500MB）。 | Implemented | 已实现 |

---

## 2. Interactive Reader | 交互式阅读内核

| Feature | 功能描述 | Interaction | 交互逻辑 | Status | 现状 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Canvas Rendering** | High-fidelity rendering of PDF pages. | `pdf.js` renders to hidden canvas -> Display as image. | `pdf.js` 渲染至隐藏画布 -> 以图片显示。 | Implemented | 已实现 |
| **Rotation Control** | 90-degree incremental rotation of pages. | Click Rotate -> POST to Kotlin -> Persistent rotation metadata. | 点击旋转 -> POST 到 Kotlin -> 持久化旋转元数据。 | Implemented | 已实现 |
| **Bilingual TTS** | Multi-engine text-to-speech (EN/CN). | `SpeechSynthesis` API with voice selection & pause/stop. | 调用语音合成 API，支持语音选择及暂停/停止。 | Implemented | 已实现 |
| **Translation Engine** | Automated translation for hotspots. | Hotspot detect -> Google Translate API (Frontend Proxy). | 热点检测 -> 谷歌翻译 API。 | Implemented | 已实现 |
| **Zoom & Pan** | Zooming into illustrations. | CSS transform / Viewport scaling. | CSS 变换 / 视口缩放。 | **Planned (Design)** | **规划中 (设计)** |

---

## 3. AI Automation Engine | AI 自动化引擎

| Feature | 功能描述 | Interaction | 交互逻辑 | Status | 现状 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Auto-OCR Trigger**| Zero-click scan after 1.5s delay. | Page Flip -> Timer -> Capture Canvas -> Send to OCR. | 翻页 -> 计时器 -> 捕获画布 -> 发送至 OCR。 | Implemented | 已实现 |
| **Micro-service Link**| Handshake between Frontend & Python. | `fetch()` call to Port 8001 -> JSON results. | 调用 8001 端口 -> 返回 JSON。 | Stable | 稳定 |
| **Column Merging** | Proximity-based block clustering. | AI Service clusters lines by X-centers & vertical distance. | AI 服务根据 X 轴中心和垂直距离对行进行聚类。 | Implemented (High-Deep) | 已实现 (深度) |
| **Bulk Scanning** | AI background scan for the whole book. | Loop through all PDF pages -> Batch OCR -> Batch Sync. | 遍历 PDF 所有页面 -> 批量 OCR -> 批量同步。 | Implemented | 已实现 |
| **Layout Filtering**| Filter giant "noise" blocks. | Ignore blocks covering >90% of page. | 忽略覆盖率 >90% 的“噪声”块。 | Implemented | 已实现 |

---

## 4. Vocabulary System | 生词学习系统

| Feature | 功能描述 | Interaction | 交互逻辑 | Status | 现状 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Quick Star** | One-click save word to vocab book. | Reader Star click -> POST `/api/vocabulary`. | 阅读界面点击星标 -> POST 到后端。 | Implemented | 已实现 |
| **Vocab Review** | A dedicated view for review. | Tab switch -> GET `/api/vocabulary` -> Render list. | 切页 -> 获取列表 -> 渲染列表。 | Implemented (Basic) | 已实现 (基础) |
| **Mastery Level** | 0-5 levels of word mastery. | DB Column `mastery_level` exists. | 数据库中已存在掌握度列。 | **Not Implemented** | **未实现 (仅存 DB)** |
| **Contextual Audio** | Play audio linked to the vocab word. | `speak(item.word)` in review tab. | 复习界面调用语音合成。 | Implemented | 已实现 |
| **Sentence Reference**| Show the original sentence context. | DB Column `source_sentence` exists. | 数据库中已存在原句列。 | **Planned (UI Only)** | **规划中 (界面未出)** |

---

## 5. Implementation Depth & Audit | 实现深度与审计

### ✅ Deep Implementation (Production-Ready) | 深度实现
- **OCR Cluster Merger**: Far more advanced than raw Tesseract; handles complex layouts. (比原生识别更先进，能处理复杂布局)。
- **Cloud Sync Engine**: Robust debounced syncing to MySQL with error recovery. (强健的防抖同步机制，支持错误恢复)。

### ⚠️ Technical Debt / Debug Checklist | 技术债与调试清单
- **Memory Management**: Large PDFs can cause browser memory spikes during "Bulk Scan". (大文件 PDF 在“批量扫描”时可能导致浏览器内存激增)。
- **CORS Dependency**: API currently relies on `@CrossOrigin(origins = ["*"])`. Should be hardened later. (API 目前依赖万能跨域，后续需加固)。
- **Responsive Layout**: Some editor panels may overlap on small tablets. (部分编辑器面板在小型平板上可能重合)。

### 🚀 Future Roadmap | 未来路线图
1. **AI Mnemonics**: Use LLM to generate memory tips for vocabulary. (利用大模型生成生词助记法)。
2. **Interactive Quiz**: Generate game-style quizzes from scanned pages. (根据扫描页面生成游戏化测验)。
3. **Multi-User**: User accounts and progress tracking. (用户体系与进度追踪)。

---
*Created by Antigravity AI Engine | 由 Antigravity AI 引擎驱动生成*
