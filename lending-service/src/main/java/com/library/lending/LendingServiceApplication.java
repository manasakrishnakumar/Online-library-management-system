package com.library.lending;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import jakarta.persistence.*;
import java.time.Instant;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
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
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.annotation.Bean;
import org.springframework.context.event.EventListener;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@SpringBootApplication
@EnableFeignClients
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
    @PutMapping("/api/books/{id}/borrow") BookView borrow(@PathVariable("id") Long id);
    @PutMapping("/api/books/{id}/return") BookView giveBack(@PathVariable("id") Long id);
}

@FeignClient(name = "member-service")
interface MemberClient {
    @GetMapping("/api/members/{id}") MemberView get(@PathVariable("id") Long id);
}

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

    protected Loan() {}
    Loan(Long bookId, String bookTitle, Long memberId, String memberName, LocalDate issueDate, LocalDate dueDate) {
        this.bookId = bookId; this.bookTitle = bookTitle; this.memberId = memberId; this.memberName = memberName;
        this.issueDate = issueDate; this.dueDate = dueDate; this.status = "ISSUED";
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
    private String details;

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

interface LoanRepository extends JpaRepository<Loan, Long> {
    List<Loan> findByMemberId(Long memberId);
}

interface LoanEventRepository extends JpaRepository<LoanEvent, Long> {
    List<LoanEvent> findByLoanIdOrderByIdAsc(Long loanId);
}

record IssueRequest(Long bookId, Long memberId) {}

/** In-process domain event; forwarded to RabbitMQ only after the database transaction commits. */
record LibraryEvent(String routingKey, Map<String, Object> payload) {}

/** Asynchronous messaging: lending announces facts, and other services (fine, notification) react on their own. */
@Component
class EventPublisher {
    private static final Logger log = LoggerFactory.getLogger(EventPublisher.class);
    private final RabbitTemplate rabbit;
    private final ObjectMapper mapper;

    EventPublisher(RabbitTemplate rabbit, ObjectMapper mapper) { this.rabbit = rabbit; this.mapper = mapper; }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    void publish(LibraryEvent e) {
        try {
            rabbit.convertAndSend("library.events", e.routingKey(), mapper.writeValueAsString(e.payload()));
        } catch (Exception ex) {
            log.warn("Could not publish {}: {}", e.routingKey(), ex.getMessage());
        }
    }
}

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
    BookView borrow(Long id) { return books.borrow(id); }

    @CircuitBreaker(name = "bookService", fallbackMethod = "returnFallback")
    BookView giveBack(Long id) { return books.giveBack(id); }

    MemberView memberFallback(Long id, Throwable t) { throw unavailable("member-service", t); }
    BookView borrowFallback(Long id, Throwable t) { throw unavailable("book-service", t); }
    BookView returnFallback(Long id, Throwable t) { throw unavailable("book-service", t); }

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

@Service
class LendingService {
    private final LoanRepository loans;
    private final LoanEventRepository events;
    private final RemoteGateway remote;
    private final ApplicationEventPublisher bus;
    private final int loanDays;

    LendingService(LoanRepository loans, LoanEventRepository events, RemoteGateway remote,
                   ApplicationEventPublisher bus, @Value("${library.loan-period-days:14}") int loanDays) {
        this.loans = loans; this.events = events; this.remote = remote; this.bus = bus; this.loanDays = loanDays;
    }

    @Transactional
    Loan issue(IssueRequest req) {
        MemberView m = remote.member(req.memberId());
        if (!m.active()) throw new ResponseStatusException(HttpStatus.CONFLICT, "Member is not active");
        BookView b = remote.borrow(req.bookId());
        LocalDate today = LocalDate.now();
        Loan loan = loans.save(new Loan(b.id(), b.title(), m.id(), m.name(), today, today.plusDays(loanDays)));
        events.save(new LoanEvent(loan.getId(), "BOOK_ISSUED",
            b.title() + " issued to " + m.name() + ", due " + loan.getDueDate()));
        bus.publishEvent(new LibraryEvent("loan.issued", payload(loan)));
        return loan;
    }

    @Transactional
    Loan giveBack(Long id) {
        Loan loan = loans.findById(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Loan not found"));
        if ("RETURNED".equals(loan.getStatus())) throw new ResponseStatusException(HttpStatus.CONFLICT, "Already returned");
        remote.giveBack(loan.getBookId());
        loan.markReturned(LocalDate.now());
        events.save(new LoanEvent(id, "BOOK_RETURNED", loan.getBookTitle() + " returned on " + loan.getReturnDate()));
        Loan saved = loans.save(loan);
        bus.publishEvent(new LibraryEvent("loan.returned", payload(saved)));
        return saved;
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

    /** The circuit breakers may still be open from the startup wait, so retry until they close again. */
    private Loan issueWithRetry(IssueRequest req) throws InterruptedException {
        for (int attempt = 1; ; attempt++) {
            try { return lending.issue(req); }
            catch (RuntimeException e) {
                if (attempt >= 8) throw e;
                Thread.sleep(6000);
            }
        }
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

    LoanController(LendingService service, LoanRepository loans, LoanEventRepository events) {
        this.service = service; this.loans = loans; this.events = events;
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

    @PostMapping("/issue") @ResponseStatus(HttpStatus.CREATED)
    Loan issue(@RequestBody IssueRequest req) { return service.issue(req); }

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
