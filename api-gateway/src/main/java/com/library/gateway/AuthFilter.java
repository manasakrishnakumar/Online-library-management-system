package com.library.gateway;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import java.nio.charset.StandardCharsets;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/** Verifies the bearer token on every routed request and applies the role rules before the call reaches a service. */
@Component
public class AuthFilter implements GlobalFilter, Ordered {
    private final JwtService jwt;

    public AuthFilter(JwtService jwt) { this.jwt = jwt; }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();
        HttpMethod method = exchange.getRequest().getMethod();
        if (path.startsWith("/api/auth/") || HttpMethod.OPTIONS.equals(method)) return chain.filter(exchange);

        String header = exchange.getRequest().getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (header == null || !header.startsWith("Bearer ")) return reject(exchange, HttpStatus.UNAUTHORIZED, "Login required");
        Claims claims;
        try {
            claims = jwt.parse(header.substring(7));
        } catch (JwtException | IllegalArgumentException e) {
            return reject(exchange, HttpStatus.UNAUTHORIZED, "Invalid or expired token");
        }
        String role = claims.get("role", String.class);
        Long memberId = claims.get("memberId", Long.class);
        if (!AccessRules.allowed(method.name(), path, role, memberId)) {
            return reject(exchange, HttpStatus.FORBIDDEN, "Your role (" + role + ") may not do this");
        }
        var mutated = exchange.getRequest().mutate()
            .headers(h -> { h.remove("X-Auth-User"); h.remove("X-Auth-Role"); h.add("X-Auth-User", claims.getSubject()); h.add("X-Auth-Role", role); })
            .build();
        return chain.filter(exchange.mutate().request(mutated).build());
    }

    private Mono<Void> reject(ServerWebExchange exchange, HttpStatus status, String message) {
        var res = exchange.getResponse();
        res.setStatusCode(status);
        res.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        byte[] body = ("{\"status\":" + status.value() + ",\"error\":\"" + status.getReasonPhrase() + "\",\"message\":\"" + message + "\"}")
            .getBytes(StandardCharsets.UTF_8);
        DataBuffer buf = res.bufferFactory().wrap(body);
        return res.writeWith(Mono.just(buf));
    }

    @Override
    public int getOrder() { return -1; }
}
