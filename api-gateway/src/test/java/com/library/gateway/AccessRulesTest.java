package com.library.gateway;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class AccessRulesTest {
    @Test
    void librarianMayManageEverythingPublic() {
        assertTrue(AccessRules.allowed("POST", "/api/loans/issue", "LIBRARIAN", null));
        assertTrue(AccessRules.allowed("DELETE", "/api/books/5", "LIBRARIAN", null));
        assertTrue(AccessRules.allowed("GET", "/api/members", "LIBRARIAN", null));
    }

    @Test
    void stockEndpointsAreInternalOnlyEvenForLibrarians() {
        assertFalse(AccessRules.allowed("PUT", "/api/books/5/borrow", "LIBRARIAN", null));
        assertFalse(AccessRules.allowed("PUT", "/api/books/5/return", "LIBRARIAN", null));
    }

    @Test
    void memberCanBrowseBooksButNotChangeThem() {
        assertTrue(AccessRules.allowed("GET", "/api/books", "MEMBER", 1L));
        assertTrue(AccessRules.allowed("GET", "/api/books/search", "MEMBER", 1L));
        assertFalse(AccessRules.allowed("POST", "/api/books", "MEMBER", 1L));
        assertFalse(AccessRules.allowed("DELETE", "/api/books/5", "MEMBER", 1L));
    }

    @Test
    void memberSeesOnlyOwnRecords() {
        assertTrue(AccessRules.allowed("GET", "/api/loans/member/1", "MEMBER", 1L));
        assertTrue(AccessRules.allowed("GET", "/api/fines/member/1", "MEMBER", 1L));
        assertTrue(AccessRules.allowed("GET", "/api/notifications/member/1", "MEMBER", 1L));
        assertFalse(AccessRules.allowed("GET", "/api/loans/member/2", "MEMBER", 1L));
        assertFalse(AccessRules.allowed("GET", "/api/members", "MEMBER", 1L));
        assertFalse(AccessRules.allowed("GET", "/api/loans", "MEMBER", 1L));
        assertFalse(AccessRules.allowed("POST", "/api/loans/issue", "MEMBER", 1L));
    }

    @Test
    void unknownRoleGetsNothing() {
        assertFalse(AccessRules.allowed("GET", "/api/books", "GUEST", null));
        assertFalse(AccessRules.allowed("GET", "/api/books", null, null));
    }
}
