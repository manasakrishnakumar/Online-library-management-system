package com.library.member;

import jakarta.persistence.*;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
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
public class MemberServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(MemberServiceApplication.class, args);
    }

    /** Loads the sample members (members.csv, '|' separated) on first start. */
    @Bean
    CommandLineRunner seed(MemberRepository repo) {
        return args -> {
            if (repo.count() > 0) return;
            try (var in = MemberServiceApplication.class.getResourceAsStream("/members.csv");
                 var rd = new java.io.BufferedReader(new java.io.InputStreamReader(in, java.nio.charset.StandardCharsets.UTF_8))) {
                rd.lines().skip(1).filter(l -> !l.isBlank()).forEach(l -> {
                    String[] c = l.split("[|]");
                    repo.save(new Member(c[0], c[1]));
                });
            }
        };
    }
}

@Entity
class Member {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @NotBlank private String name;
    @NotBlank @Email @Column(unique = true) private String email;
    private boolean active = true;

    protected Member() {}
    Member(String name, String email) { this.name = name; this.email = email; }

    public Long getId() { return id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public boolean isActive() { return active; }
    public void setActive(boolean active) { this.active = active; }
}

interface MemberRepository extends JpaRepository<Member, Long> {}

@RestController
@RequestMapping("/api/members")
class MemberController {
    private final MemberRepository repo;

    MemberController(MemberRepository repo) { this.repo = repo; }

    @GetMapping
    List<Member> all() { return repo.findAll(); }

    @GetMapping("/{id}")
    Member get(@PathVariable Long id) { return find(id); }

    @PostMapping @ResponseStatus(HttpStatus.CREATED)
    Member create(@Valid @RequestBody Member m) { return repo.save(m); }

    @PutMapping("/{id}")
    Member update(@PathVariable Long id, @Valid @RequestBody Member in) {
        Member m = find(id);
        m.setName(in.getName()); m.setEmail(in.getEmail()); m.setActive(in.isActive());
        return repo.save(m);
    }

    @DeleteMapping("/{id}") @ResponseStatus(HttpStatus.NO_CONTENT)
    void delete(@PathVariable Long id) { repo.delete(find(id)); }

    private Member find(Long id) {
        return repo.findById(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Member not found"));
    }
}
