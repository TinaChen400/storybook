package com.storybook.entity

import jakarta.persistence.*
import java.time.LocalDateTime

@Entity
@Table(name = "vocabulary")
class Vocabulary(
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    val id: Int = 0,

    @Column(nullable = false, columnDefinition = "TEXT")
    var word: String = "",

    @Column(columnDefinition = "TEXT")
    var translation: String? = null,

    @Column(name = "example_sentence", columnDefinition = "TEXT")
    var exampleSentence: String? = null,

    @Column(name = "difficulty_level")
    var difficultyLevel: Int = 1,

    @Column(name = "source_book_id", length = 36)
    var sourceBookId: String? = null,

    @Column(name = "last_practiced")
    var lastPracticed: LocalDateTime? = null,

    @Column(name = "created_at", updatable = false, insertable = false)
    var createdAt: LocalDateTime? = null
)
