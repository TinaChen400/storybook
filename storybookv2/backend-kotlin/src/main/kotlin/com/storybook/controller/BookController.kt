package com.storybook.controller

import com.storybook.entity.Book
import com.storybook.entity.Page
import com.storybook.entity.Hotspot
import com.storybook.repository.BookRepository
import com.storybook.repository.PageRepository
import com.storybook.repository.HotspotRepository
import org.springframework.web.bind.annotation.*
import org.springframework.web.multipart.MultipartFile
import java.io.File
import java.nio.file.Files
import java.nio.file.Paths
import java.util.*

@RestController
@RequestMapping("/api/books")
class BookController(
    private val bookRepository: BookRepository,
    private val pageRepository: PageRepository,
    private val hotspotRepository: HotspotRepository
) {

    @GetMapping
    fun getAllBooks(): List<Book> = bookRepository.findAll()

    @GetMapping("/{id}")
    fun getBookDetail(@PathVariable id: String): Book = bookRepository.findById(id).orElseThrow { RuntimeException("Book not found") }

    @PostMapping
    fun createBook(@RequestBody book: Book): Book = bookRepository.save(book)

    @PostMapping("/{bookId}/sync-page")
    fun syncPageHotspots(
        @PathVariable bookId: String,
        @RequestBody hotspotsData: List<Hotspot>,
        @RequestParam pageNumber: Int
    ): Page {
        val book = bookRepository.findById(bookId).orElseThrow { RuntimeException("Book not found") }
        val page = pageRepository.findByBookIdAndPageNumber(bookId, pageNumber) ?: Page(book = book, pageNumber = pageNumber).also { pageRepository.save(it) }
        hotspotRepository.deleteByPageId(page.id)
        hotspotsData.forEach { it.page = page; hotspotRepository.save(it) }
        return pageRepository.findById(page.id).get()
    }

    @PostMapping("/{id}/rotation")
    fun updateRotation(@PathVariable id: String, @RequestParam angle: Int): Book {
        val book = bookRepository.findById(id).orElseThrow { RuntimeException("Book not found") }
        book.rotation = angle
        return bookRepository.save(book)
    }

    @PostMapping("/upload")
    fun uploadBook(@RequestParam("file") file: MultipartFile): Book {
        val uploadDir = System.getenv("UPLOAD_DIR") ?: if (File("/app").exists()) "/app/uploads" else "uploads"
        val folder = File(uploadDir)
        if (!folder.exists()) folder.mkdirs()
        val fileName = "${UUID.randomUUID()}_${file.originalFilename}"
        val path = Paths.get(uploadDir, fileName)
        Files.copy(file.inputStream, path)
        val newBook = Book(title = file.originalFilename ?: "Unknown", pdfPath = "/uploads/$fileName")
        return bookRepository.save(newBook)
    }

    @DeleteMapping("/{id}")
    fun deleteBook(@PathVariable id: String): Map<String, Any> {
        val book = bookRepository.findById(id).orElseThrow { RuntimeException("Book not found") }
        bookRepository.deleteById(id)
        return mapOf("success" to true)
    }
}