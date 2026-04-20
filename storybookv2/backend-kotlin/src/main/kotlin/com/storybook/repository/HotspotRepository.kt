package com.storybook.repository

import com.storybook.entity.Hotspot
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository
import jakarta.transaction.Transactional

@Repository
interface HotspotRepository : JpaRepository<Hotspot, Int> {
    @Transactional
    fun deleteByPageId(pageId: String)
}
