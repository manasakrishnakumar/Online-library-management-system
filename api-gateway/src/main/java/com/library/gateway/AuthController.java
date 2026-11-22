package com.library.gateway;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/** Login, token refresh and password change, served by the gateway itself (passwords are BCrypt hashes). */
@RestController
@RequestMapping("/api/auth")
public class AuthController {
    record LoginRequest(String username, String password) {}
    record PasswordChange(String oldPassword, String newPassword) {}

    private final JwtService jwt;
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
    private final Map<String, SecurityProps.UserDef> users = new HashMap<>();
    private final Map<String, String> hashes = new ConcurrentHashMap<>();

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
        return tokenResponse(u);
    }

    /** Exchanges a still-valid token for a fresh one, so an active session does not end after the token lifetime. */
    @PostMapping("/refresh")
    public Map<String, Object> refresh(@RequestHeader(value = "Authorization", required = false) String auth) {
        return tokenResponse(userOf(auth));
    }

    /** Changes the caller's password. The new hash is kept in memory, so it lasts until the gateway restarts. */
    @PostMapping("/change-password")
    public Map<String, String> changePassword(@RequestHeader(value = "Authorization", required = false) String auth, @RequestBody PasswordChange req) {
        SecurityProps.UserDef u = userOf(auth);
        if (req.oldPassword() == null || !encoder.matches(req.oldPassword(), hashes.get(u.getUsername()))) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "The old password is wrong");
        }
        if (req.newPassword() == null || req.newPassword().length() < 8) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "The new password must have at least 8 characters");
        }
        hashes.put(u.getUsername(), encoder.encode(req.newPassword()));
        return Map.of("message", "Password changed");
    }

    private SecurityProps.UserDef userOf(String auth) {
        if (auth == null || !auth.startsWith("Bearer ")) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Login required");
        Claims claims;
        try {
            claims = jwt.parse(auth.substring(7));
        } catch (JwtException | IllegalArgumentException e) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid or expired token");
        }
        SecurityProps.UserDef u = users.get(claims.getSubject());
        if (u == null) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Unknown user");
        return u;
    }

    private Map<String, Object> tokenResponse(SecurityProps.UserDef u) {
        Map<String, Object> out = new HashMap<>();
        out.put("token", jwt.issue(u.getUsername(), u.getRole(), u.getMemberId()));
        out.put("username", u.getUsername());
        out.put("role", u.getRole());
        out.put("memberId", u.getMemberId());
        return out;
    }
}
