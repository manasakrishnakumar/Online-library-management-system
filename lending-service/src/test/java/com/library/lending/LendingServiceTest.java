package com.library.lending;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.time.LocalDate;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

class LendingServiceTest {
    private final LoanRepository loans = mock(LoanRepository.class);
    private final LoanEventRepository events = mock(LoanEventRepository.class);
    private final RemoteGateway remote = mock(RemoteGateway.class);
    private final ApplicationEventPublisher bus = mock(ApplicationEventPublisher.class);
    private final LendingService service = new LendingService(loans, events, remote, bus, 14);

    @Test
    void inactiveMemberCannotBorrow() {
        when(remote.member(1L)).thenReturn(new MemberView(1L, "Asha", false));
        ResponseStatusException e = assertThrows(ResponseStatusException.class, () -> service.issue(new IssueRequest(5L, 1L)));
        assertEquals(HttpStatus.CONFLICT, e.getStatusCode());
        verify(remote, never()).borrow(any());
    }

    @Test
    void issueSetsDueDateAndPublishesEvent() {
        when(remote.member(1L)).thenReturn(new MemberView(1L, "Asha", true));
        when(remote.borrow(5L)).thenReturn(new BookView(5L, "Building Microservices", 1));
        when(loans.save(any(Loan.class))).thenAnswer(i -> i.getArgument(0));
        Loan loan = service.issue(new IssueRequest(5L, 1L));
        assertEquals(LocalDate.now().plusDays(14), loan.getDueDate());
        assertEquals("ISSUED", loan.getStatus());
        verify(bus).publishEvent(any(LibraryEvent.class));
    }

    @Test
    void returningTwiceIsRejected() {
        Loan loan = new Loan(5L, "Book", 1L, "Asha", LocalDate.now(), LocalDate.now().plusDays(14));
        loan.markReturned(LocalDate.now());
        when(loans.findById(1L)).thenReturn(Optional.of(loan));
        ResponseStatusException e = assertThrows(ResponseStatusException.class, () -> service.giveBack(1L));
        assertEquals(HttpStatus.CONFLICT, e.getStatusCode());
    }

    @Test
    void returnMarksLoanReturnedAndPublishesEvent() {
        Loan loan = new Loan(5L, "Book", 1L, "Asha", LocalDate.now(), LocalDate.now().plusDays(14));
        when(loans.findById(1L)).thenReturn(Optional.of(loan));
        when(loans.save(any(Loan.class))).thenAnswer(i -> i.getArgument(0));
        Loan result = service.giveBack(1L);
        assertEquals("RETURNED", result.getStatus());
        verify(remote).giveBack(5L);
        verify(bus).publishEvent(any(LibraryEvent.class));
    }
}
