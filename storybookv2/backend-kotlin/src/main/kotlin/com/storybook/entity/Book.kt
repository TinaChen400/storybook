package com.storybook.entity

import jakarta.persistence.*
import java.time.LocalDateTime
import java.util.UUID

@Entity
@Table(name = "books")
class Book(
    @Id
    @Column(length = 36)
    var id: String = UUID.randomUUID().toString(),

    @Column(nullable = false)
    var title: String = "",

    var author: String? = null,

    @Column(name = "folder_path", columnDefinition = "TEXT")
    var folder: String? = null,

    @Column(name = "cover_url", columnDefinition = "TEXT")
    var cover: String? = null,

    @Column(name = "pdf_path")
    var pdfPath: String? = null,

    @Column(name = "rotation", columnDefinition = "int default 0")
    var rotation: Int = 0,

    @OneToMany(mappedBy = "book", cascade = [CascadeType.ALL], fetch = FetchType.LAZY)
    @com.fasterxml.jackson.annotation.JsonManagedReference
    var pages: MutableList<Page> = mutableListOf(),

    @Column(name = "created_at", insertable = false, updatable = false)
    var createdAt: LocalDateTime? = null
)
