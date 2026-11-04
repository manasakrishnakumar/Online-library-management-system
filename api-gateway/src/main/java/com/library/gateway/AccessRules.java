package com.library.gateway;

import java.util.regex.Pattern;

/** Role-based access rules enforced at the gateway. Librarians may do everything except call internal endpoints. */
public final class AccessRules {
    private static final Pattern INTERNAL = Pattern.compile("^/api/books/\\d+/(borrow|return)$");
    private static final Pattern BOOK_READ = Pattern.compile("^/api/books(/search|/\\d+)?$");
    private static final Pattern OWN = Pattern.compile("^/api/(members|loans/member|fines/member|notifications/member)/(\\d+)$");

    private AccessRules() {}

    public static boolean allowed(String method, String path, String role, Long memberId) {
        if (INTERNAL.matcher(path).matches()) return false;       // stock changes belong to the lending saga only
        if ("LIBRARIAN".equals(role)) return true;
        if (!"MEMBER".equals(role) || !"GET".equals(method)) return false;
        if (BOOK_READ.matcher(path).matches()) return true;
        var m = OWN.matcher(path);
        return m.matches() && memberId != null && memberId.toString().equals(m.group(2));
    }
}
