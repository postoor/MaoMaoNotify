"use strict";
// MaoMaoNotify Web Admin (§70). Vanilla JS SPA, no build step. Talks to the
// same-origin REST API at /api/v1.

const API = "/api/v1";
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Hand-drawn cat mark (matches the app icon).
const cat = (px) => `<svg viewBox="0 0 120 120" width="${px}" height="${px}" style="flex:none;vertical-align:middle">
  <path d="M33 46 L35 15 L60 39 Z" fill="#1C1B1A"/><path d="M87 46 L85 15 L60 39 Z" fill="#1C1B1A"/>
  <path d="M60 32 C41 32 25 42 25 63 C25 88 40 105 60 105 C80 105 95 88 95 63 C95 42 79 32 60 32 Z" fill="#1C1B1A"/>
  <ellipse cx="46" cy="64" rx="10.5" ry="12.5" fill="#E3A02E"/><ellipse cx="74" cy="64" rx="10.5" ry="12.5" fill="#E3A02E"/>
  <circle cx="46" cy="65" r="6.2" fill="#141312"/><circle cx="74" cy="65" r="6.2" fill="#141312"/>
  <circle cx="43.6" cy="61.4" r="2" fill="#FFFDF7"/><circle cx="71.6" cy="61.4" r="2" fill="#FFFDF7"/>
  <path d="M56 82 L64 82 L60 87 Z" fill="#B98A86"/></svg>`;

const store = {
  get access() { return localStorage.getItem("mm_access"); },
  get refresh() { return localStorage.getItem("mm_refresh"); },
  set(a, r) { localStorage.setItem("mm_access", a); localStorage.setItem("mm_refresh", r); },
  clear() { localStorage.removeItem("mm_access"); localStorage.removeItem("mm_refresh"); },
};

let me = null;

function toast(msg, isErr = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = isErr ? "err" : "";
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.hidden = true), 3200);
}

async function api(path, { method = "GET", body, auth = true, retry = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && store.access) headers.Authorization = `Bearer ${store.access}`;
  const resp = await fetch(API + path, {
    method, headers, body: body != null ? JSON.stringify(body) : undefined,
  });
  if (resp.status === 401 && auth && retry && store.refresh) {
    const r = await fetch(`${API}/auth/refresh`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: store.refresh }),
    });
    if (r.ok) {
      const t = await r.json();
      store.set(t.access_token, t.refresh_token);
      return api(path, { method, body, auth, retry: false });
    }
    store.clear();
    renderLogin();
    throw new Error("Session expired");
  }
  const data = resp.status === 204 ? null : await resp.json().catch(() => null);
  if (!resp.ok) throw new Error(data?.error?.message || `HTTP ${resp.status}`);
  return data;
}

// ---- Login ----

function renderLogin() {
  me = null;
  document.getElementById("app").innerHTML = `
    <div class="login card">
      <div style="display:flex; flex-direction:column; align-items:center; gap:6px; margin-bottom:10px;">
        ${cat(72)}
        <h1 style="margin:0;">MaoMaoNotify Admin</h1>
      </div>
      <label>Email</label><input id="email" type="email" />
      <label>Password</label><input id="password" type="password" />
      <div class="spacer"></div>
      <button class="primary" id="loginBtn">Log in</button>
    </div>`;
  $("#loginBtn").onclick = async () => {
    try {
      const t = await api("/auth/login", {
        method: "POST", auth: false,
        body: { email: $("#email").value.trim(), password: $("#password").value },
      });
      store.set(t.access_token, t.refresh_token);
      await boot();
    } catch (e) { toast(e.message, true); }
  };
}

// ---- Shell ----

const TABS = [
  { id: "devices", label: "Devices" },
  { id: "agents", label: "Agents" },
  { id: "prefs", label: "Preferences" },
  { id: "voice", label: "Voice Settings" },
  { id: "history", label: "Notifications" },
  { id: "tts", label: "Server TTS", admin: true },
  { id: "users", label: "User Management", admin: true },
];

function renderShell(active) {
  const isAdmin = me?.role === "admin";
  document.getElementById("app").innerHTML = `
    <div class="shell">
      <nav>
        <div class="brand">${cat(28)} MaoMaoNotify</div>
        ${TABS.map((t) => `<a data-tab="${t.id}"
            class="${t.id === active ? "active" : ""} ${t.admin && !isAdmin ? "hidden" : ""}">${t.label}</a>`).join("")}
        <div class="spacer"></div>
        <a id="logout">Log out (${esc(me?.email || "")})</a>
      </nav>
      <main id="main"></main>
    </div>`;
  document.querySelectorAll("nav a[data-tab]").forEach((a) => {
    a.onclick = () => renderShell(a.dataset.tab) || views[a.dataset.tab]($("#main"));
  });
  $("#logout").onclick = () => { store.clear(); renderLogin(); };
  views[active]($("#main"));
}

const views = { devices, agents, prefs, voice, history, tts, users };

// ---- Devices ----

async function devices(main) {
  main.innerHTML = `<h2>Devices</h2>
    <div class="row"><button class="primary" id="pair">Generate pairing code</button></div>
    <div id="pairbox"></div><div id="list" class="muted">Loading…</div>`;
  $("#pair").onclick = async () => {
    try {
      const p = await api("/devices/pairing", { method: "POST" });
      $("#pairbox").innerHTML = `<div class="secret">Pairing code: <b>${esc(p.code)}</b>
        &nbsp; token: <span class="mono">${esc(p.token)}</span><br>expires: ${esc(p.expires_at)}</div>`;
    } catch (e) { toast(e.message, true); }
  };
  const rows = await api("/devices");
  $("#list").innerHTML = rows.length ? `<table><thead><tr>
      <th>Name</th><th>Platform</th><th>Last seen</th><th></th></tr></thead><tbody>
    ${rows.map((d) => `<tr>
      <td>${esc(d.display_name || d.detected_name || "(unnamed)")}<div class="mono">${esc(d.id)}</div></td>
      <td><span class="pill">${esc(d.platform)}</span> ${esc(d.architecture || "")}</td>
      <td>${esc(d.last_seen_at || "never")}</td>
      <td class="row"><button data-rename="${esc(d.id)}">Rename</button>
        <button class="danger" data-del="${esc(d.id)}">Delete</button></td>
    </tr>`).join("")}</tbody></table>` : `<p class="muted">No devices paired.</p>`;
  main.querySelectorAll("[data-rename]").forEach((b) => b.onclick = async () => {
    const name = prompt("New display name:");
    if (!name) return;
    try { await api(`/devices/${b.dataset.rename}`, { method: "PATCH", body: { display_name: name } }); devices(main); }
    catch (e) { toast(e.message, true); }
  });
  main.querySelectorAll("[data-del]").forEach((b) => b.onclick = async () => {
    if (!confirm("Delete this device?")) return;
    try { await api(`/devices/${b.dataset.del}`, { method: "DELETE" }); devices(main); }
    catch (e) { toast(e.message, true); }
  });
}

// ---- Agents ----

const SCOPES = ["notification:send", "notification:read", "action:receive",
  "presence:read", "notification:broadcast", "notification:target_device"];

async function agents(main) {
  main.innerHTML = `<h2>Agents</h2>
    <div class="card"><h3>New agent</h3>
      <label>Name</label><input id="agentName" placeholder="Claude Code" />
      <label>Scopes</label>
      <div class="row">${SCOPES.map((s) => `<label style="margin:0"><input type="checkbox" value="${s}"
        ${["notification:send", "notification:read", "action:receive"].includes(s) ? "checked" : ""}
        style="width:auto"> ${s}</label>`).join("")}</div>
      <div class="spacer"></div><button class="primary" id="createAgent">Create</button>
      <div id="agentSecret"></div>
    </div><div class="spacer"></div><div id="alist" class="muted">Loading…</div>`;
  $("#createAgent").onclick = async () => {
    const scopes = [...main.querySelectorAll('.card input[type=checkbox]:checked')].map((c) => c.value);
    try {
      const a = await api("/agents", { method: "POST", body: { name: $("#agentName").value.trim(), scopes } });
      $("#agentSecret").innerHTML = `<div class="secret">Token (shown once):<br>
        <span class="mono">${esc(a.token)}</span></div>`;
      agentList();
    } catch (e) { toast(e.message, true); }
  };
  async function agentList() {
    const rows = await api("/agents");
    $("#alist").innerHTML = rows.length ? `<table><thead><tr>
      <th>Name</th><th>ID</th><th>Webhooks</th><th></th></tr></thead><tbody>
      ${rows.map((a) => `<tr>
        <td>${esc(a.name)}</td><td class="mono">${esc(a.id)}</td>
        <td><button data-wh="${esc(a.id)}">Add webhook</button></td>
        <td><button class="danger" data-adel="${esc(a.id)}">Delete</button></td>
      </tr>`).join("")}</tbody></table>` : `<p class="muted">No agents.</p>`;
    main.querySelectorAll("[data-adel]").forEach((b) => b.onclick = async () => {
      if (!confirm("Delete agent?")) return;
      try { await api(`/agents/${b.dataset.adel}`, { method: "DELETE" }); agentList(); }
      catch (e) { toast(e.message, true); }
    });
    main.querySelectorAll("[data-wh]").forEach((b) => b.onclick = async () => {
      const url = prompt("Webhook URL:");
      if (!url) return;
      try {
        const w = await api(`/agents/${b.dataset.wh}/webhooks`, { method: "POST", body: { url, events: ["notification.responded"] } });
        $("#agentSecret").innerHTML = `<div class="secret">Webhook secret (shown once):<br>
          <span class="mono">${esc(w.secret)}</span></div>`;
      } catch (e) { toast(e.message, true); }
    });
  }
  agentList();
}

// ---- Preferences (manual presence + quiet hours) ----

async function prefs(main) {
  const p = await api("/preferences");
  const q = p.quiet_hours || {};
  main.innerHTML = `<h2>Preferences</h2><div class="card">
    <label>Manual presence (§19)</label>
    <select id="mp">${["auto", "available", "busy", "away", "do_not_disturb"]
      .map((v) => `<option ${v === p.manual_presence ? "selected" : ""}>${v}</option>`).join("")}</select>
    <h3 style="margin-top:20px">Quiet Hours (§20)</h3>
    <label><input type="checkbox" id="qEnabled" ${q.enabled ? "checked" : ""} style="width:auto"> Enabled</label>
    <div class="row">
      <div><label>Start</label><input id="qStart" value="${esc(q.start || "23:00")}"></div>
      <div><label>End</label><input id="qEnd" value="${esc(q.end || "08:00")}"></div>
      <div><label>Timezone</label><input id="qTz" value="${esc(q.timezone || "Asia/Taipei")}"></div>
    </div>
    <div class="spacer"></div><button class="primary" id="savePrefs">Save</button>
  </div>`;
  $("#savePrefs").onclick = async () => {
    try {
      await api("/preferences", { method: "PATCH", body: {
        manual_presence: $("#mp").value,
        quiet_hours: { enabled: $("#qEnabled").checked, start: $("#qStart").value,
          end: $("#qEnd").value, timezone: $("#qTz").value },
      }});
      toast("Preferences saved");
    } catch (e) { toast(e.message, true); }
  };
}

// ---- Voice Settings (per-device voice policy, §37) ----

async function voice(main) {
  const devs = await api("/devices");
  main.innerHTML = `<h2>Voice Settings</h2>
    ${devs.length ? `<div class="card">
      <label>Device</label>
      <select id="vdev">${devs.map((d) => `<option value="${esc(d.id)}">${esc(d.display_name || d.platform)} (${esc(d.id)})</option>`).join("")}</select>
      <label>Voice policy (JSON, §37)</label>
      <textarea id="vpol" rows="10" class="mono"></textarea>
      <div class="spacer"></div><button class="primary" id="saveVoice">Save</button>
    </div>` : `<p class="muted">No devices. Pair a device first.</p>`}`;
  if (!devs.length) return;
  async function load() {
    const p = await api(`/devices/${$("#vdev").value}/preferences`);
    $("#vpol").value = JSON.stringify(p.voice_policy || {}, null, 2);
  }
  $("#vdev").onchange = load;
  await load();
  $("#saveVoice").onclick = async () => {
    let policy;
    try { policy = JSON.parse($("#vpol").value || "{}"); }
    catch { return toast("Invalid JSON", true); }
    try {
      await api(`/devices/${$("#vdev").value}/preferences`, { method: "PATCH", body: { voice_policy: policy } });
      toast("Voice policy saved");
    } catch (e) { toast(e.message, true); }
  };
}

// ---- Notification history ----

async function history(main) {
  const rows = await api("/notifications");
  main.innerHTML = `<h2>Notification History</h2>
    ${rows.length ? `<table><thead><tr><th>Created</th><th>Type</th><th>Priority</th>
      <th>Title</th><th>Message</th><th>Status</th><th>Read</th></tr></thead><tbody>
      ${rows.map((n) => `<tr>
        <td>${esc((n.created_at || "").slice(0, 19))}</td>
        <td>${esc(n.type)}</td><td>${esc(n.priority)}</td>
        <td>${esc(n.title || "")}</td><td>${esc(n.message || "")}</td>
        <td><span class="pill">${esc(n.status)}</span></td>
        <td>${n.read_at ? "✓" : ""}</td></tr>`).join("")}</tbody></table>`
      : `<p class="muted">No notifications yet.</p>`}`;
}

// ---- Server TTS settings (admin) ----

async function tts(main) {
  const s = await api("/admin/settings/tts");
  main.innerHTML = `<h2>Server TTS Settings</h2><div class="card">
    <p class="muted">Env default: <b>${esc(s.default_from_env)}</b> · Fallback: <b>${esc(s.fallback_provider)}</b></p>
    <label>Default provider (§29)</label>
    <select id="prov">${s.available.map((p) => `<option ${p === s.provider ? "selected" : ""}>${p}</option>`).join("")}</select>
    <div class="spacer"></div><button class="primary" id="saveTts">Save</button>
  </div>`;
  $("#saveTts").onclick = async () => {
    try { await api("/admin/settings/tts", { method: "PATCH", body: { provider: $("#prov").value } }); toast("TTS provider updated"); }
    catch (e) { toast(e.message, true); }
  };
}

// ---- User management (admin) ----

async function users(main) {
  main.innerHTML = `<h2>User Management</h2>
    <div class="card"><h3>New user</h3>
      <div class="row">
        <div style="flex:1"><label>Email</label><input id="uEmail" type="email"></div>
        <div style="flex:1"><label>Password</label><input id="uPass" type="password"></div>
        <div><label>Role</label><select id="uRole"><option>user</option><option>admin</option></select></div>
      </div>
      <div class="spacer"></div><button class="primary" id="createUser">Create</button>
    </div><div class="spacer"></div><div id="ulist" class="muted">Loading…</div>`;
  $("#createUser").onclick = async () => {
    try {
      await api("/admin/users", { method: "POST", body: {
        email: $("#uEmail").value.trim(), password: $("#uPass").value, role: $("#uRole").value } });
      toast("User created"); list();
    } catch (e) { toast(e.message, true); }
  };
  async function list() {
    const rows = await api("/admin/users");
    $("#ulist").innerHTML = `<table><thead><tr><th>Email</th><th>Role</th><th>Created</th><th></th></tr></thead><tbody>
      ${rows.map((u) => `<tr><td>${esc(u.email)}</td><td><span class="pill">${esc(u.role)}</span></td>
        <td>${esc((u.created_at || "").slice(0, 10))}</td>
        <td>${u.id === me.id ? '<span class="muted">you</span>'
          : `<button class="danger" data-udel="${esc(u.id)}">Delete</button>`}</td></tr>`).join("")}
      </tbody></table>`;
    main.querySelectorAll("[data-udel]").forEach((b) => b.onclick = async () => {
      if (!confirm("Delete user?")) return;
      try { await api(`/admin/users/${b.dataset.udel}`, { method: "DELETE" }); list(); }
      catch (e) { toast(e.message, true); }
    });
  }
  list();
}

// ---- Boot ----

async function boot() {
  try {
    me = await api("/me");
    renderShell("devices");
  } catch {
    renderLogin();
  }
}

if (store.access) boot(); else renderLogin();
