package com.library.gateway;

import java.util.HashMap;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/** Login endpoint served by the gateway itself: checks the password (BCrypt) and returns a signed JWT. */
@RestController
@RequestMapping("/api/auth")
public class AuthController {
    record LoginRequest(String username, String password) {}

    private final JwtService jwt;
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
    private final Map<String, SecurityProps.UserDef> users = new HashMap<>();
    private final Map<String, String> hashes = new HashMap<>();

    public AuthController(JwtService jwt, SecurityProps props) {
        this.jwt = jwt;
        for (SecurityProps.UserDef u : props.getUsers()) {
            users.put(u.getUsername(), u);
            hashes.put(u.getUsername(), encoder.encode(u.getPassword()));   // hashed once at start-up; only hashes are compared
        }
    }

    @PostMapping("/login")
    public Map<String, Object> login(@RequestBody LoginRequest req) {
        SecurityProps.UserDef u = req.username() == null ? null : users.get(req.username());
        if (u == null || req.password() == null || !encoder.matches(req.password(), hashes.get(u.getUsername()))) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Wrong username or password");
        }
        Map<String, Object> out = new HashMap<>();
        out.put("token", jwt.issue(u.getUsername(), u.getRole(), u.getMemberId()));
        out.put("username", u.getUsername());
        out.put("role", u.getRole());
        out.put("memberId", u.getMemberId());
        return out;
    }
}
