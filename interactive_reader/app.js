// Interactive Bilingual Storybook Reader
// PDF.js + PaddleOCR Integration

// PDF.js worker setup
if (window.pdfjsLib || window.pdf) { (window.pdfjsLib || window.pdf).GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'; }

// Constants
const API_BASE = 'http://127.0.0.1:8080';
const OCR_API = 'http://127.0.0.1:8001';

// State
const state = {
    books: [],
    currentBook: null,
    currentPage: 0,
    totalPages: 0,
    pdfDoc: null,
    pageRendering: false,
    pageNumPending: null,
    pageEdits: {}, // Store unsaved session edits: { pageNum: [hotspots] }
    savedHotspots: [],
    currentLanguage: 'en',
    editorMode: false,
    voices: { en: null, cn: null },
    audio: null,
    isDrawing: false,
    drawStart: { x: 0, y: 0 },
    tempBox: null
};

// DOM Elements
const el = {
    libraryView: document.getElementById('library-view'),
    readerView: document.getElementById('reader-view'),
    bookGrid: document.getElementById('book-grid'),
    pageImage: document.getElementById('page-image'),
    hotspotLayer: document.getElementById('hotspot-layer'),
    editorLayer: document.getElementById('editor-layer'),
    currentPageNum: document.getElementById('current-page-num'),
    totalPagesNum: document.getElementById('total-pages-num'),
    currentBookTitle: document.getElementById('current-book-title'),
    editorPanel: document.getElementById('editor-panel'),
    ocrPreviewCanvas: document.getElementById('ocr-preview-canvas'),
    ocrStatus: document.getElementById('ocr-status'),
    hotspotList: document.getElementById('hotspot-list'),
    voiceSelectEn: document.getElementById('voice-select-en'),
    voiceSelectCn: document.getElementById('voice-select-cn')
};

// ============ INITIALIZATION ============

document.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing Storybook Reader...');
    initEventListeners();
    await loadVoices();
    loadBooks();
});

// ============ EVENT LISTENERS ============

function initEventListeners() {
    // Import PDF
    document.getElementById('btn-import-pdf').addEventListener('click', () => {
        document.getElementById('pdf-upload-input').click();
    });
    document.getElementById('pdf-upload-input').addEventListener('change', handlePdfUpload);

    // Navigation
    document.getElementById('back-to-library').addEventListener('click', goToLibrary);
    document.getElementById('prev-page').addEventListener('click', () => changePage(-1));
    document.getElementById('next-page').addEventListener('click', () => changePage(1));

    // Language toggle
    document.getElementById('toggle-language').addEventListener('click', toggleLanguage);


    // Editor Mode
    document.getElementById('toggle-editor').addEventListener('click', toggleEditorMode);
    document.getElementById('clear-hotspots').addEventListener('click', clearHotspots);
    document.getElementById('translate-all').addEventListener('click', translateAllHotspots);
    document.getElementById('save-hotspots').addEventListener('click', saveHotspotsCurrentPage);
    document.getElementById('restart-ocr').addEventListener('click', restartOCR);
    document.getElementById('copy-json').addEventListener('click', copyHotspotsJSON);

    // AI Scan
    document.getElementById('ai-scan-btn').addEventListener('click', runOCRCurrentPage);

    // Voice controls
    document.getElementById('play-voice').addEventListener('click', playCurrentHotspot);
    document.getElementById('stop-voice').addEventListener('click', stopVoice);
    
    if (el.voiceSelectEn) {
        el.voiceSelectEn.addEventListener('change', (e) => {
            const voice = speechSynthesis.getVoices().find(v => v.name === e.target.value);
            if (voice) state.voices.en = voice;
        });
    }
    if (el.voiceSelectCn) {
        el.voiceSelectCn.addEventListener('change', (e) => {
            const voice = speechSynthesis.getVoices().find(v => v.name === e.target.value);
            if (voice) state.voices.cn = voice;
        });
    }

    // Editor Drawing
    if (el.editorLayer) {
        el.editorLayer.addEventListener('mousedown', startDrawing);
        el.editorLayer.addEventListener('mousemove', draw);
        window.addEventListener('mouseup', endDrawing);
    }
}

// ============ PDF HANDLING ============


async function handlePdfUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        showToast('Uploading PDF...');
        const response = await fetch(`${API_BASE}/api/books/upload`, {
            method: 'POST',
            body: formData
        });
        if (!response.ok) throw new Error('Upload failed on server');
        const book = await response.json();
        showToast('PDF imported successfully!');
        loadBooks();
    } catch (err) {
        console.error('Upload failed:', err);
        showToast('Upload failed: ' + err.message);
    }
}

async function loadBooks() {
    try {
        console.log('Attempting to load books from API...');
        const response = await fetch(`${API_BASE}/api/books`);
        if (!response.ok) throw new Error('API unavailable');
        const books = await response.json();
        state.books = books;
        renderBookGrid(books);
    } catch (err) {
        console.warn('API load failed, falling back to local books.json:', err);
        try {
            const response = await fetch('books.json');
            const data = await response.json();
            // Support both root array and nested {books:[]} format
            state.books = Array.isArray(data) ? data : (data.books || []);
            renderBookGrid(state.books);
        } catch (localErr) {
            console.error('Failed to load local books.json:', localErr);
            showToast('Failed to load library data.');
        }
    }
}

function renderBookGrid(books) {
    if (!el.bookGrid) return;
    el.bookGrid.innerHTML = books.map(book => {
        // Resolve cover URL (handle potential relative paths in books.json)
        let coverUrl = book.coverUrl || book.cover || '';
        if (coverUrl && !coverUrl.startsWith('http') && !coverUrl.startsWith('data:')) {
            // If it's a local fallback, we might need to adjust path
            // books.json uses relative paths like "../book_clay/page_001.jpg"
            // We'll leave them as is or try to normalize
        }
        
        return `
        <div class="book-card" data-id="${book.id}">
            <div class="book-cover">
                <img src="${coverUrl || 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22150%22><rect fill=%22%23633%22 width=%22100%22 height=%22150%22/><text fill=%22white%22 x=%2250%22 y=%2280%22 text-anchor=%22middle%22>📖</text></svg>'}" alt="${book.title}" onerror="this.src='https://via.placeholder.com/150x200?text=Book'">
            </div>
            <div class="book-info">
                <h3>${book.title}</h3>
                <p>${book.pageCount || (book.pages ? book.pages.length : 0)} pages</p>
            </div>
        </div>
    `}).join('');

    document.querySelectorAll('.book-card').forEach(card => {
        card.addEventListener('click', () => openBook(card.dataset.id));
    });
    
    // Refresh lucide icons
    if (window.lucide) lucide.createIcons();
}

async function openBook(bookId) {
    try {
        showToast('Loading book details...');
        
        // Fetch full book detail (includes all pages and hotspots from DB)
        let book;
        const response = await fetch(`${API_BASE}/api/books/${bookId}`);
        if (response.ok) {
            book = await response.json();
            console.log('Deep loaded book detail from backend');
        } else {
            // Fallback to local state if backend fetch fails
            book = state.books.find(b => b.id === bookId);
            console.warn('Backend detail fetch failed, falling back to local metadata');
        }

        if (!book) throw new Error('Book not found');
        
        state.currentBook = book;
        state.totalPages = book.pages?.length || 0;
        state.currentPage = 0;
        
        // Load PDF or Images
        const pdfUrl = book.pdfUrl || (book.pdfPath ? `${API_BASE}${book.pdfPath}` : null);
        
        if (pdfUrl) {
            console.log('Loading PDF from:', pdfUrl);
            const loadingTask = pdfjsLib.getDocument(pdfUrl);
            state.pdfDoc = await loadingTask.promise;
            state.totalPages = state.pdfDoc.numPages;
        }

        // Switch to reader view
        el.libraryView.classList.remove('active');
        el.readerView.classList.add('active');
        el.currentBookTitle.textContent = book.title;
        el.totalPagesNum.textContent = state.totalPages;

        // Reset per-page session edits when opening a new book
        state.pageEdits = {};

        await renderPage(1);
    } catch (err) {
        console.error('Failed to open book:', err);
        showToast('Failed to open book: ' + err.message);
    }
}

async function renderPage(num) {
    state.pageRendering = true;
    try {
        let imgUrl = '';
        if (state.pdfDoc) {
            const page = await state.pdfDoc.getPage(num);
            const viewport = page.getViewport({ scale: 1.5 });
            
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;

            await page.render({ canvasContext: context, viewport: viewport }).promise;
            imgUrl = canvas.toDataURL('image/png');
        } else {
            // Fallback for image-based books in books.json
            const pageData = state.currentBook.pages[num - 1];
            if (pageData) {
                // Handle relative paths
                const bookFolder = state.currentBook.folder || '';
                imgUrl = pageData.image.startsWith('http') ? pageData.image : `${bookFolder}${pageData.image}`;
            }
        }
        
        // Set image and wait for load to render hotspots
        el.pageImage.onload = () => {
             syncLayerDimensions();
             // Load hotspots for this page once image is ready for scaling calculations
             loadPageHotspots(state.currentBook?.id, num);
        };
        el.pageImage.src = imgUrl;
        
        state.currentPage = num - 1;
        el.currentPageNum.textContent = num;

    } catch (err) {
        console.error('Render error:', err);
    }
    state.pageRendering = false;

    if (state.pageNumPending !== null) {
        renderPage(state.pageNumPending);
        state.pageNumPending = null;
    }
}

function changePage(delta) {
    const newPage = state.currentPage + 1 + delta;
    if (newPage >= 1 && newPage <= state.totalPages) {
        if (state.pageRendering) {
            state.pageNumPending = newPage;
        } else {
            renderPage(newPage);
        }
    }
}

function goToLibrary() {
    el.readerView.classList.remove('active');
    el.libraryView.classList.add('active');
    state.currentBook = null;
    state.pdfDoc = null;
    loadBooks();
}

// ============ HOTSPOT RENDERING ============

function loadPageHotspots(bookId, pageNum) {
    // Priority: 1. Current session edits, 2. Book saved data
    let hotspots = [];
    
    if (state.pageEdits[pageNum]) {
        hotspots = state.pageEdits[pageNum];
    } else if (state.currentBook?.pages) {
        const page = state.currentBook.pages.find(p => p.pageNumber === pageNum);
        hotspots = page?.hotspots || [];
    }
    
    // Normalize data schema (Backend uses textEn/textZh, frontend uses text_en/text_zh)
    const normalized = hotspots.map(normalizeHotspot);
    renderHotspots(normalized);
}

function normalizeHotspot(hs) {
    return {
        ...hs,
        x: hs.x ?? 0,
        y: hs.y ?? 0,
        w: hs.width ?? hs.w ?? 10,
        h: hs.height ?? hs.h ?? 5,
        text_en: hs.text_en || hs.text || hs.textEn || '',
        text_zh: hs.text_zh || hs.translatedText || hs.textZh || ''
    };
}

function syncLayerDimensions() {
    if (!el.pageImage || !el.hotspotLayer) return;
    
    // Get the actual displayed dimensions of the image (accounting for object-fit: contain)
    const rect = el.pageImage.getBoundingClientRect();
    
    // We adjust the layers to exactly match the image bounds
    [el.hotspotLayer, el.editorLayer].forEach(layer => {
        if (!layer) return;
        layer.style.width = el.pageImage.clientWidth + 'px';
        layer.style.height = el.pageImage.clientHeight + 'px';
        
        // Match the position (in case of padding/margins)
        layer.style.top = el.pageImage.offsetTop + 'px';
        layer.style.left = el.pageImage.offsetLeft + 'px';
    });
}

function renderHotspots(hotspots) {
    if (!el.hotspotLayer || !el.pageImage) return;
    
    // Sync layers first to ensure scale math 1:1 with visual image
    syncLayerDimensions();
    
    el.hotspotLayer.innerHTML = '';
    
    // Ensure image is loaded to get correct client dimensions
    if (!el.pageImage.complete || el.pageImage.naturalWidth === 0) {
        console.log('Image not ready yet, delay rendering hotspots...');
        setTimeout(() => renderHotspots(hotspots), 50);
        return;
    }

    const clientW = el.pageImage.clientWidth;
    const clientH = el.pageImage.clientHeight;
    const naturalW = el.pageImage.naturalWidth || clientW;
    const naturalH = el.pageImage.naturalHeight || clientH;
    
    const scaleX = clientW / (naturalW || 1);
    const scaleY = clientH / (naturalH || 1);
    
    console.log(`Rendering ${hotspots.length} hotspots. Scale: ${scaleX.toFixed(3)}, ${scaleY.toFixed(3)}`);
    
    hotspots.forEach((hotspot, index) => {
        // Normalize hotspot keys (support BOTH API format and books.json format)
        const x = hotspot.x ?? 0;
        const y = hotspot.y ?? 0;
        const w = hotspot.width ?? hotspot.w ?? 10;
        const h = hotspot.height ?? hotspot.h ?? 5;
        
        // Handle coordinates: some are absolute (pixels), some are percentages (0-100)
        // If x, y are small (e.g. < 100) and naturalW is large, they might be percentages
        let left, top, width, height;
        
        if (x <= 100 && y <= 100 && naturalW > 500) {
            // Probably percentage based (common in manual JSON)
            left = (x * clientW) / 100;
            top = (y * clientH) / 100;
            width = (w * clientW) / 100;
            height = (h * clientH) / 100;
        } else {
            // Probably pixel based (common in API OCR)
            left = x * scaleX;
            top = y * scaleY;
            width = w * scaleX;
            height = h * scaleY;
        }

        const box = document.createElement('div');
        box.className = 'hotspot-box';
        box.dataset.index = index;
        
        box.style.left = left + 'px';
        box.style.top = top + 'px';
        box.style.width = width + 'px';
        box.style.height = height + 'px';
        
        // Normalize text
        const text = state.currentLanguage === 'en' 
            ? (hotspot.text_en || hotspot.text || '') 
            : (hotspot.text_zh || hotspot.translatedText || hotspot.text || '');
            
        box.innerHTML = `<span class="hotspot-text">${text}</span>`;
        box.addEventListener('click', (e) => {
            e.stopPropagation();
            selectHotspot(hotspot);
        });
        
        el.hotspotLayer.appendChild(box);
    });

    // If in editor mode, also render the editable list
    if (state.editorMode) {
        renderHotspotList(hotspots);
    }
}

function renderHotspotList(hotspots) {
    if (!el.hotspotList) return;
    
    el.hotspotList.innerHTML = hotspots.map((hs, i) => {
        const normalized = normalizeHotspot(hs);
        return `
            <div class="hotspot-item" data-index="${i}">
                <div class="hs-item-header">
                    <span>Box #${i + 1}</span>
                    <button class="btn-delete-hs" onclick="deleteHotspot(${i})">×</button>
                </div>
                <div class="hs-inputs">
                    <input type="text" placeholder="English text" value="${normalized.text_en}" oninput="updateHotspotText(${i}, 'en', this.value)">
                    <input type="text" placeholder="Chinese text" value="${normalized.text_zh}" oninput="updateHotspotText(${i}, 'zh', this.value)">
                </div>
            </div>
        `;
    }).join('');
}

window.deleteHotspot = function(index) {
    const pageNum = state.currentPage + 1;
    if (state.pageEdits[pageNum]) {
        state.pageEdits[pageNum].splice(index, 1);
        renderHotspots(state.pageEdits[pageNum]);
    }
};

window.updateHotspotText = function(index, lang, value) {
    const pageNum = state.currentPage + 1;
    if (!state.pageEdits[pageNum] || !state.pageEdits[pageNum][index]) return;
    
    const hs = state.pageEdits[pageNum][index];
    if (lang === 'en') {
        hs.text_en = value;
        hs.text = value; 
    } else {
        hs.text_zh = value;
        hs.translatedText = value;
    }
};

// ============ DRAWING LOGIC ============

function startDrawing(e) {
    if (!state.editorMode) return;
    state.isDrawing = true;
    const rect = el.editorLayer.getBoundingClientRect();
    state.drawStart = { 
        x: e.clientX - rect.left, 
        y: e.clientY - rect.top 
    };
    
    state.tempBox = document.createElement('div');
    state.tempBox.className = 'editor-selection';
    el.editorLayer.appendChild(state.tempBox);
}

function draw(e) {
    if (!state.isDrawing || !state.tempBox) return;
    const rect = el.editorLayer.getBoundingClientRect();
    const curX = e.clientX - rect.left;
    const curY = e.clientY - rect.top;
    
    const left = Math.min(state.drawStart.x, curX);
    const top = Math.min(state.drawStart.y, curY);
    const width = Math.abs(state.drawStart.x - curX);
    const height = Math.abs(state.drawStart.y - curY);
    
    state.tempBox.style.left = left + 'px';
    state.tempBox.style.top = top + 'px';
    state.tempBox.style.width = width + 'px';
    state.tempBox.style.height = height + 'px';
}

function endDrawing(e) {
    if (!state.isDrawing) return;
    state.isDrawing = false;
    
    if (state.tempBox) {
        const rect = el.editorLayer.getBoundingClientRect();
        const clientW = rect.width;
        const clientH = rect.height;
        
        // Convert client pixels to percentages (0-100) for storage
        const x = (parseFloat(state.tempBox.style.left) / clientW) * 100;
        const y = (parseFloat(state.tempBox.style.top) / clientH) * 100;
        const w = (parseFloat(state.tempBox.style.width) / clientW) * 100;
        const h = (parseFloat(state.tempBox.style.height) / clientH) * 100;
        
        // Only add if it's large enough (prevent tiny clicks)
        if (w > 1 && h > 1) {
            const pageNum = state.currentPage + 1;
            if (!state.pageEdits[pageNum]) {
                // If it's the first edit on this page, copy current hotspots to session
                const existingPage = state.currentBook.pages?.find(p => p.pageNumber === pageNum);
                state.pageEdits[pageNum] = existingPage ? JSON.parse(JSON.stringify(existingPage.hotspots || [])) : [];
            }
            
            state.pageEdits[pageNum].push({
                x, y, w: w, h: h,
                text_en: 'New Item',
                text_zh: '新项目',
                text: 'New Item'
            });
            renderHotspots(state.pageEdits[pageNum]);
        }
        
        state.tempBox.remove();
        state.tempBox = null;
    }
}

// ============ OCR ============

async function runOCRCurrentPage() {
    if (!el.pageImage.src) return;
    
    const statusEl = document.getElementById('ai-status-text');
    statusEl.textContent = 'Scanning...';
    el.ocrStatus.textContent = 'Processing image...';
    
    try {
        // Convert page image to base64
        const imageData = el.pageImage.src.split(',')[1];
        
        const response = await fetch(`${OCR_API}/ocr`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        
        const result = await response.json();
        console.log('OCR result:', result);
        
        const paragraphs = result.paragraphs || [];
        el.ocrStatus.textContent = `Found ${paragraphs.length} text blocks`;
        
        if (paragraphs.length > 0) {
            // Convert OCR results to hotspots and store in session state
            const pageNum = state.currentPage + 1;
            state.pageEdits[pageNum] = paragraphs.map(p => ({
                x: p.bbox.x0,
                y: p.bbox.y0,
                width: p.bbox.x1 - p.bbox.x0,
                height: p.bbox.y1 - p.bbox.y0,
                text: p.text,
                translatedText: ''
            }));
            
            renderHotspots(state.pageEdits[pageNum]);
            showToast(`Found ${paragraphs.length} text regions`);
        }
        
        statusEl.textContent = 'AI Scan Page';
    } catch (err) {
        console.error('OCR failed:', err);
        el.ocrStatus.textContent = 'OCR failed: ' + err.message;
        statusEl.textContent = 'AI Scan Page';
    }
}

// ============ EDITOR FUNCTIONS ============


function toggleEditorMode() {
    state.editorMode = !state.editorMode;
    el.editorPanel.classList.toggle('hidden', !state.editorMode);
    el.editorLayer.classList.toggle('hidden', !state.editorMode);
    
    if (state.editorMode) {
        // Redraw with list
        const pageNum = state.currentPage + 1;
        loadPageHotspots(state.currentBook?.id, pageNum);
    }
}

function clearHotspots() {
    const pageNum = state.currentPage + 1;
    state.pageEdits[pageNum] = [];
    renderHotspots([]);
    showToast('Hotspots cleared for this page');
}

async function translateAllHotspots() {
    const pageNum = state.currentPage + 1;
    const hotspots = state.pageEdits[pageNum] || [];
    
    if (hotspots.length === 0) {
        showToast('Nothing to translate. Run AI Scan first.');
        return;
    }

    const statusEl = document.getElementById('ai-status-text');
    const originalText = statusEl.textContent;
    statusEl.textContent = 'Translating...';
    
    showToast(`Translating ${hotspots.length} items...`);
    
    for (let hs of hotspots) {
        try {
            const textToTranslate = hs.text_en || hs.text;
            if (!textToTranslate) continue;
            
            const from = 'en';
            const to = 'zh-CN';
            
            // Backend expects GET with params: translate?text=...&from=...&to=...
            const url = `${API_BASE}/api/translate?text=${encodeURIComponent(textToTranslate)}&from=${from}&to=${to}`;
            
            const response = await fetch(url);
            if (!response.ok) throw new Error('Translation API failed');
            
            const result = await response.json();
            hs.text_zh = result.translatedText;
            hs.translatedText = result.translatedText;
            
            console.log(`Translated: ${textToTranslate} -> ${hs.text_zh}`);
        } catch (err) {
            console.error('Translation failed for item:', err);
        }
    }
    
    renderHotspots(hotspots);
    statusEl.textContent = originalText;
    showToast('Translation complete');
}

async function saveHotspotsCurrentPage() {
    if (!state.currentBook) return;
    const pageNum = state.currentPage + 1;
    const hotspots = state.pageEdits[pageNum];
    
    if (!hotspots) {
        showToast('No changes to save.');
        return;
    }

    try {
        showToast('Saving to cloud...');
        
        // Map frontend fields back to Backend Entity format
        const hotspotsData = hotspots.map(hs => ({
            x: hs.x,
            y: hs.y,
            width: hs.width || hs.w,
            height: hs.height || hs.h,
            textEn: hs.text_en || hs.text,
            textZh: hs.text_zh || hs.translatedText
        }));

        const response = await fetch(`${API_BASE}/api/books/${state.currentBook.id}/sync-page?pageNumber=${pageNum}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(hotspotsData)
        });

        if (!response.ok) throw new Error('Cloud save failed');
        
        showToast('Page saved to cloud successfully!');
        
        // Refresh book data from server to keep sync
        const bookResponse = await fetch(`${API_BASE}/api/books/${state.currentBook.id}`);
        state.currentBook = await bookResponse.json();
        
        // Clear session edit for this page as it's now "saved"
        delete state.pageEdits[pageNum];
        
    } catch (err) {
        console.error('Save failed:', err);
        showToast('Save failed: ' + err.message);
    }
}

function restartOCR() {
    showToast('Restarting OCR engine...');
    runOCRCurrentPage();
}

function copyHotspotsJSON() {
    const json = JSON.stringify(state.tempHotspots, null, 2);
    navigator.clipboard.writeText(json);
    showToast('JSON copied to clipboard');
}

// ============ LANGUAGE & VOICE ============


function toggleLanguage() {
    state.currentLanguage = state.currentLanguage === 'en' ? 'cn' : 'en';
    document.getElementById('lang-label').textContent = state.currentLanguage === 'en' ? 'English' : '中文';
}

async function loadVoices() {
    return new Promise((resolve) => {
        let voices = speechSynthesis.getVoices();
        
        const populate = () => {
            voices = speechSynthesis.getVoices();
            if (voices.length === 0) return false;

            const enVoices = voices.filter(v => v.lang.startsWith('en'));
            const cnVoices = voices.filter(v => v.lang.startsWith('zh') || v.lang.startsWith('cn'));

            if (el.voiceSelectEn) {
                el.voiceSelectEn.innerHTML = enVoices.map(v => `<option value="${v.name}">${v.name}</option>`).join('');
                state.voices.en = enVoices[0] || voices[0];
            }
            if (el.voiceSelectCn) {
                el.voiceSelectCn.innerHTML = cnVoices.map(v => `<option value="${v.name}">${v.name}</option>`).join('');
                state.voices.cn = cnVoices[0] || voices[0];
            }
            
            console.log(`Loaded ${enVoices.length} EN voices and ${cnVoices.length} CN voices`);
            return true;
        };

        if (populate()) {
            resolve();
        } else {
            speechSynthesis.onvoiceschanged = () => {
                if (populate()) resolve();
            };
        }
    });
}

function playCurrentHotspot() {
    if (!state.currentHotspot) return;
    stopVoice();
    
    // Use normalization utility for TTS
    const normalized = normalizeHotspot(state.currentHotspot);
    const text = state.currentLanguage === 'en' ? normalized.text_en : normalized.text_zh;
    
    if (!text) return;
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = state.currentLanguage === 'en' ? state.voices.en : state.voices.cn;
    speechSynthesis.speak(utterance);
}

function stopVoice() {
    speechSynthesis.cancel();
}

function selectHotspot(hotspot) {
    state.currentHotspot = hotspot;
    playCurrentHotspot();
}

// ============ UTILITIES ============

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 3000);
}




