package com.storybook.repository

import com.storybook.entity.Vocabulary
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository

@Repository
interface VocabularyRepository : JpaRepository<Vocabulary, Int>
