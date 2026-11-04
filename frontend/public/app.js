"use strict";

/* ---------- helpers ---------- */
const $ = (s, r = document) => r.querySelector(s);
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const today = () => new Date().toISOString().slice(0, 10);

async function api(method, path, body) {
  const res = await fetch(path, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
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
  if (!rows.length) return `<div class="empty">Nothing here yet.</div>`;
  const head = cols.map(c => `<th>${esc(c.h)}</th>`).join("") + (actions ? "<th></th>" : "");
  const body = rows.map(r => `<tr>${cols.map(c => `<td>${c.f ? c.f(r) : esc(r[c.k])}</td>`).join("")}${actions ? `<td class="act">${actions(r)}</td>` : ""}</tr>`).join("");
  return `<div class="tw"><table><tr>${head}</tr>${body}</table></div>`;
}

const isOverdue = l => l.status === "ISSUED" && l.dueDate < today();

/* ---------- pages ---------- */
const pages = {};

pages.dashboard = async view => {
  const [books, members, loans, fines] = await Promise.all([api("GET", "/api/books"), api("GET", "/api/members"), api("GET", "/api/loans"), api("GET", "/api/fines")]);
  const active = loans.filter(l => l.status === "ISSUED");
  const overdue = active.filter(isOverdue);
  const unpaid = fines.filter(f => !f.paid).reduce((s, f) => s + Number(f.amount), 0);
  const titleOf = id => (books.find(b => b.id === id) || {}).title || "Book #" + id;
  const nameOf = id => (members.find(m => m.id === id) || {}).name || "Member #" + id;
  const stat = (n, l) => `<div class="stat"><div class="n">${esc(n)}</div><div class="l">${esc(l)}</div></div>`;
  view.innerHTML = `<div class="cards">
      ${stat(books.length, "Book titles")}
      ${stat(books.reduce((s, b) => s + b.availableCopies, 0) + " / " + books.reduce((s, b) => s + b.totalCopies, 0), "Copies available")}
      ${stat(members.length, "Members")}
      ${stat(active.length, "Books on loan")}
      ${stat(overdue.length, "Overdue loans")}
      ${stat("₹" + unpaid.toFixed(2), "Unpaid fines")}
    </div>
    <div class="panel"><h2>Currently on loan</h2>${table([
      { h: "Book", k: "bookTitle" }, { h: "Member", k: "memberName" },
      { h: "Due", k: "dueDate" }, { h: "Status", f: l => isOverdue(l) ? '<span class="tag bad">Overdue</span>' : '<span class="tag ok">On time</span>' }
    ], active)}</div>`;
};

pages.books = async view => {
  let books = await api("GET", "/api/books");
  let q = "";
  const draw = () => {
    const rows = books.filter(b => (b.title + " " + b.author + " " + b.isbn + " " + (b.category || "")).toLowerCase().includes(q.toLowerCase()));
    $("#list").innerHTML = table([
      { h: "Title", k: "title" }, { h: "Author", k: "author" }, { h: "Category", k: "category" }, { h: "ISBN", k: "isbn" },
      { h: "Available", f: b => b.availableCopies > 0 ? `<span class="tag ok">${b.availableCopies} / ${b.totalCopies}</span>` : `<span class="tag bad">0 / ${b.totalCopies}</span>` }
    ], rows, b => `<button class="b s" data-edit="${b.id}">Edit</button><button class="b s d" data-del="${b.id}">Delete</button>`);
  };
  view.innerHTML = `<div class="bar"><input id="q" type="search" placeholder="Search title, author, category or ISBN"><span class="grow"></span><button class="b p" id="add">Add book</button></div><div class="panel" id="list"></div>`;
  draw();
  $("#q").oninput = e => { q = e.target.value; draw(); };
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
  $("#add").onclick = () => form("Add book");
  $("#list").onclick = safe(async e => {
    const edit = e.target.dataset.edit, del = e.target.dataset.del;
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
      { h: "#", k: "id" }, { h: "Book", k: "bookTitle" }, { h: "Member", k: "memberName" },
      { h: "Issued", k: "issueDate" }, { h: "Due", k: "dueDate" }, { h: "Returned", f: l => esc(l.returnDate || "-") },
      { h: "Status", f: l => l.status === "RETURNED" ? '<span class="tag ok">Returned</span>' : isOverdue(l) ? '<span class="tag bad">Overdue</span>' : '<span class="tag warn">Issued</span>' }
    ], loans, l => (l.status === "ISSUED" ? `<button class="b s" data-ret="${l.id}">Return</button>` : "") +
      `<button class="b s" data-fine="${l.id}">Fine</button><button class="b s" data-hist="${l.id}">History</button>` +
      (l.status === "ISSUED" ? `<button class="b s" data-late="${l.id}" title="Demo: make this loan 20 days overdue">Make overdue</button>` : ""))}</div>`;
  $("#issue").onclick = () => {
    const free = books.filter(b => b.availableCopies > 0), act = members.filter(m => m.active);
    const s = openModal("Issue a book", `<form id="f">
      <label>Book<select name="bookId" required>${free.map(b => `<option value="${b.id}">${esc(b.title)} (${b.availableCopies} left)</option>`).join("")}</select></label>
      <label>Member<select name="memberId" required>${act.map(m => `<option value="${m.id}">${esc(m.name)}</option>`).join("")}</select></label>
      <div class="row"><button type="button" class="b" id="cancel">Cancel</button><button class="b p">Issue</button></div></form>`);
    $("#cancel", s).onclick = closeModal;
    $("#f", s).onsubmit = safe(async e => {
      e.preventDefault();
      const d = Object.fromEntries(new FormData(e.target));
      const loan = await api("POST", "/api/loans/issue", { bookId: +d.bookId, memberId: +d.memberId });
      closeModal(); toast("Issued. Due on " + loan.dueDate); route();
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

pages.system = async view => {
  const services = [
    ["API Gateway", "/gateway-health"], ["Book Service", "/api/books"], ["Member Service", "/api/members"],
    ["Lending Service", "/api/loans"], ["Fine Service", "/api/fines"], ["Notification Service", "/api/notifications"]
  ];
  const results = await Promise.all(services.map(async ([n, u]) => {
    const t = performance.now();
    try { const r = await fetch(u); return [n, r.ok, Math.round(performance.now() - t)]; } catch { return [n, false, 0]; }
  }));
  view.innerHTML = `<div class="panel"><h2>Service health (checked through the gateway)</h2>${results.map(([n, ok, ms]) =>
    `<div class="svc"><span>${esc(n)}</span><span>${ok ? `<small>${ms} ms</small> <span class="tag ok">Up</span>` : '<span class="tag bad">Down</span>'}</span></div>`).join("")}</div>
    <div class="panel"><h2>Architecture</h2><p>This UI talks only to the API Gateway. The gateway discovers services through Eureka and routes <code>/api/books</code>, <code>/api/members</code>, <code>/api/loans</code> and <code>/api/fines</code>. Lending calls Book and Member over REST (circuit-breaker protected). Lending and Fines publish events to RabbitMQ; Fines and Notification consume them.</p>
    <p><button class="b" id="re">Re-check</button></p></div>`;
  $("#re").onclick = route;
};

/* ---------- router ---------- */
const titles = { dashboard: "Dashboard", books: "Books", members: "Members", lending: "Lending", fines: "Fines", notifications: "Notifications", system: "System status" };

async function route() {
  const name = (location.hash.replace(/^#\//, "") || "dashboard");
  const page = pages[name] ? name : "dashboard";
  document.querySelectorAll("#nav a").forEach(a => a.classList.toggle("on", a.dataset.r === page));
  $("#title").textContent = titles[page];
  $("#side").classList.remove("open");
  const view = $("#view");
  view.innerHTML = `<div class="empty">Loading...</div>`;
  try { await pages[page](view); }
  catch (e) { view.innerHTML = `<div class="panel"><span class="tag bad">Error</span> ${esc(e.message)}</div>`; }
}
$("#menu").onclick = () => $("#side").classList.toggle("open");
window.addEventListener("hashchange", route);
route();
