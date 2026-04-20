package com.storybook.controller

import org.springframework.web.bind.annotation.*
import org.springframework.web.client.RestTemplate
import java.net.URLEncoder

@RestController
@RequestMapping("/api/translate")
@CrossOrigin("*")
class TranslationController {

    private val restTemplate = RestTemplate()
    // MyMemory free tier hard limit is 500 chars per request
    private val CHUNK_SIZE = 450

    @GetMapping
    fun translate(
        @RequestParam text: String,
        @RequestParam from: String = "en",
        @RequestParam to: String = "zh-CN"
    ): Map<String, String> {
        return try {
            val translatedText = if (text.length <= CHUNK_SIZE) {
                translateChunk(text, from, to)
            } else {
                // Split at sentence boundaries (. ! ?\n) and translate each chunk
                val chunks = splitIntoChunks(text, CHUNK_SIZE)
                chunks.joinToString(" ") { translateChunk(it, from, to) }
            }
            mapOf("translatedText" to translatedText)
        } catch (e: Exception) {
            mapOf("translatedText" to "[Translation Error: ${e.message}]")
        }
    }

    private fun translateChunk(text: String, from: String, to: String): String {
        val encodedText = URLEncoder.encode(text, "UTF-8")
        val url = "https://api.mymemory.translated.net/get?q=$encodedText&langpair=$from|$to"
        val response = restTemplate.getForObject(url, Map::class.java)
        val responseData = response?.get("responseData") as? Map<*, *>
        return responseData?.get("translatedText") as? String ?: text
    }

    private fun splitIntoChunks(text: String, maxSize: Int): List<String> {
        val sentences = text.split(Regex("(?<=[.!?\\n])\\s+"))
        val chunks = mutableListOf<String>()
        val current = StringBuilder()
        for (sentence in sentences) {
            if (current.length + sentence.length + 1 > maxSize) {
                if (current.isNotEmpty()) { chunks.add(current.toString().trim()); current.clear() }
                // If a single sentence is still too long, force-split it
                if (sentence.length > maxSize) {
                    sentence.chunked(maxSize).forEach { chunks.add(it) }
                } else {
                    current.append(sentence).append(" ")
                }
            } else {
                current.append(sentence).append(" ")
            }
        }
        if (current.isNotEmpty()) chunks.add(current.toString().trim())
        return chunks
    }
}
