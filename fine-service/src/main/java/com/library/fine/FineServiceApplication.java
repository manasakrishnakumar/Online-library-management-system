package com.library.fine;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.context.annotation.Bean;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@SpringBootApplication
@EnableFeignClients
public class FineServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(FineServiceApplication.class, args);
    }

    @Bean TopicExchange libraryEvents() { return new TopicExchange("library.events"); }
    @Bean Queue returnedQueue() { return new Queue("fine.loan-returned", true); }
    @Bean Binding returnedBinding(Queue returnedQueue, TopicExchange libraryEvents) {
        return BindingBuilder.bind(returnedQueue).to(libraryEvents).with("loan.returned");
    }
}

/** Reacts to loan.returned events: if the book came back late, a fine is assessed without anyone calling this service. */
@Component
class LoanReturnedListener {
    private static final Logger log = LoggerFactory.getLogger(LoanReturnedListener.class);
    private final FineRepository fines;
    private final RabbitTemplate rabbit;
    private final ObjectMapper mapper;
    private final BigDecimal perDay;
    private final io.micrometer.core.instrument.MeterRegistry meters;

    LoanReturnedListener(FineRepository fines, RabbitTemplate rabbit, ObjectMapper mapper, io.micrometer.core.instrument.MeterRegistry meters,
                         @Value("${library.fine-per-day:2.0}") double perDay) {
        this.fines = fines; this.rabbit = rabbit; this.mapper = mapper; this.meters = meters; this.perDay = BigDecimal.valueOf(perDay);
    }

    @RabbitListener(queues = "fine.loan-returned")
    void onReturned(String json) throws Exception {
        JsonNode n = mapper.readTree(json);
        long loanId = n.get("loanId").asLong();
        long days = ChronoUnit.DAYS.between(LocalDate.parse(n.get("dueDate").asText()), LocalDate.parse(n.get("returnDate").asText()));
        if (days <= 0 || fines.findByLoanId(loanId).isPresent()) return;
        BigDecimal amount = perDay.multiply(BigDecimal.valueOf(days));
        fines.save(new Fine(loanId, n.get("memberId").asLong(), days, amount));
        log.info("Fine of {} assessed for loan {}", amount, loanId);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("loanId", loanId);
        out.put("memberId", n.get("memberId").asLong());
        out.put("memberName", n.get("memberName").asText());
        out.put("bookTitle", n.get("bookTitle").asText());
        out.put("daysOverdue", days);
        out.put("amount", amount);
        rabbit.convertAndSend("library.events", "fine.assessed", mapper.writeValueAsString(out), m -> {
            m.getMessageProperties().setMessageId("fine-" + loanId);
            return m;
        });
        meters.counter("library.fines.assessed").increment();
        meters.counter("library.fines.amount").increment(amount.doubleValue());
    }
}

record LoanView(Long id, Long memberId, LocalDate dueDate, LocalDate returnDate, String status) {}

@FeignClient(name = "lending-service")
interface LendingClient {
    @GetMapping("/api/loans/{id}") LoanView loan(@PathVariable("id") Long id);
}

@Service
class LendingGateway {
    private final LendingClient client;

    LendingGateway(LendingClient client) { this.client = client; }

    @CircuitBreaker(name = "lendingService", fallbackMethod = "fallback")
    LoanView loan(Long id) { return client.loan(id); }

    LoanView fallback(Long id, Throwable t) {
        if (t instanceof feign.FeignException fe && fe.status() == 404) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Loan not found");
        }
        throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "lending-service is unavailable, try again later");
    }
}

@Entity
class Fine {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(unique = true) private Long loanId;
    private Long memberId;
    private long daysOverdue;
    private BigDecimal amount;
    private boolean paid;

    protected Fine() {}
    Fine(Long loanId, Long memberId, long daysOverdue, BigDecimal amount) {
        this.loanId = loanId; this.memberId = memberId; this.daysOverdue = daysOverdue; this.amount = amount;
    }

    public Long getId() { return id; }
    public Long getLoanId() { return loanId; }
    public Long getMemberId() { return memberId; }
    public long getDaysOverdue() { return daysOverdue; }
    public BigDecimal getAmount() { return amount; }
    public boolean isPaid() { return paid; }
    void update(long days, BigDecimal amt) { this.daysOverdue = days; this.amount = amt; }
    void markPaid() { this.paid = true; }
}

interface FineRepository extends JpaRepository<Fine, Long> {
    List<Fine> findByMemberId(Long memberId);
    java.util.Optional<Fine> findByLoanId(Long loanId);
}

@RestController
@RequestMapping("/api/fines")
class FineController {
    private final FineRepository fines;
    private final LendingGateway lending;
    private final BigDecimal perDay;

    FineController(FineRepository fines, LendingGateway lending, @Value("${library.fine-per-day:2.0}") double perDay) {
        this.fines = fines; this.lending = lending; this.perDay = BigDecimal.valueOf(perDay);
    }

    @GetMapping List<Fine> all() { return fines.findAll(); }

    @GetMapping("/member/{memberId}")
    List<Fine> byMember(@PathVariable Long memberId) { return fines.findByMemberId(memberId); }

    /** Fine = days past due date x daily rate. Works for returned and still-issued loans. */
    @PostMapping("/calculate/{loanId}")
    Fine calculate(@PathVariable Long loanId) {
        LoanView loan = lending.loan(loanId);
        LocalDate end = loan.returnDate() != null ? loan.returnDate() : LocalDate.now();
        long days = Math.max(0, ChronoUnit.DAYS.between(loan.dueDate(), end));
        if (days == 0) throw new ResponseStatusException(HttpStatus.CONFLICT, "Loan is not overdue, no fine");
        BigDecimal amount = perDay.multiply(BigDecimal.valueOf(days));
        Fine fine = fines.findByLoanId(loanId).orElseGet(() -> new Fine(loanId, loan.memberId(), days, amount));
        fine.update(days, amount);
        return fines.save(fine);
    }

    @PutMapping("/{id}/pay")
    Fine pay(@PathVariable Long id) {
        Fine f = fines.findById(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Fine not found"));
        f.markPaid();
        return fines.save(f);
    }
}
