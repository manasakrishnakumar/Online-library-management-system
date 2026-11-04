package com.library.gateway;

import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

/** Demo user store and JWT settings, bound from library.security.* (served by the Config Server or application.yml). */
@ConfigurationProperties(prefix = "library.security")
public class SecurityProps {
    private String jwtSecret = "change-me-change-me-change-me-32b!";
    private long tokenMinutes = 60;
    private List<UserDef> users = new ArrayList<>();

    public String getJwtSecret() { return jwtSecret; }
    public void setJwtSecret(String jwtSecret) { this.jwtSecret = jwtSecret; }
    public long getTokenMinutes() { return tokenMinutes; }
    public void setTokenMinutes(long tokenMinutes) { this.tokenMinutes = tokenMinutes; }
    public List<UserDef> getUsers() { return users; }
    public void setUsers(List<UserDef> users) { this.users = users; }

    public static class UserDef {
        private String username;
        private String password;
        private String role;
        private Long memberId;

        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }
        public String getPassword() { return password; }
        public void setPassword(String password) { this.password = password; }
        public String getRole() { return role; }
        public void setRole(String role) { this.role = role; }
        public Long getMemberId() { return memberId; }
        public void setMemberId(Long memberId) { this.memberId = memberId; }
    }
}
