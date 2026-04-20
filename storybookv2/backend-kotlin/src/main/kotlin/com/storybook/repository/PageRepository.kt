package com.storybook.repository

import com.storybook.entity.Page
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository

@Repository
interface PageRepository : JpaRepository<Page, String> {
    fun findByBookIdAndPageNumber(bookId: String, pageNumber: Int): Page?
}
