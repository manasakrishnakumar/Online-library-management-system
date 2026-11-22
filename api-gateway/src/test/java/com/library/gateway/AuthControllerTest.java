package com.library.gateway;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

class AuthControllerTest {
    private AuthController auth;
    private String bearer(Map<String, Object> login) { return "Bearer " + login.get("token"); }

    @BeforeEach
    void setUp() {
        SecurityProps p = new SecurityProps();
        p.setJwtSecret("0123456789-0123456789-0123456789-ab");
        SecurityProps.UserDef u = new SecurityProps.UserDef();
        u.setUsername("asha"); u.setPassword("member123"); u.setRole("MEMBER"); u.setMemberId(1L);
        p.getUsers().add(u);
        auth = new AuthController(new JwtService(p), p);
    }

    @Test
    void wrongPasswordIsRejected() {
        ResponseStatusException e = assertThrows(ResponseStatusException.class, () -> auth.login(new AuthController.LoginRequest("asha", "nope")));
        assertEquals(HttpStatus.UNAUTHORIZED, e.getStatusCode());
    }

    @Test
    void refreshGivesAFreshTokenForTheSameUser() {
        Map<String, Object> login = auth.login(new AuthController.LoginRequest("asha", "member123"));
        Map<String, Object> again = auth.refresh(bearer(login));
        assertEquals("asha", again.get("username"));
        assertEquals("MEMBER", again.get("role"));
        assertEquals(1L, again.get("memberId"));
    }

    @Test
    void refreshWithoutOrWithBadTokenIsRejected() {
        assertThrows(ResponseStatusException.class, () -> auth.refresh(null));
        assertThrows(ResponseStatusException.class, () -> auth.refresh("Bearer abc.def.ghi"));
    }

    @Test
    void changedPasswordWorksAndTheOldOneStops() {
        Map<String, Object> login = auth.login(new AuthController.LoginRequest("asha", "member123"));
        auth.changePassword(bearer(login), new AuthController.PasswordChange("member123", "a-new-password"));
        assertNotNull(auth.login(new AuthController.LoginRequest("asha", "a-new-password")).get("token"));
        assertThrows(ResponseStatusException.class, () -> auth.login(new AuthController.LoginRequest("asha", "member123")));
    }

    @Test
    void changePasswordChecksOldPasswordAndLength() {
        String b = bearer(auth.login(new AuthController.LoginRequest("asha", "member123")));
        ResponseStatusException wrong = assertThrows(ResponseStatusException.class, () -> auth.changePassword(b, new AuthController.PasswordChange("bad", "long-enough-1")));
        assertEquals(HttpStatus.FORBIDDEN, wrong.getStatusCode());
        ResponseStatusException shortPw = assertThrows(ResponseStatusException.class, () -> auth.changePassword(b, new AuthController.PasswordChange("member123", "short")));
        assertEquals(HttpStatus.BAD_REQUEST, shortPw.getStatusCode());
    }
}
