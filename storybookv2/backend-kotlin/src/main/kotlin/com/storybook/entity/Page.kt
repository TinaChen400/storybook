package com.storybook.entity

import jakarta.persistence.*
import java.util.UUID

@Entity
@Table(name = "pages")
class Page(
    @Id
    @Column(length = 36)
    var id: String = UUID.randomUUID().toString(),

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "book_id", nullable = false, columnDefinition = "VARCHAR(36)")
    @com.fasterxml.jackson.annotation.JsonBackReference
    var book: Book? = null,

    @OneToMany(mappedBy = "page", cascade = [CascadeType.ALL], fetch = FetchType.LAZY, orphanRemoval = true)
    @com.fasterxml.jackson.annotation.JsonManagedReference
    var hotspots: MutableList<Hotspot> = mutableListOf(),

    @Column(name = "page_number", nullable = false)
    var pageNumber: Int = 0,

    @Column(name = "image_url")
    var imageUrl: String? = null,

    @Column(name = "image_path")
    var imagePath: String? = null
)
