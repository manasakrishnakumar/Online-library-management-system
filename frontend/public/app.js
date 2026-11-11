"use strict";

/* ---------- helpers ---------- */
const $ = (s, r = document) => r.querySelector(s);
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const today = () => new Date().toISOString().slice(0, 10);

let session = null;
try { session = JSON.parse(sessionStorage.getItem("lib.session")); } catch { session = null; }
const saveSession = s => {
  session = s;
  try { s ? sessionStorage.setItem("lib.session", JSON.stringify(s)) : sessionStorage.removeItem("lib.session"); } catch { /* storage blocked */ }
};
const isLibrarian = () => session && session.role === "LIBRARIAN";

async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (session) headers.Authorization = "Bearer " + session.token;
  const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (res.status === 401 && session) { saveSession(null); showLogin("Your session ended, please sign in again."); throw new Error("Please sign in again"); }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const msg = data && (data.message || data.error) ? (data.message || data.error) : res.statusText;
    throw new Error(res.status === 503 ? "A backend service is unavailable right now. Please try again shortly." : msg || "Request failed");
  }
  return data;
}

function toast(msg, bad) {
  const t = document.createElement("div");
  t.className = "toast" + (bad ? " err" : "");
  t.textContent = msg;
  $("#toasts").appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

/** Wraps an async handler so failures show as a toast instead of an unhandled rejection. */
const safe = fn => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message, true); } };

function openModal(title, bodyHtml) {
  $("#sheet").innerHTML = `<h2>${esc(title)}</h2>${bodyHtml}`;
  $("#modal").hidden = false;
  const first = $("#sheet input, #sheet select");
  if (first) first.focus();
  return $("#sheet");
}
const closeModal = () => { $("#modal").hidden = true; };
$("#modal").addEventListener("click", e => { if (e.target.id === "modal") closeModal(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });

function table(cols, rows, actions) {
  if (!rows.length) return `<div class="empty"><span class="big">&#128237;</span>Nothing here yet.</div>`;
  const head = cols.map(c => `<th>${esc(c.h)}</th>`).join("") + (actions ? "<th></th>" : "");
  const body = rows.map(r => `<tr>${cols.map(c => `<td${c.w ? ' class="w"' : ""}>${c.f ? c.f(r) : esc(r[c.k])}</td>`).join("")}${actions ? `<td class="act">${actions(r)}</td>` : ""}</tr>`).join("");
  return `<div class="tw"><table><tr>${head}</tr>${body}</table></div>`;
}


const firstName = () => {
  const n = (session.username || "").split("@")[0].split(".")[0];
  return n.charAt(0).toUpperCase() + n.slice(1);
};
const shortTitle = t => String(t).replace(/\s*\(.*\)\s*$/, "");
const coverHue = t => { let h = 0; for (const ch of String(t)) h = (h * 31 + ch.charCodeAt(0)) % 360; return h; };
const cover = b => `<div class="cover" style="--h:${coverHue(b.title)}"><span>${esc(shortTitle(b.title))}</span></div>`;
const stat = (icon, n, l, tone) => `<div class="stat ${tone || ""}"><div class="ico">${icon}</div><div><div class="n">${esc(n)}</div><div class="l">${esc(l)}</div></div></div>`;

const isOverdue = l => l.status === "ISSUED" && l.dueDate < today();

/* ---------- pages ---------- */
const pages = {};

pages.dashboard = async view => {
  const [books, members, loans, fines] = await Promise.all([api("GET", "/api/books"), api("GET", "/api/members"), api("GET", "/api/loans"), api("GET", "/api/fines")]);
  const active = loans.filter(l => l.status === "ISSUED");
  const overdue = active.filter(isOverdue);
  const open = fines.filter(f => !f.paid);
  const unpaid = open.reduce((s, f) => s + Number(f.amount), 0);
  const total = books.reduce((s, b) => s + b.totalCopies, 0), avail = books.reduce((s, b) => s + b.availableCopies, 0);
  const pct = total ? Math.round(avail / total * 100) : 0;
  const nameOf = id => (members.find(m => m.id === id) || {}).name || "Member #" + id;
  view.innerHTML = `<section class="hero"><div><h2>Welcome back, ${esc(firstName())}</h2>
      <p>${active.length} book${active.length === 1 ? " is" : "s are"} out on loan and ${overdue.length} ${overdue.length === 1 ? "is" : "are"} overdue. ${open.length ? "Unpaid fines: ₹" + unpaid.toFixed(2) + "." : "No unpaid fines."}</p></div>
      <div class="ring" style="--p:${pct}"><span>${pct}%<small>in stock</small></span></div></section>
    <div class="cards">
      ${stat("&#128218;", books.length.toLocaleString(), "Book titles")}
      ${stat("&#128214;", avail.toLocaleString() + " / " + total.toLocaleString(), "Copies available", "good")}
      ${stat("&#128101;", members.length, "Members")}
      ${stat("&#128257;", active.length, "Books on loan", "warn")}
      ${stat("&#9200;", overdue.length, "Overdue loans", overdue.length ? "bad" : "good")}
      ${stat("&#128176;", "₹" + unpaid.toFixed(2), "Unpaid fines", open.length ? "bad" : "good")}
    </div>
    <div class="two">
      <div class="panel"><h2>Currently on loan</h2>${table([
        { h: "Book", k: "bookTitle", w: 1 }, { h: "Member", k: "memberName", w: 1 },
        { h: "Due", k: "dueDate" }, { h: "Status", f: l => isOverdue(l) ? '<span class="tag bad">Overdue</span>' : '<span class="tag ok">On time</span>' }
      ], active)}</div>
      <div class="panel"><h2>Unpaid fines</h2>${table([
        { h: "Member", f: f => esc(nameOf(f.memberId)) }, { h: "Days late", k: "daysOverdue" }, { h: "Amount", f: f => "₹" + Number(f.amount).toFixed(2) }
      ], open)}</div>
    </div>`;
};

pages.books = async view => {
  const ro = !isLibrarian();
  let books = await api("GET", "/api/books");
  let q = "", page = 0, mode = "grid";
  const draw = () => {
    const PAGE = mode === "grid" ? 24 : 25;
    const all = books.filter(b => (b.title + " " + b.author + " " + b.isbn + " " + (b.category || "")).toLowerCase().includes(q.toLowerCase()));
    const pages = Math.max(1, Math.ceil(all.length / PAGE));
    page = Math.min(page, pages - 1);
    const rows = all.slice(page * PAGE, page * PAGE + PAGE);
    const avail = b => b.availableCopies > 0 ? `<span class="tag ok">${b.availableCopies} of ${b.totalCopies} in</span>` : `<span class="tag bad">All out</span>`;
    const acts = b => ro ? "" : `<div class="acts"><button class="b s" data-edit="${b.id}">Edit</button><button class="b s d" data-del="${b.id}">Delete</button></div>`;
    let content;
    if (!rows.length) content = `<div class="empty"><span class="big">&#128269;</span>No books match your search.</div>`;
    else if (mode === "grid") {
      content = `<div class="grid">${rows.map(b => `<article class="book">${cover(b)}<div class="meta"><h3 title="${esc(b.title)}">${esc(shortTitle(b.title))}</h3><p>${esc(b.author)}</p>
        <div class="chips">${b.category ? `<span class="chip">${esc(b.category)}</span>` : ""}${avail(b)}</div>${acts(b)}</div></article>`).join("")}</div>`;
    } else {
      content = table([
        { h: "Title", k: "title", w: 1 }, { h: "Author", k: "author", w: 1 }, { h: "Category", k: "category" }, { h: "ISBN", k: "isbn" },
        { h: "Available", f: b => avail(b) }
      ], rows, ro ? null : b => `<button class="b s" data-edit="${b.id}">Edit</button><button class="b s d" data-del="${b.id}">Delete</button>`);
    }
    $("#list").innerHTML = content +
      `<div class="pager"><button class="b s" data-pg="-1" ${page === 0 ? "disabled" : ""}>&larr; Previous</button><span>Page ${page + 1} of ${pages} &middot; ${all.length.toLocaleString()} books</span><button class="b s" data-pg="1" ${page >= pages - 1 ? "disabled" : ""}>Next &rarr;</button></div>`;
  };
  view.innerHTML = `<div class="bar"><input id="q" type="search" placeholder="Search title, author, category or ISBN"><span class="grow"></span>
    <div class="seg"><button data-mode="grid" class="on">Grid</button><button data-mode="table">Table</button></div>${ro ? "" : '<button class="b p" id="add">+ Add book</button>'}</div><div id="list"></div>`;
  draw();
  $("#q").oninput = e => { q = e.target.value; page = 0; draw(); };
  view.querySelector(".seg").onclick = e => {
    if (!e.target.dataset.mode) return;
    mode = e.target.dataset.mode; page = 0;
    view.querySelectorAll(".seg button").forEach(b => b.classList.toggle("on", b === e.target));
    draw();
  };
  const form = (title, b) => {
    const s = openModal(title, `<form id="f">
      <label>Title<input name="title" required value="${esc(b?.title)}"></label>
      <label>Author<input name="author" required value="${esc(b?.author)}"></label>
      <label>ISBN<input name="isbn" required value="${esc(b?.isbn)}"></label>
      <label>Category<input name="category" value="${esc(b?.category)}"></label>
      <label>Total copies<input name="totalCopies" type="number" min="1" required value="${esc(b?.totalCopies ?? 1)}"></label>
      <div class="row"><button type="button" class="b" id="cancel">Cancel</button><button class="b p">Save</button></div></form>`);
    $("#cancel", s).onclick = closeModal;
    $("#f", s).onsubmit = safe(async e => {
      e.preventDefault();
      const d = Object.fromEntries(new FormData(e.target)); d.totalCopies = +d.totalCopies;
      if (b) await api("PUT", "/api/books/" + b.id, d); else await api("POST", "/api/books", d);
      closeModal(); toast(b ? "Book updated" : "Book added"); route();
    });
  };
  if (!ro) $("#add").onclick = () => form("Add book");
  $("#list").onclick = safe(async e => {
    const edit = e.target.dataset.edit, del = e.target.dataset.del;
    if (e.target.dataset.pg) { page += +e.target.dataset.pg; draw(); window.scrollTo({ top: 0, behavior: "smooth" }); return; }
    if (edit) form("Edit book", books.find(b => b.id == edit));
    if (del && confirm("Delete this book?")) { await api("DELETE", "/api/books/" + del); toast("Book deleted"); route(); }
  });
};

pages.members = async view => {
  const members = await api("GET", "/api/members");
  view.innerHTML = `<div class="bar"><span class="grow"></span><button class="b p" id="add">Add member</button></div>
    <div class="panel">${table([
      { h: "Name", k: "name" }, { h: "Email", k: "email" },
      { h: "Status", f: m => m.active ? '<span class="tag ok">Active</span>' : '<span class="tag warn">Suspended</span>' }
    ], members, m => `<button class="b s" data-edit="${m.id}">Edit</button><button class="b s" data-toggle="${m.id}">${m.active ? "Suspend" : "Activate"}</button><button class="b s d" data-del="${m.id}">Delete</button>`)}</div>`;
  const form = (title, m) => {
    const s = openModal(title, `<form id="f">
      <label>Name<input name="name" required value="${esc(m?.name)}"></label>
      <label>Email<input name="email" type="email" required value="${esc(m?.email)}"></label>
      <div class="row"><button type="button" class="b" id="cancel">Cancel</button><button class="b p">Save</button></div></form>`);
    $("#cancel", s).onclick = closeModal;
    $("#f", s).onsubmit = safe(async e => {
      e.preventDefault();
      const d = Object.fromEntries(new FormData(e.target));
      if (m) await api("PUT", "/api/members/" + m.id, { ...d, active: m.active }); else await api("POST", "/api/members", d);
      closeModal(); toast(m ? "Member updated" : "Member added"); route();
    });
  };
  $("#add").onclick = () => form("Add member");
  view.querySelector(".panel").onclick = safe(async e => {
    const { edit, toggle, del } = e.target.dataset;
    const m = members.find(x => x.id == (edit || toggle || del));
    if (edit) form("Edit member", m);
    if (toggle) { await api("PUT", "/api/members/" + m.id, { name: m.name, email: m.email, active: !m.active }); toast("Status changed"); route(); }
    if (del && confirm("Delete this member?")) { await api("DELETE", "/api/members/" + del); toast("Member deleted"); route(); }
  });
};

pages.lending = async view => {
  const [books, members, loans] = await Promise.all([api("GET", "/api/books"), api("GET", "/api/members"), api("GET", "/api/loans")]);
  const titleOf = id => (books.find(b => b.id === id) || {}).title || "Book #" + id;
  const nameOf = id => (members.find(m => m.id === id) || {}).name || "Member #" + id;
  loans.sort((a, b) => b.id - a.id);
  view.innerHTML = `<div class="bar"><span class="grow"></span><button class="b p" id="issue">Issue a book</button></div>
    <div class="panel">${table([
      { h: "#", k: "id" }, { h: "Book", k: "bookTitle", w: 1 }, { h: "Member", k: "memberName", w: 1 },
      { h: "Issued", k: "issueDate" }, { h: "Due", k: "dueDate" }, { h: "Returned", f: l => esc(l.returnDate || "-") },
      { h: "Status", f: l => l.status === "RETURNED" ? '<span class="tag ok">Returned</span>' : l.status === "FAILED" ? `<span class="tag bad" title="${esc(l.failureReason)}">Failed</span>` : l.status === "PENDING" ? '<span class="tag warn">Pending</span>' : isOverdue(l) ? '<span class="tag bad">Overdue</span>' : '<span class="tag warn">Issued</span>' }
    ], loans, l => (l.status === "ISSUED" ? `<button class="b s" data-ret="${l.id}">Return</button>` : "") +
      `<button class="b s" data-fine="${l.id}">Fine</button><button class="b s" data-hist="${l.id}">History</button>` +
      (l.status === "ISSUED" ? `<button class="b s" data-late="${l.id}" title="Demo: make this loan 20 days overdue">Make overdue</button>` : ""))}</div>`;
  $("#issue").onclick = () => {
    const free = books.filter(b => b.availableCopies > 0), act = members.filter(m => m.active);
    const opts = (term) => free.filter(b => b.title.toLowerCase().includes(term.toLowerCase())).slice(0, 50)
      .map(b => `<option value="${b.id}">${esc(b.title)} (${b.availableCopies} left)</option>`).join("");
    const s = openModal("Issue a book", `<form id="f">
      <label>Book (type to search, showing up to 50)<input id="bq" placeholder="e.g. Hobbit"><select name="bookId" id="bsel" required>${opts("")}</select></label>
      <label>Member<select name="memberId" required>${act.map(m => `<option value="${m.id}">${esc(m.name)}</option>`).join("")}</select></label>
      <div class="row"><button type="button" class="b" id="cancel">Cancel</button><button class="b p">Issue</button></div></form>`);
    $("#cancel", s).onclick = closeModal;
    $("#bq", s).oninput = e => { $("#bsel", s).innerHTML = opts(e.target.value); };
    $("#f", s).onsubmit = safe(async e => {
      e.preventDefault();
      const d = Object.fromEntries(new FormData(e.target));
      const loan = await api("POST", "/api/loans/issue", { bookId: +d.bookId, memberId: +d.memberId });
      closeModal(); toast(loan.status === "PENDING" ? "Accepted: a service is unavailable, the loan will complete automatically" : "Issued. Due on " + loan.dueDate); route();
    });
  };
  view.querySelector(".panel").onclick = safe(async e => {
    const { ret, fine, hist, late } = e.target.dataset;
    if (ret) { await api("POST", `/api/loans/${ret}/return`); toast("Book returned"); route(); }
    if (late) { await api("POST", `/api/loans/${late}/simulate-overdue?days=20`); toast("Loan moved 20 days into the past"); route(); }
    if (fine) { const f = await api("POST", `/api/fines/calculate/${fine}`); toast(`Fine of ₹${Number(f.amount).toFixed(2)} recorded (${f.daysOverdue} days)`); }
    if (hist) {
      const ev = await api("GET", `/api/loans/${hist}/events`);
      const s = openModal("Loan #" + hist + " history", `<ul class="timeline">${ev.map(x => `<li><strong>${esc(x.type.replace("_", " "))}</strong><small>${esc(new Date(x.occurredAt).toLocaleString())} &middot; ${esc(x.details)}</small></li>`).join("")}</ul><div class="row"><button class="b" id="cancel">Close</button></div>`);
      $("#cancel", s).onclick = closeModal;
    }
  });
};

pages.fines = async view => {
  const [fines, members] = await Promise.all([api("GET", "/api/fines"), api("GET", "/api/members")]);
  const nameOf = id => (members.find(m => m.id === id) || {}).name || "Member #" + id;
  view.innerHTML = `<div class="panel">${table([
    { h: "Fine #", k: "id" }, { h: "Loan #", k: "loanId" }, { h: "Member", f: f => esc(nameOf(f.memberId)) },
    { h: "Days late", k: "daysOverdue" }, { h: "Amount", f: f => "₹" + Number(f.amount).toFixed(2) },
    { h: "Status", f: f => f.paid ? '<span class="tag ok">Paid</span>' : '<span class="tag bad">Unpaid</span>' }
  ], fines, f => f.paid ? "" : `<button class="b s" data-pay="${f.id}">Mark paid</button>`)}</div>
  <p class="empty">Fines are created from the Lending page (use <em>Make overdue</em> then <em>Fine</em> to try it).</p>`;
  view.querySelector(".panel").onclick = safe(async e => {
    if (e.target.dataset.pay) { await api("PUT", `/api/fines/${e.target.dataset.pay}/pay`); toast("Fine marked paid"); route(); }
  });
};

pages.notifications = async view => {
  const list = await api("GET", "/api/notifications");
  const tag = t => t === "FINE_ASSESSED" ? '<span class="tag bad">Fine</span>' : t === "LOAN_RETURNED" ? '<span class="tag ok">Returned</span>' : '<span class="tag warn">Issued</span>';
  view.innerHTML = `<div class="panel"><h2>Messages sent by notification-service</h2>
    <p class="empty" style="padding-top:0">These are created asynchronously: lending-service and fine-service publish events to RabbitMQ and this service reacts.</p>${table([
    { h: "When", f: n => esc(new Date(n.createdAt).toLocaleString()) }, { h: "Type", f: n => tag(n.type) },
    { h: "Message", f: n => `<span style="white-space:normal">${esc(n.message)}</span>` }], list)}</div>`;
};

pages.myloans = async view => {
  const loans = (await api("GET", "/api/loans/member/" + session.memberId)).sort((x, y) => y.id - x.id);
  const out = loans.filter(l => l.status === "ISSUED");
  view.innerHTML = `<section class="hero small"><div><h2>Hello, ${esc(firstName())}</h2><p>You have ${out.length} book${out.length === 1 ? "" : "s"} out${out.filter(isOverdue).length ? ", " + out.filter(isOverdue).length + " overdue" : ""}.</p></div></section>
    <div class="panel">${table([
    { h: "Book", k: "bookTitle", w: 1 }, { h: "Issued", k: "issueDate" }, { h: "Due", k: "dueDate" }, { h: "Returned", f: l => esc(l.returnDate || "-") },
    { h: "Status", f: l => l.status === "RETURNED" ? '<span class="tag ok">Returned</span>' : isOverdue(l) ? '<span class="tag bad">Overdue</span>' : '<span class="tag warn">' + esc(l.status) + '</span>' }
  ], loans)}</div>`;
};

pages.myfines = async view => {
  const fines = await api("GET", "/api/fines/member/" + session.memberId);
  view.innerHTML = `<div class="panel">${table([
    { h: "Loan #", k: "loanId" }, { h: "Days late", k: "daysOverdue" }, { h: "Amount", f: f => "₹" + Number(f.amount).toFixed(2) },
    { h: "Status", f: f => f.paid ? '<span class="tag ok">Paid</span>' : '<span class="tag bad">Unpaid</span>' }
  ], fines)}</div>`;
};

pages.mynotes = async view => {
  const list = await api("GET", "/api/notifications/member/" + session.memberId);
  view.innerHTML = `<div class="panel">${table([
    { h: "When", f: n => esc(new Date(n.createdAt).toLocaleString()) }, { h: "Message", f: n => `<span style="white-space:normal">${esc(n.message)}</span>` }], list)}</div>`;
};

pages.system = async view => {
  const services = [
    ["API Gateway", "/gateway-health"], ["Book Service", "/api/books"], ["Member Service", "/api/members"],
    ["Lending Service", "/api/loans"], ["Fine Service", "/api/fines"], ["Notification Service", "/api/notifications"]
  ];
  const results = await Promise.all(services.map(async ([n, u]) => {
    const t = performance.now();
    try { const r = await fetch(u, { headers: { Authorization: "Bearer " + session.token } }); return [n, r.ok, Math.round(performance.now() - t)]; } catch { return [n, false, 0]; }
  }));
  view.innerHTML = `<div class="panel"><h2>Service health (checked through the gateway)</h2>${results.map(([n, ok, ms]) =>
    `<div class="svc"><span>${esc(n)}</span><span>${ok ? `<small>${ms} ms</small> <span class="tag ok">Up</span>` : '<span class="tag bad">Down</span>'}</span></div>`).join("")}</div>
    <div class="panel"><h2>Architecture</h2><p>This UI talks only to the API Gateway. The gateway discovers services through Eureka and routes <code>/api/books</code>, <code>/api/members</code>, <code>/api/loans</code> and <code>/api/fines</code>. Lending calls Book and Member over REST (circuit-breaker protected). Lending and Fines publish events to RabbitMQ; Fines and Notification consume them.</p>
    <p><button class="b" id="re">Re-check</button></p></div>`;
  $("#re").onclick = route;
};

/* ---------- router ---------- */
const titles = { dashboard: "Dashboard", books: "Books", members: "Members", lending: "Lending", fines: "Fines", notifications: "Notifications", system: "System status",
  myloans: "My loans", myfines: "My fines", mynotes: "My notifications" };
const NAV = {
  LIBRARIAN: [["dashboard", "Dashboard", "&#128202;"], ["books", "Books", "&#128218;"], ["members", "Members", "&#128101;"], ["lending", "Lending", "&#128257;"],
    ["fines", "Fines", "&#128176;"], ["notifications", "Notifications", "&#128276;"], ["system", "System", "&#129658;"]],
  MEMBER: [["books", "Books", "&#128218;"], ["myloans", "My loans", "&#128214;"], ["myfines", "My fines", "&#128176;"], ["mynotes", "My notifications", "&#128276;"]]
};

function buildNav() {
  const items = NAV[session.role] || [];
  $("#nav").innerHTML = items.map(([r, t, i]) => `<a href="#/${r}" data-r="${r}"><span class="ni">${i}</span>${esc(t)}</a>`).join("");
  $("#who").innerHTML = `<div class="av">${esc(firstName().charAt(0))}</div><div class="nm"><b>${esc(session.username)}</b><span>${esc(session.role.toLowerCase())}</span></div><button class="b s" id="logout">Sign out</button>`;
  $("#logout").onclick = () => { saveSession(null); showLogin(""); };
}

function showLogin(msg) {
  $("#loginErr").textContent = msg || "";
  $("#login").hidden = false;
  $("#nav").innerHTML = "";
  $("#who").innerHTML = "";
  $("#view").innerHTML = "";
  const f = $("#loginForm").elements.username;
  if (f) f.focus();
}

$("#loginForm").onsubmit = async e => {
  e.preventDefault();
  const d = Object.fromEntries(new FormData(e.target));
  try {
    const res = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(d) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { $("#loginErr").textContent = data.message || "Sign-in failed"; return; }
    saveSession(data);
    e.target.reset();
    $("#login").hidden = true;
    buildNav();
    location.hash = "#/" + NAV[data.role][0][0];
    route();
  } catch (err) { $("#loginErr").textContent = "Could not reach the server"; }
};

async function route() {
  if (!session) { showLogin(""); return; }
  const allowed = (NAV[session.role] || []).map(x => x[0]);
  let name = location.hash.replace(/^#\//, "") || allowed[0];
  if (!allowed.includes(name) || !pages[name]) name = allowed[0];
  document.querySelectorAll("#nav a").forEach(a => a.classList.toggle("on", a.dataset.r === name));
  $("#title").textContent = titles[name];
  $("#side").classList.remove("open");
  const view = $("#view");
  view.innerHTML = `<div class="empty">Loading...</div>`;
  try { await pages[name](view); }
  catch (e) { view.innerHTML = `<div class="panel"><span class="tag bad">Error</span> ${esc(e.message)}</div>`; }
}
$("#menu").onclick = () => $("#side").classList.toggle("open");
window.addEventListener("hashchange", route);
if (session) { $("#login").hidden = true; buildNav(); }
route();
