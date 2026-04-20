-- 创建书本表
CREATE TABLE IF NOT EXISTS books (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    cover_url TEXT,
    folder_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建页面表
CREATE TABLE IF NOT EXISTS pages (
    id VARCHAR(36) PRIMARY KEY,
    book_id VARCHAR(36),
    page_number INT,
    image_path TEXT,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- 创建框框（Hotspots）表
CREATE TABLE IF NOT EXISTS hotspots (
    id VARCHAR(36) PRIMARY KEY,
    page_id VARCHAR(36),
    rect_json TEXT NOT NULL,
    text_en TEXT,
    text_zh TEXT,
    ai_interpretation_en TEXT,
    ai_interpretation_zh TEXT, -- 重点放在本句解读
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
);

-- 创建生词本表 (经过精细化设计的学习版)
CREATE TABLE IF NOT EXISTS vocabulary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word VARCHAR(100) NOT NULL,
    syllables VARCHAR(100),            -- 音节划分，如 beau-ti-ful
    audio_url VARCHAR(255),           -- 单词发音链接
    
    context_pos VARCHAR(50),          -- 在当前句子中的具体词性
    derivative_forms TEXT,            -- 其它词性样式 (存为 JSON, 如 {"n": "...", "adj": "..."})
    
    definition_en TEXT,               -- 针对本句意思的英文释义
    definition_zh TEXT,               -- 针对本句意思的中文释义
    
    source_sentence_en TEXT,          -- 书中的原始英文句子
    source_sentence_zh TEXT,          -- 书中原文的翻译
    
    ai_mnemonic_zh TEXT,              -- 针对本句意思的 AI 助记法
    
    mastery_level INT DEFAULT 0,      -- 掌握度 (0-5)
    source_book_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
