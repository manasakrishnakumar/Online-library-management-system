package com.library.book;

import jakarta.persistence.*;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import java.util.List;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@SpringBootApplication
public class BookServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(BookServiceApplication.class, args);
    }

    /** Loads the sample catalogue (books.csv, '|' separated) on first start. */
    @Bean
    CommandLineRunner seed(BookRepository repo) {
        return args -> {
            if (repo.count() > 0) return;
            try (var in = BookServiceApplication.class.getResourceAsStream("/books.csv");
                 var rd = new java.io.BufferedReader(new java.io.InputStreamReader(in, java.nio.charset.StandardCharsets.UTF_8))) {
                rd.lines().skip(1).filter(l -> !l.isBlank()).forEach(l -> {
                    String[] c = l.split("[|]");
                    repo.save(new Book(c[0], c[1], c[2], c[3], Integer.parseInt(c[4].trim())));
                });
            }
        };
    }
}

@Entity
class Book {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @NotBlank private String title;
    @NotBlank private String author;
    @NotBlank @Column(unique = true) private String isbn;
    private String category;
    @Min(1) private int totalCopies;
    private int availableCopies;

    protected Book() {}
    Book(String title, String author, String isbn, String category, int totalCopies) {
        this.title = title; this.author = author; this.isbn = isbn; this.category = category;
        this.totalCopies = totalCopies; this.availableCopies = totalCopies;
    }

    public Long getId() { return id; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getAuthor() { return author; }
    public void setAuthor(String author) { this.author = author; }
    public String getIsbn() { return isbn; }
    public void setIsbn(String isbn) { this.isbn = isbn; }
    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }
    public int getTotalCopies() { return totalCopies; }
    public void setTotalCopies(int totalCopies) { this.totalCopies = totalCopies; }
    public int getAvailableCopies() { return availableCopies; }
    public void setAvailableCopies(int availableCopies) { this.availableCopies = availableCopies; }
}

interface BookRepository extends JpaRepository<Book, Long> {
    List<Book> findByTitleContainingIgnoreCaseOrAuthorContainingIgnoreCase(String title, String author);
}

@RestController
@RequestMapping("/api/books")
class BookController {
    private final BookRepository repo;

    BookController(BookRepository repo) { this.repo = repo; }

    @GetMapping
    List<Book> all() { return repo.findAll(); }

    @GetMapping("/search")
    List<Book> search(@RequestParam String q) {
        return repo.findByTitleContainingIgnoreCaseOrAuthorContainingIgnoreCase(q, q);
    }

    @GetMapping("/{id}")
    Book get(@PathVariable Long id) { return find(id); }

    @PostMapping @ResponseStatus(HttpStatus.CREATED)
    Book create(@Valid @RequestBody Book b) {
        b.setAvailableCopies(b.getTotalCopies());
        return repo.save(b);
    }

    @PutMapping("/{id}")
    Book update(@PathVariable Long id, @Valid @RequestBody Book in) {
        Book b = find(id);
        int onLoan = b.getTotalCopies() - b.getAvailableCopies();
        b.setTitle(in.getTitle()); b.setAuthor(in.getAuthor()); b.setIsbn(in.getIsbn()); b.setCategory(in.getCategory());
        b.setTotalCopies(in.getTotalCopies());
        b.setAvailableCopies(Math.max(0, in.getTotalCopies() - onLoan));
        return repo.save(b);
    }

    @DeleteMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT)
    void delete(@PathVariable Long id) { repo.delete(find(id)); }

    /** Called by lending-service when a book is issued. */
    @PutMapping("/{id}/borrow")
    Book borrow(@PathVariable Long id) {
        Book b = find(id);
        if (b.getAvailableCopies() < 1) throw new ResponseStatusException(HttpStatus.CONFLICT, "No copies available");
        b.setAvailableCopies(b.getAvailableCopies() - 1);
        return repo.save(b);
    }

    /** Called by lending-service when a book is returned. */
    @PutMapping("/{id}/return")
    Book giveBack(@PathVariable Long id) {
        Book b = find(id);
        if (b.getAvailableCopies() < b.getTotalCopies()) b.setAvailableCopies(b.getAvailableCopies() + 1);
        return repo.save(b);
    }

    private Book find(Long id) {
        return repo.findById(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Book not found"));
    }
}
