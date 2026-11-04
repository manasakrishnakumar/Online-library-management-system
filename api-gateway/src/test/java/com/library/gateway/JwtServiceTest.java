package com.library.gateway;

import static org.junit.jupiter.api.Assertions.*;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import org.junit.jupiter.api.Test;

class JwtServiceTest {
    private JwtService service(String secret, long minutes) {
        SecurityProps p = new SecurityProps();
        p.setJwtSecret(secret);
        p.setTokenMinutes(minutes);
        return new JwtService(p);
    }

    @Test
    void tokenCarriesRoleAndMemberId() {
        JwtService jwt = service("0123456789-0123456789-0123456789-ab", 60);
        Claims c = jwt.parse(jwt.issue("asha", "MEMBER", 1L));
        assertEquals("asha", c.getSubject());
        assertEquals("MEMBER", c.get("role", String.class));
        assertEquals(1L, c.get("memberId", Long.class));
    }

    @Test
    void tokenSignedWithAnotherKeyIsRejected() {
        String token = service("0123456789-0123456789-0123456789-ab", 60).issue("x", "LIBRARIAN", null);
        assertThrows(JwtException.class, () -> service("another-secret-another-secret-another-1", 60).parse(token));
    }

    @Test
    void tamperedTokenIsRejected() {
        JwtService jwt = service("0123456789-0123456789-0123456789-ab", 60);
        String token = jwt.issue("x", "MEMBER", 1L);
        String forged = token.substring(0, token.length() - 3) + (token.endsWith("AAA") ? "BBB" : "AAA");
        assertThrows(JwtException.class, () -> jwt.parse(forged));
    }

    @Test
    void expiredTokenIsRejected() {
        JwtService jwt = service("0123456789-0123456789-0123456789-ab", -1);
        assertThrows(JwtException.class, () -> jwt.parse(jwt.issue("x", "MEMBER", 1L)));
    }
}
