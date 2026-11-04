package com.library.book;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

class BookControllerTest {
    private final BookRepository repo = mock(BookRepository.class);
    private final BookController controller = new BookController(repo);

    private Book book(int total) {
        Book b = new Book("Clean Code", "Robert C. Martin", "123", "Software", total);
        when(repo.findById(1L)).thenReturn(Optional.of(b));
        when(repo.save(any(Book.class))).thenAnswer(i -> i.getArgument(0));
        return b;
    }

    @Test
    void borrowReducesAvailableCopies() {
        book(2);
        assertEquals(1, controller.borrow(1L).getAvailableCopies());
    }

    @Test
    void borrowFailsWhenNoCopiesLeft() {
        book(1);
        controller.borrow(1L);
        ResponseStatusException e = assertThrows(ResponseStatusException.class, () -> controller.borrow(1L));
        assertEquals(HttpStatus.CONFLICT, e.getStatusCode());
    }

    @Test
    void returnNeverExceedsTotalCopies() {
        book(2);
        assertEquals(2, controller.giveBack(1L).getAvailableCopies());
    }

    @Test
    void unknownBookIsNotFound() {
        when(repo.findById(9L)).thenReturn(Optional.empty());
        ResponseStatusException e = assertThrows(ResponseStatusException.class, () -> controller.get(9L));
        assertEquals(HttpStatus.NOT_FOUND, e.getStatusCode());
    }
}
