package com.library.book;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

class BookControllerTest {
    private final BookRepository repo = mock(BookRepository.class);
    private final StockOpRepository ops = mock(StockOpRepository.class);
    private final BookController controller = new BookController(repo, ops);

    private Book book(int total) {
        Book b = new Book("Clean Code", "Robert C. Martin", "123", "Software", total);
        when(repo.findById(1L)).thenReturn(Optional.of(b));
        when(repo.save(any(Book.class))).thenAnswer(i -> i.getArgument(0));
        return b;
    }

    @Test
    void borrowReducesAvailableCopies() {
        book(2);
        assertEquals(1, controller.borrow(1L, null).getAvailableCopies());
    }

    @Test
    void borrowFailsWhenNoCopiesLeft() {
        book(1);
        controller.borrow(1L, null);
        ResponseStatusException e = assertThrows(ResponseStatusException.class, () -> controller.borrow(1L, null));
        assertEquals(HttpStatus.CONFLICT, e.getStatusCode());
    }

    @Test
    void returnNeverExceedsTotalCopies() {
        book(2);
        assertEquals(2, controller.giveBack(1L, null).getAvailableCopies());
    }

    @Test
    void repeatedIdempotencyKeyDoesNotChangeStockTwice() {
        book(3);
        when(ops.existsById("loan-1-borrow")).thenReturn(false, true);
        assertEquals(2, controller.borrow(1L, "loan-1-borrow").getAvailableCopies());
        assertEquals(2, controller.borrow(1L, "loan-1-borrow").getAvailableCopies());
    }

    @Test
    void pageCapsTheSizeAndReturnsTotals() {
        Book b = new Book("The Hobbit", "J.R.R. Tolkien", "618260307", "Classic", 5);
        when(repo.searchPage(eq("tolkien"), any(Pageable.class))).thenReturn(new PageImpl<>(List.of(b), PageRequest.of(0, 100), 250));
        Map<String, Object> r = controller.page("  tolkien ", 0, 5000);
        ArgumentCaptor<Pageable> pageable = ArgumentCaptor.forClass(Pageable.class);
        verify(repo).searchPage(eq("tolkien"), pageable.capture());
        assertEquals(100, pageable.getValue().getPageSize());
        assertEquals(250L, r.get("total"));
        assertEquals(3, r.get("pages"));
    }

    @Test
    void negativePageNumberIsTreatedAsFirstPage() {
        when(repo.searchPage(any(), any(Pageable.class))).thenReturn(new PageImpl<>(List.of(), PageRequest.of(0, 24), 0));
        Map<String, Object> r = controller.page("", -4, 24);
        assertEquals(0, r.get("page"));
        assertEquals(1, r.get("pages"));
    }

    @Test
    void statsComeFromTheDatabaseTotals() {
        BookStats st = mock(BookStats.class);
        when(st.getTitles()).thenReturn(10000L);
        when(st.getTotalCopies()).thenReturn(30000L);
        when(st.getAvailableCopies()).thenReturn(29996L);
        when(repo.stats()).thenReturn(st);
        Map<String, Object> r = controller.stats();
        assertEquals(10000L, r.get("titles"));
        assertEquals(29996L, r.get("availableCopies"));
    }

    @Test
    void unknownBookIsNotFound() {
        when(repo.findById(9L)).thenReturn(Optional.empty());
        ResponseStatusException e = assertThrows(ResponseStatusException.class, () -> controller.get(9L));
        assertEquals(HttpStatus.NOT_FOUND, e.getStatusCode());
    }
}
