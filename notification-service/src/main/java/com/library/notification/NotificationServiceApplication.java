package com.library.notification;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.List;
import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Component;
import org.springframework.web.bind.annotation.*;

@SpringBootApplication
public class NotificationServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(NotificationServiceApplication.class, args);
    }

    @Bean TopicExchange libraryEvents() { return new TopicExchange("library.events"); }
    @Bean Queue notificationQueue() { return new Queue("notification.all-events", true); }
    @Bean Binding loanBinding(Queue notificationQueue, TopicExchange libraryEvents) {
        return BindingBuilder.bind(notificationQueue).to(libraryEvents).with("loan.*");
    }
    @Bean Binding fineBinding(Queue notificationQueue, TopicExchange libraryEvents) {
        return BindingBuilder.bind(notificationQueue).to(libraryEvents).with("fine.*");
    }
}

@Entity
class Notification {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private Long memberId;
    private String type;
    @Column(unique = true) private String eventId;
    @Column(length = 500) private String message;
    private Instant createdAt = Instant.now();

    protected Notification() {}
    Notification(Long memberId, String type, String message, String eventId) {
        this.memberId = memberId; this.type = type; this.message = message; this.eventId = eventId;
    }

    public Long getId() { return id; }
    public Long getMemberId() { return memberId; }
    public String getType() { return type; }
    public String getMessage() { return message; }
    public Instant getCreatedAt() { return createdAt; }
}

interface NotificationRepository extends JpaRepository<Notification, Long> {
    List<Notification> findByMemberIdOrderByIdDesc(Long memberId);
    boolean existsByEventId(String eventId);
}

/** Consumes loan.* and fine.* events from RabbitMQ and records the message a member would receive by e-mail/SMS. */
@Component
class EventConsumer {
    private final NotificationRepository repo;
    private final ObjectMapper mapper;

    private final io.micrometer.core.instrument.MeterRegistry meters;

    EventConsumer(NotificationRepository repo, ObjectMapper mapper, io.micrometer.core.instrument.MeterRegistry meters) {
        this.repo = repo; this.mapper = mapper; this.meters = meters;
    }

    @RabbitListener(queues = "notification.all-events")
    void onEvent(org.springframework.amqp.core.Message msg) throws Exception {
        String key = msg.getMessageProperties().getReceivedRoutingKey();
        String eventId = msg.getMessageProperties().getMessageId();
        if (eventId != null && repo.existsByEventId(eventId)) return;      // duplicate delivery (at-least-once outbox)
        JsonNode n = mapper.readTree(new String(msg.getBody(), java.nio.charset.StandardCharsets.UTF_8));
        long member = n.get("memberId").asLong();
        String name = n.get("memberName").asText();
        String book = n.get("bookTitle").asText();
        switch (key) {
            case "loan.issued" -> repo.save(new Notification(member, "LOAN_ISSUED",
                "Hi " + name + ", you borrowed \"" + book + "\". Please return it by " + n.get("dueDate").asText() + ".", eventId));
            case "loan.returned" -> repo.save(new Notification(member, "LOAN_RETURNED",
                "Hi " + name + ", thanks for returning \"" + book + "\".", eventId));
            case "fine.assessed" -> repo.save(new Notification(member, "FINE_ASSESSED",
                "Hi " + name + ", \"" + book + "\" was " + n.get("daysOverdue").asLong() + " days late. A fine of Rs "
                    + n.get("amount").asText() + " has been added to your account.", eventId));
            default -> { return; }
        }
        meters.counter("library.notifications", "type", key).increment();
    }
}

@RestController
@RequestMapping("/api/notifications")
class NotificationController {
    private final NotificationRepository repo;

    NotificationController(NotificationRepository repo) { this.repo = repo; }

    @GetMapping
    List<Notification> all() { return repo.findAll(Sort.by(Sort.Direction.DESC, "id")); }

    @GetMapping("/member/{memberId}")
    List<Notification> byMember(@PathVariable Long memberId) { return repo.findByMemberIdOrderByIdDesc(memberId); }
}
