package com.storybook.entity

import jakarta.persistence.*

@Entity
@Table(name = "hotspots")
class Hotspot(
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    val id: Int = 0,

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "page_id", nullable = false, columnDefinition = "VARCHAR(36)")
    @com.fasterxml.jackson.annotation.JsonBackReference
    var page: Page? = null,

    var x: Double = 0.0,
    var y: Double = 0.0,
    var width: Double = 0.0,
    var height: Double = 0.0,

    @Column(name = "text_en", columnDefinition = "TEXT")
    var textEn: String? = null,

    @Column(name = "text_zh", columnDefinition = "TEXT")
    var textZh: String? = null,

    @Column(name = "interpret_en", columnDefinition = "TEXT")
    var interpretEn: String? = null,
    
    @Column(name = "interpret_zh", columnDefinition = "TEXT")
    var interpretZh: String? = null
)
