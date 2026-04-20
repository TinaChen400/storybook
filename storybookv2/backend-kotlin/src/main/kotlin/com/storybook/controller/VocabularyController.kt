package com.storybook.controller

import com.storybook.entity.Vocabulary
import com.storybook.repository.VocabularyRepository
import org.springframework.web.bind.annotation.*

@RestController
@CrossOrigin(origins = ["*"]) // 直接允许所有来源访问，先打通链路！
@RequestMapping("/api/vocabulary")
class VocabularyController(private val vocabularyRepository: VocabularyRepository) {

    @GetMapping
    fun getAll(): List<Vocabulary> = vocabularyRepository.findAll()

    @PostMapping
    fun addWord(@RequestBody vocab: Vocabulary): Vocabulary = vocabularyRepository.save(vocab)
}
