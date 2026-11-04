package com.library.gateway;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import javax.crypto.SecretKey;
import org.springframework.stereotype.Component;

/** Issues and verifies HS256 JSON Web Tokens carrying the user's role and, for members, their member id. */
@Component
public class JwtService {
    private final SecretKey key;
    private final long minutes;

    public JwtService(SecurityProps props) {
        this.key = Keys.hmacShaKeyFor(props.getJwtSecret().getBytes(StandardCharsets.UTF_8));
        this.minutes = props.getTokenMinutes();
    }

    public String issue(String username, String role, Long memberId) {
        Instant now = Instant.now();
        var b = Jwts.builder().subject(username).claim("role", role)
            .issuedAt(Date.from(now)).expiration(Date.from(now.plusSeconds(minutes * 60)));
        if (memberId != null) b.claim("memberId", memberId);
        return b.signWith(key).compact();
    }

    /** Throws io.jsonwebtoken.JwtException when the token is malformed, tampered with or expired. */
    public Claims parse(String token) {
        return Jwts.parser().verifyWith(key).build().parseSignedClaims(token).getPayload();
    }
}
