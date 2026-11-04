package com.library.fine;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

class LoanReturnedListenerTest {
    private final FineRepository fines = mock(FineRepository.class);
    private final RabbitTemplate rabbit = mock(RabbitTemplate.class);
    private final LoanReturnedListener listener = new LoanReturnedListener(fines, rabbit, new ObjectMapper(), 2.0);

    private String event(String due, String returned) {
        return "{\"loanId\":1,\"memberId\":2,\"memberName\":\"Asha\",\"bookTitle\":\"Book\",\"dueDate\":\"" + due + "\",\"returnDate\":\"" + returned + "\"}";
    }

    @Test
    void lateReturnCreatesFineAndPublishesEvent() throws Exception {
        listener.onReturned(event("2026-01-01", "2026-01-05"));
        ArgumentCaptor<Fine> captor = ArgumentCaptor.forClass(Fine.class);
        verify(fines).save(captor.capture());
        assertEquals(4, captor.getValue().getDaysOverdue());
        assertEquals(0, captor.getValue().getAmount().compareTo(new java.math.BigDecimal("8")));
        verify(rabbit).convertAndSend(eq("library.events"), eq("fine.assessed"), any(Object.class));
    }

    @Test
    void onTimeReturnCreatesNoFine() throws Exception {
        listener.onReturned(event("2026-01-05", "2026-01-05"));
        verify(fines, never()).save(any(Fine.class));
    }
}
