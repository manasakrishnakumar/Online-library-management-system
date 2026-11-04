package com.library.lending;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import jakarta.persistence.*;
import java.time.Instant;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.context.annotation.Bean;
import org.springframework.context.event.EventListener;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@SpringBootApplication
@EnableFeignClients
@EnableScheduling
public class LendingServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(LendingServiceApplication.class, args);
    }

    @Bean
    TopicExchange libraryEvents() { return new TopicExchange("library.events"); }
}

/** Minimal views of other services' data: lending only keeps IDs and snapshots, never shares their database. */
record BookView(Long id, String title, int availableCopies) {}
record MemberView(Long id, String name, boolean active) {}

@FeignClient(name = "book-service")
interface BookClient {
    @PutMapping("/api/books/{id}/borrow")
    BookView borrow(@PathVariable("id") Long id, @RequestHeader("Idempotency-Key") String key);

    @PutMapping("/api/books/{id}/return")
    BookView giveBack(@PathVariable("id") Long id, @RequestHeader("Idempotency-Key") String key);
}

@FeignClient(name = "member-service")
interface MemberClient {
    @GetMapping("/api/members/{id}") MemberView get(@PathVariable("id") Long id);
}

/** Loan life cycle: PENDING (saga started) -> ISSUED -> RETURNED, or PENDING -> FAILED. */
@Entity
class Loan {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private Long bookId;
    private String bookTitle;
    private Long memberId;
    private String memberName;
    private LocalDate issueDate;
    private LocalDate dueDate;
    private LocalDate returnDate;
    private String status;
    private String failureReason;
    private Instant createdAt = Instant.now();

    protected Loan() {}
    Loan(Long bookId, Long memberId, String memberName, LocalDate issueDate, LocalDate dueDate) {
        this.bookId = bookId; this.memberId = memberId; this.memberName = memberName;
        this.issueDate = issueDate; this.dueDate = dueDate; this.status = "PENDING";
    }

    public Long getId() { return id; }
    public Long getBookId() { return bookId; }
    public String getBookTitle() { return bookTitle; }
    public Long getMemberId() { return memberId; }
    public String getMemberName() { return memberName; }
    public LocalDate getIssueDate() { return issueDate; }
    public LocalDate getDueDate() { return dueDate; }
    public LocalDate getReturnDate() { return returnDate; }
    public String getStatus() { return status; }
    public String getFailureReason() { return failureReason; }
    public Instant getCreatedAt() { return createdAt; }
    void markIssued(String title) { this.bookTitle = title; this.status = "ISSUED"; }
    void markFailed(String reason) { this.status = "FAILED"; this.failureReason = reason; }
    void shiftBack(int days) { this.issueDate = issueDate.minusDays(days); this.dueDate = dueDate.minusDays(days); }
    void markReturned(LocalDate date) { this.returnDate = date; this.status = "RETURNED"; }
}

/** Append-only event log: a light take on event sourcing; every state change is recorded as an event. */
@Entity
class LoanEvent {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private Long loanId;
    private String type;
    private Instant occurredAt = Instant.now();
    @Column(length = 500) private String details;

    protected LoanEvent() {}
    LoanEvent(Long loanId, String type, String details) {
        this.loanId = loanId; this.type = type; this.details = details;
    }

    public Long getId() { return id; }
    public Long getLoanId() { return loanId; }
    public String getType() { return type; }
    public Instant getOccurredAt() { return occurredAt; }
    public String getDetails() { return details; }
}

/** Transactional outbox: the event is stored in the same transaction as the loan change and relayed to RabbitMQ afterwards. */
@Entity
class OutboxEvent {
    @Id private String id = UUID.randomUUID().toString();
    private String routingKey;
    @Column(length = 2000) private String payload;
    private Instant createdAt = Instant.now();
    private Instant sentAt;

    protected OutboxEvent() {}
    OutboxEvent(String routingKey, String payload) { this.routingKey = routingKey; this.payload = payload; }

    public String getId() { return id; }
    public String getRoutingKey() { return routingKey; }
    public String getPayload() { return payload; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getSentAt() { return sentAt; }
    void markSent() { this.sentAt = Instant.now(); }
}

interface LoanRepository extends JpaRepository<Loan, Long> {
    List<Loan> findByMemberId(Long memberId);
    List<Loan> findByStatusAndCreatedAtBefore(String status, Instant before);
    long countByStatus(String status);
}

interface LoanEventRepository extends JpaRepository<LoanEvent, Long> {
    List<LoanEvent> findByLoanIdOrderByIdAsc(Long loanId);
}

interface OutboxRepository extends JpaRepository<OutboxEvent, String> {
    List<OutboxEvent> findTop50BySentAtIsNullOrderByCreatedAtAsc();
    long countBySentAtIsNull();
}

record IssueRequest(Long bookId, Long memberId) {}

/** Remote calls wrapped in circuit breakers so a failing downstream service degrades gracefully. */
@Service
class RemoteGateway {
    private static final ObjectMapper JSON = new ObjectMapper();
    private final BookClient books;
    private final MemberClient members;

    RemoteGateway(BookClient books, MemberClient members) { this.books = books; this.members = members; }

    @CircuitBreaker(name = "memberService", fallbackMethod = "memberFallback")
    MemberView member(Long id) { return members.get(id); }

    @CircuitBreaker(name = "bookService", fallbackMethod = "borrowFallback")
    BookView borrow(Long id, String key) { return books.borrow(id, key); }

    @CircuitBreaker(name = "bookService", fallbackMethod = "returnFallback")
    BookView giveBack(Long id, String key) { return books.giveBack(id, key); }

    MemberView memberFallback(Long id, Throwable t) { throw unavailable("member-service", t); }
    BookView borrowFallback(Long id, String key, Throwable t) { throw unavailable("book-service", t); }
    BookView returnFallback(Long id, String key, Throwable t) { throw unavailable("book-service", t); }

    private ResponseStatusException unavailable(String svc, Throwable t) {
        if (t instanceof feign.FeignException fe && fe.status() >= 400 && fe.status() < 500) {
            String msg = fe.contentUTF8();
            try {
                JsonNode n = JSON.readTree(msg);
                if (n.hasNonNull("message")) msg = n.get("message").asText();
            } catch (Exception ignored) { /* keep the raw body */ }
            return new ResponseStatusException(HttpStatus.valueOf(fe.status()), msg);
        }
        return new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, svc + " is unavailable, try again later");
    }
}

/**
 * Orchestrated saga for issuing a book. Each step is a local transaction; remote calls are idempotent.
 *   1. save the loan as PENDING                       (lending database)
 *   2. reserve a copy in book-service                 (book database, idempotency key loan-{id}-borrow)
 *   3. mark the loan ISSUED and write the outbox row  (lending database, one transaction)
 * A definite rejection by book-service fails the loan; an unknown outcome (timeout, outage) leaves it PENDING and
 * the recovery job replays step 2 and 3. If step 3 fails after step 2 succeeded, the copy is released (compensation).
 */
@Service
class LendingService {
    private static final Logger log = LoggerFactory.getLogger(LendingService.class);
    private final LoanRepository loans;
    private final LoanEventRepository events;
    private final OutboxRepository outbox;
    private final RemoteGateway remote;
    private final TransactionTemplate tx;
    private final ObjectMapper mapper;
    private final MeterRegistry meters;
    private final int loanDays;

    LendingService(LoanRepository loans, LoanEventRepository events, OutboxRepository outbox, RemoteGateway remote,
                   TransactionTemplate tx, ObjectMapper mapper, MeterRegistry meters,
                   @Value("${library.loan-period-days:14}") int loanDays) {
        this.loans = loans; this.events = events; this.outbox = outbox; this.remote = remote;
        this.tx = tx; this.mapper = mapper; this.meters = meters; this.loanDays = loanDays;
    }

    Loan issue(IssueRequest req) {
        MemberView m = remote.member(req.memberId());
        if (!m.active()) throw new ResponseStatusException(HttpStatus.CONFLICT, "Member is not active");
        LocalDate today = LocalDate.now();
        Loan pending = tx.execute(s -> {
            Loan l = loans.save(new Loan(req.bookId(), m.id(), m.name(), today, today.plusDays(loanDays)));
            events.save(new LoanEvent(l.getId(), "LOAN_REQUESTED", "book " + req.bookId() + " requested by " + m.name()));
            return l;
        });
        return advance(pending.getId());
    }

    /** Runs the remaining saga steps for a PENDING loan; safe to call repeatedly. */
    Loan advance(Long loanId) {
        Loan loan = loans.findById(loanId).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Loan not found"));
        if (!"PENDING".equals(loan.getStatus())) return loan;
        BookView book;
        try {
            book = remote.borrow(loan.getBookId(), "loan-" + loanId + "-borrow");
        } catch (ResponseStatusException e) {
            if (e.getStatusCode().is4xxClientError()) {          // definite rejection: nothing to compensate
                fail(loanId, e.getReason());
                throw e;
            }
            log.warn("Loan {} stays PENDING: {}", loanId, e.getReason());   // unknown outcome: recovery job retries
            return loan;
        }
        try {
            return tx.execute(s -> {
                Loan l = loans.findById(loanId).orElseThrow();
                if (!"PENDING".equals(l.getStatus())) return l;   // another instance already finished it
                l.markIssued(book.title());
                events.save(new LoanEvent(loanId, "BOOK_ISSUED", book.title() + " issued to " + l.getMemberName() + ", due " + l.getDueDate()));
                outbox.save(new OutboxEvent("loan.issued", json(payload(l))));
                meters.counter("library.loans.issued").increment();
                return loans.save(l);
            });
        } catch (RuntimeException e) {                           // step 3 failed after step 2: compensate
            log.error("Finishing loan {} failed, releasing the copy", loanId, e);
            try { remote.giveBack(loan.getBookId(), "loan-" + loanId + "-compensate"); } catch (RuntimeException ignored) { /* retried by recovery */ }
            fail(loanId, "could not record the loan: " + e.getMessage());
            throw e;
        }
    }

    Loan giveBack(Long id) {
        Loan loan = loans.findById(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Loan not found"));
        if ("RETURNED".equals(loan.getStatus())) throw new ResponseStatusException(HttpStatus.CONFLICT, "Already returned");
        if (!"ISSUED".equals(loan.getStatus())) throw new ResponseStatusException(HttpStatus.CONFLICT, "Loan is " + loan.getStatus() + ", not issued");
        remote.giveBack(loan.getBookId(), "loan-" + id + "-return");    // idempotent, so a retry after a failure is safe
        return tx.execute(s -> {
            Loan l = loans.findById(id).orElseThrow();
            if ("RETURNED".equals(l.getStatus())) return l;
            l.markReturned(LocalDate.now());
            events.save(new LoanEvent(id, "BOOK_RETURNED", l.getBookTitle() + " returned on " + l.getReturnDate()));
            outbox.save(new OutboxEvent("loan.returned", json(payload(l))));
            meters.counter("library.loans.returned").increment();
            return loans.save(l);
        });
    }

    private void fail(Long loanId, String reason) {
        tx.execute(s -> {
            Loan l = loans.findById(loanId).orElseThrow();
            l.markFailed(reason);
            events.save(new LoanEvent(loanId, "LOAN_FAILED", reason == null ? "rejected" : reason));
            meters.counter("library.loans.failed").increment();
            return loans.save(l);
        });
    }

    private String json(Map<String, Object> p) {
        try { return mapper.writeValueAsString(p); } catch (Exception e) { throw new IllegalStateException(e); }
    }

    private Map<String, Object> payload(Loan l) {
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("loanId", l.getId());
        p.put("bookId", l.getBookId());
        p.put("bookTitle", l.getBookTitle());
        p.put("memberId", l.getMemberId());
        p.put("memberName", l.getMemberName());
        p.put("dueDate", String.valueOf(l.getDueDate()));
        p.put("returnDate", l.getReturnDate() == null ? null : l.getReturnDate().toString());
        return p;
    }
}

/** Finishes sagas that were interrupted (crash, book-service outage) once the dependency is back. */
@Component
class SagaRecovery {
    private static final Logger log = LoggerFactory.getLogger(SagaRecovery.class);
    private final LoanRepository loans;
    private final LendingService lending;

    SagaRecovery(LoanRepository loans, LendingService lending) { this.loans = loans; this.lending = lending; }

    @Scheduled(fixedDelay = 5000, initialDelay = 15000)
    void recover() {
        for (Loan l : loans.findByStatusAndCreatedAtBefore("PENDING", Instant.now().minusSeconds(10))) {
            try {
                Loan done = lending.advance(l.getId());
                log.info("Recovered loan {} -> {}", l.getId(), done.getStatus());
            } catch (RuntimeException e) {
                log.debug("Loan {} not recovered yet: {}", l.getId(), e.getMessage());
            }
        }
    }
}

/** Relays outbox rows to RabbitMQ (at-least-once). Consumers deduplicate on the message id. */
@Component
class OutboxRelay {
    private static final Logger log = LoggerFactory.getLogger(OutboxRelay.class);
    private final OutboxRepository outbox;
    private final RabbitTemplate rabbit;

    OutboxRelay(OutboxRepository outbox, RabbitTemplate rabbit, MeterRegistry meters) {
        this.outbox = outbox; this.rabbit = rabbit;
        Gauge.builder("library.outbox.pending", outbox, OutboxRepository::countBySentAtIsNull)
            .description("Events stored in the outbox but not yet delivered to RabbitMQ").register(meters);
    }

    @Scheduled(fixedDelay = 300)
    void relay() {
        for (OutboxEvent e : outbox.findTop50BySentAtIsNullOrderByCreatedAtAsc()) {
            try {
                rabbit.convertAndSend("library.events", e.getRoutingKey(), e.getPayload(), m -> {
                    m.getMessageProperties().setMessageId(e.getId());
                    return m;
                });
                e.markSent();
                outbox.save(e);
            } catch (Exception ex) {
                log.warn("Broker not reachable, {} event(s) wait in the outbox: {}", e.getRoutingKey(), ex.getMessage());
                return;
            }
        }
    }
}

/** Loads a realistic demo history (on time, overdue and late-returned loans) once, after the other services are up. */
@Component
class DemoDataSeeder {
    private static final Logger log = LoggerFactory.getLogger(DemoDataSeeder.class);
    private final LoanRepository loans;
    private final LendingService lending;
    private final RemoteGateway remote;

    DemoDataSeeder(LoanRepository loans, LendingService lending, RemoteGateway remote) {
        this.loans = loans; this.lending = lending; this.remote = remote;
    }

    @EventListener(ApplicationReadyEvent.class)
    void start() {
        Thread t = new Thread(this::seed, "demo-data-seeder");
        t.setDaemon(true);
        t.start();
    }

    private void seed() {
        try {
            if (loans.count() > 0) return;
            for (int i = 0; i < 60; i++) {           // wait for member-service and book-service to register
                try { remote.member(1L); break; } catch (Exception e) { Thread.sleep(5000); }
            }
            long[][] plan = { {5, 1}, {7, 2}, {10, 3}, {12, 4}, {20, 5}, {29, 6}, {31, 7}, {38, 8} };
            Loan[] l = new Loan[plan.length];
            for (int i = 0; i < plan.length; i++) l[i] = issueWithRetry(new IssueRequest(plan[i][0], plan[i][1]));
            lending.giveBack(l[0].getId());           // returned on time
            lending.giveBack(l[1].getId());
            late(l[2], 21);                           // still out, overdue
            late(l[3], 16);
            lending.giveBack(late(l[5], 30).getId()); // returned late -> fine-service assesses a fine
            lending.giveBack(late(l[6], 18).getId());
            log.info("Demo lending data loaded");
        } catch (Exception e) {
            log.warn("Demo data not loaded: {}", e.getMessage());
        }
    }

    /** The circuit breakers may still be open from the startup wait, so retry until the loan is really ISSUED. */
    private Loan issueWithRetry(IssueRequest req) throws InterruptedException {
        Loan loan = null;
        for (int attempt = 1; attempt <= 12; attempt++) {
            try {
                loan = loan == null ? lending.issue(req) : lending.advance(loan.getId());
                if ("ISSUED".equals(loan.getStatus())) return loan;
            } catch (RuntimeException e) {
                if (attempt >= 12) throw e;
            }
            Thread.sleep(6000);
        }
        throw new IllegalStateException("loan was not issued in time");
    }

    private Loan late(Loan loan, int days) {
        Loan managed = loans.findById(loan.getId()).orElseThrow();
        managed.shiftBack(days);
        return loans.save(managed);
    }
}

@RestController
@RequestMapping("/api/loans")
class LoanController {
    private final LendingService service;
    private final LoanRepository loans;
    private final LoanEventRepository events;

    LoanController(LendingService service, LoanRepository loans, LoanEventRepository events, MeterRegistry meters) {
        this.service = service; this.loans = loans; this.events = events;
        Gauge.builder("library.loans.pending", loans, r -> r.countByStatus("PENDING"))
            .description("Loans whose saga has not finished").register(meters);
    }

    @GetMapping List<Loan> all() { return loans.findAll(); }

    @GetMapping("/{id}")
    Loan get(@PathVariable Long id) {
        return loans.findById(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Loan not found"));
    }

    @GetMapping("/member/{memberId}")
    List<Loan> byMember(@PathVariable Long memberId) { return loans.findByMemberId(memberId); }

    /** Read side of the event log: the full history of one loan. */
    @GetMapping("/{id}/events")
    List<LoanEvent> history(@PathVariable Long id) { return events.findByLoanIdOrderByIdAsc(id); }

    /** 201 when the saga finished, 202 when it was accepted but is still PENDING (a dependency is down). */
    @PostMapping("/issue")
    ResponseEntity<Loan> issue(@RequestBody IssueRequest req) {
        Loan loan = service.issue(req);
        return ResponseEntity.status("PENDING".equals(loan.getStatus()) ? HttpStatus.ACCEPTED : HttpStatus.CREATED).body(loan);
    }

    /** Demo helper: moves a loan's dates into the past so overdue fines can be shown. */
    @PostMapping("/{id}/simulate-overdue")
    Loan simulateOverdue(@PathVariable Long id, @RequestParam(defaultValue = "20") int days) {
        Loan loan = get(id);
        loan.shiftBack(days);
        return loans.save(loan);
    }

    @PostMapping("/{id}/return")
    Loan giveBack(@PathVariable Long id) { return service.giveBack(id); }
}
