package com.library.lending;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpStatus;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.support.TransactionCallback;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.server.ResponseStatusException;

class LendingServiceTest {
    private final LoanRepository loans = mock(LoanRepository.class);
    private final LoanEventRepository events = mock(LoanEventRepository.class);
    private final OutboxRepository outbox = mock(OutboxRepository.class);
    private final RemoteGateway remote = mock(RemoteGateway.class);
    private final TransactionTemplate tx = mock(TransactionTemplate.class);
    private final Map<Long, Loan> db = new HashMap<>();
    private LendingService service;

    @BeforeEach
    @SuppressWarnings("unchecked")
    void setUp() {
        // run transaction callbacks inline and keep loans in a map that plays the lending database
        when(tx.execute(any())).thenAnswer(i -> ((TransactionCallback<Object>) i.getArgument(0)).doInTransaction(null));
        when(loans.save(any(Loan.class))).thenAnswer(i -> {
            Loan l = i.getArgument(0);
            if (l.getId() == null) ReflectionTestUtils.setField(l, "id", (long) (db.size() + 1));
            db.put(l.getId(), l);
            return l;
        });
        when(loans.findById(any())).thenAnswer(i -> Optional.ofNullable(db.get(i.<Long>getArgument(0))));
        when(remote.member(1L)).thenReturn(new MemberView(1L, "Asha", true));
        service = new LendingService(loans, events, outbox, remote, tx, new ObjectMapper(), new SimpleMeterRegistry(), 14);
    }

    @Test
    void inactiveMemberCannotBorrow() {
        when(remote.member(2L)).thenReturn(new MemberView(2L, "Ravi", false));
        ResponseStatusException e = assertThrows(ResponseStatusException.class, () -> service.issue(new IssueRequest(5L, 2L)));
        assertEquals(HttpStatus.CONFLICT, e.getStatusCode());
        verify(loans, never()).save(any(Loan.class));
    }

    @Test
    void successfulSagaIssuesLoanAndWritesOutboxEvent() {
        when(remote.borrow(eq(5L), any())).thenReturn(new BookView(5L, "Building Microservices", 1));
        Loan loan = service.issue(new IssueRequest(5L, 1L));
        assertEquals("ISSUED", loan.getStatus());
        assertEquals(LocalDate.now().plusDays(14), loan.getDueDate());
        verify(remote).borrow(5L, "loan-1-borrow");
        ArgumentCaptor<OutboxEvent> ev = ArgumentCaptor.forClass(OutboxEvent.class);
        verify(outbox).save(ev.capture());
        assertEquals("loan.issued", ev.getValue().getRoutingKey());
    }

    @Test
    void rejectionByBookServiceFailsTheLoanWithoutOutboxEvent() {
        when(remote.borrow(eq(5L), any())).thenThrow(new ResponseStatusException(HttpStatus.CONFLICT, "No copies available"));
        assertThrows(ResponseStatusException.class, () -> service.issue(new IssueRequest(5L, 1L)));
        assertEquals("FAILED", db.get(1L).getStatus());
        assertEquals("No copies available", db.get(1L).getFailureReason());
        verify(outbox, never()).save(any(OutboxEvent.class));
    }

    @Test
    void unknownOutcomeLeavesLoanPendingAndRecoveryFinishesIt() {
        when(remote.borrow(eq(5L), any())).thenThrow(new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "down"));
        Loan loan = service.issue(new IssueRequest(5L, 1L));
        assertEquals("PENDING", loan.getStatus());
        verify(remote, never()).giveBack(any(), any());

        reset(remote);                                           // book-service is back
        when(remote.borrow(eq(5L), any())).thenReturn(new BookView(5L, "Building Microservices", 1));
        assertEquals("ISSUED", service.advance(1L).getStatus());
        verify(remote).borrow(5L, "loan-1-borrow");              // same idempotency key as the first attempt
    }

    @Test
    void failureWhileRecordingTheLoanReleasesTheReservedCopy() {
        when(remote.borrow(eq(5L), any())).thenReturn(new BookView(5L, "Building Microservices", 1));
        when(outbox.save(any(OutboxEvent.class))).thenThrow(new IllegalStateException("database error"));
        assertThrows(IllegalStateException.class, () -> service.issue(new IssueRequest(5L, 1L)));
        verify(remote).giveBack(5L, "loan-1-compensate");        // compensation step of the saga
        assertEquals("FAILED", db.get(1L).getStatus());
    }

    @Test
    void returnMarksLoanReturnedAndWritesOutboxEvent() {
        when(remote.borrow(eq(5L), any())).thenReturn(new BookView(5L, "Building Microservices", 1));
        service.issue(new IssueRequest(5L, 1L));
        Loan result = service.giveBack(1L);
        assertEquals("RETURNED", result.getStatus());
        verify(remote).giveBack(5L, "loan-1-return");
        verify(outbox, times(2)).save(any(OutboxEvent.class));   // issued + returned
    }

    @Test
    void returningTwiceIsRejected() {
        when(remote.borrow(eq(5L), any())).thenReturn(new BookView(5L, "Building Microservices", 1));
        service.issue(new IssueRequest(5L, 1L));
        service.giveBack(1L);
        ResponseStatusException e = assertThrows(ResponseStatusException.class, () -> service.giveBack(1L));
        assertEquals(HttpStatus.CONFLICT, e.getStatusCode());
    }
}
