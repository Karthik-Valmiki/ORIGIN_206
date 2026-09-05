/* ═══════════════════════════════════════════════════════════════
   LMPC Verification System – Frontend Application
   API Base: http://localhost:8000
═══════════════════════════════════════════════════════════════ */

const API = "http://localhost:8000/api/v1";

/* ─── State ─────────────────────────────────────────────────── */
let STATE = {
  token: localStorage.getItem("lmpc_token") || null,
  user: null,
  currentView: "dashboard",
  reviewTargetId: null,
  categories: [],
};

/* ═══════════════════════════════════════════════════════════════
   UTILITY HELPERS
═══════════════════════════════════════════════════════════════ */
async function apiFetch(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;

  let res;
  try {
    res = await fetch(API + path, { ...opts, headers });
  } catch (err) {
    throw new Error("Unable to reach backend server. Please verify the API is running at " + API);
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    if (typeof data.detail === "string") {
      msg = data.detail;
    } else if (Array.isArray(data.detail)) {
      msg = data.detail.map(d => d.msg || JSON.stringify(d)).join("; ");
    } else if (data.detail && typeof data.detail === "object") {
      msg = data.detail.message || JSON.stringify(data.detail);
    }
    throw new Error(msg);
  }
  return data;
}

function getUserRole(u) {
  if (!u) return "OFFICER";
  if (typeof u.role === "string" && u.role) return u.role.toUpperCase();
  if (Array.isArray(u.roles) && u.roles.length > 0) {
    const r = u.roles[0];
    return (typeof r === "object" ? r.role_name : r).toUpperCase();
  }
  return "OFFICER";
}

function showToast(msg, type = "") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast" + (type ? ` toast-${type}` : "");
  t.style.display = "block";
  setTimeout(() => { t.style.display = "none"; }, 3500);
}

function setLoading(btnId, loading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.querySelector(".btn-text").style.display = loading ? "none" : "";
  btn.querySelector(".spinner").style.display  = loading ? "inline-block" : "none";
  btn.disabled = loading;
}

function showError(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.style.display = "block";
}
function hideError(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "none";
}

function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function statusBadge(status) {
  const s = (status || "").toUpperCase();
  const map = {
    PENDING:         ["pending",        "Pending"],
    PROCESSING:      ["processing",     "Processing"],
    COMPLIANT:       ["approved",       "✓ Compliant"],
    NON_COMPLIANT:   ["rejected",       "✕ Non-Compliant"],
    PROCESSING_FAILED: ["submitted",    "Processing Failed"],
    // Finding-level statuses
    PASS:   ["approved",  "PASS"],
    FAIL:   ["rejected",  "FAIL"],
    INFO:   ["submitted", "INFO"],
  };
  const [cls, label] = map[s] || ["pending", s];
  return `<span class="badge badge-${cls}"><span class="badge-dot"></span>${label}</span>`;
}

function roleBadge(userOrRole) {
  const r = typeof userOrRole === "object" ? getUserRole(userOrRole) : (userOrRole || "").toUpperCase();
  return r === "ADMIN"
    ? `<span class="badge badge-admin">Admin</span>`
    : `<span class="badge badge-officer">Officer</span>`;
}

function activeBadge(active) {
  return active
    ? `<span class="badge badge-active">Active</span>`
    : `<span class="badge badge-inactive">Inactive</span>`;
}

function moniker(name) {
  if (!name) return "?";
  return name.split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase();
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

/* ═══════════════════════════════════════════════════════════════
   AUTH FLOW
═══════════════════════════════════════════════════════════════ */
/* ── Tab switcher (Login ↔ Register) ───────────────────────── */
function showAuthTab(tab) {
  const isLogin = tab === "login";
  document.getElementById("auth-login-panel").style.display    = isLogin ? "" : "none";
  document.getElementById("auth-register-panel").style.display = isLogin ? "none" : "";
  document.getElementById("tab-login").classList.toggle("active", isLogin);
  document.getElementById("tab-register").classList.toggle("active", !isLogin);
  // Clear any stale errors when switching tabs
  hideError(isLogin ? "register-error" : "login-error");
}

async function boot() {
  if (STATE.token) {
    // Try to resume existing session
    try {
      STATE.user = await apiFetch("/auth/me");
      enterApp();
      return;
    } catch {
      STATE.token = null;
      localStorage.removeItem("lmpc_token");
    }
  }
  // Always land on the Login tab
  showAuthTab("login");
}

/* ── Register (Officer self-registration) ───────────────────── */
document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError("register-error");

  const fullName = document.getElementById("reg-name").value.trim();
  const email    = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;

  if (password.length < 8) {
    showError("register-error", "Password must be at least 8 characters.");
    return;
  }

  setLoading("register-btn", true);
  try {
    await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({ full_name: fullName, email, password, role_name: "OFFICER" }),
    });
    showToast("Account created! Please sign in.", "success");
    showAuthTab("login");
    document.getElementById("login-email").value = email;
  } catch (err) {
    showError("register-error", err.message);
  } finally {
    setLoading("register-btn", false);
  }
});

/* ── Login ──────────────────────────────────────────────────── */
document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError("login-error");

  const emailInput = document.getElementById("login-email");
  const passwordInput = document.getElementById("login-password");
  const email = emailInput.value.trim();
  const password = passwordInput.value;

  if (!email || !password) {
    showError("login-error", "Please enter both email and password.");
    return;
  }

  setLoading("login-btn", true);
  emailInput.disabled = true;
  passwordInput.disabled = true;

  try {
    const data = await apiFetch("/auth/login/json", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    STATE.token = data.access_token;
    localStorage.setItem("lmpc_token", data.access_token);
    STATE.user = await apiFetch("/auth/me");
    enterApp();
  } catch (err) {
    showError("login-error", err.message);
  } finally {
    setLoading("login-btn", false);
    emailInput.disabled = false;
    passwordInput.disabled = false;
  }
});

// Clear login error dynamically as the user types
document.getElementById("login-email")?.addEventListener("input", () => hideError("login-error"));
document.getElementById("login-password")?.addEventListener("input", () => hideError("login-error"));

/* ── Mobile Sidebar Drawer ─────────────────────────────────── */
function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  if (sidebar.classList.contains("open")) {
    closeSidebar();
  } else {
    openSidebar();
  }
}

function openSidebar() {
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (sidebar) sidebar.classList.add("open");
  if (backdrop) backdrop.classList.add("visible");
  document.body.style.overflow = "hidden"; // Prevent body scroll while drawer is open
}

function closeSidebar() {
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (sidebar) sidebar.classList.remove("open");
  if (backdrop) backdrop.classList.remove("visible");
  document.body.style.overflow = "";
}

/* ── Enter App ─────────────────────────────────────────────── */
function enterApp() {
  document.getElementById("auth-overlay").style.display = "none";
  document.getElementById("app").style.display = "flex";

  const u = STATE.user;
  const userRole = getUserRole(u);
  const initials = moniker(u.full_name || u.email);

  document.getElementById("user-name-display").textContent  = u.full_name || u.email;
  document.getElementById("user-role-display").textContent  = userRole;
  document.getElementById("user-avatar-initials").textContent = initials;
  const mobileAvatar = document.getElementById("mobile-avatar");
  if (mobileAvatar) mobileAvatar.textContent = initials;

  document.getElementById("greeting-text").textContent = `${greeting()}, ${(u.full_name || "").split(" ")[0] || "Officer"}`;

  // Show/hide admin items on both desktop sidebar and mobile bottom nav
  if (userRole === "ADMIN") {
    document.querySelectorAll(".nav-item-admin, .bnav-admin").forEach(el => el.classList.remove("hidden"));
  } else {
    document.querySelectorAll(".nav-item-admin, .bnav-admin").forEach(el => el.classList.add("hidden"));
  }

  navigate("dashboard");
}

function logout() {
  closeSidebar();
  STATE.token = null;
  STATE.user = null;
  localStorage.removeItem("lmpc_token");
  document.querySelectorAll(".nav-item-admin, .bnav-admin").forEach(el => el.classList.add("hidden"));
  document.getElementById("app").style.display = "none";
  document.getElementById("auth-overlay").style.display = "flex";
  showAuthTab("login");
}

/* ═══════════════════════════════════════════════════════════════
   NAVIGATION
═══════════════════════════════════════════════════════════════ */
function navigate(view) {
  event?.preventDefault();
  closeSidebar();
  STATE.currentView = view;

  // Highlight desktop nav item
  document.querySelectorAll(".nav-item").forEach(el => {
    el.classList.toggle("active", el.id === `nav-${view}`);
  });

  // Highlight mobile bottom nav item
  document.querySelectorAll(".bnav-item").forEach(el => {
    el.classList.toggle("active", el.id === `bnav-${view}`);
  });

  // Show/hide views
  document.querySelectorAll(".view").forEach(el => {
    el.style.display = el.id === `view-${view}` ? "" : "none";
  });

  // Load data
  if (view === "dashboard")   loadDashboard();
  if (view === "inspections") loadInspections();
  if (view === "users")       loadUsers();
  if (view === "rules")       loadRules();
}

/* ═══════════════════════════════════════════════════════════════
   DASHBOARD
═══════════════════════════════════════════════════════════════ */
async function loadDashboard() {
  try {
    const inspections = await apiFetch("/inspections/?limit=100");
    const list = Array.isArray(inspections) ? inspections : (inspections.items || []);

    const counts = _countsByStatus(list);
    document.getElementById("stat-pending").textContent   = counts.PENDING + counts.PROCESSING;
    document.getElementById("stat-submitted").textContent = counts.PROCESSING;
    document.getElementById("stat-approved").textContent  = counts.COMPLIANT;
    document.getElementById("stat-rejected").textContent  = counts.NON_COMPLIANT;

    const recent = list.slice(0, 7);
    const tbody = document.getElementById("recent-tbody");
    tbody.innerHTML = recent.length ? recent.map(inspectionRow).join("") : emptyRow(5, "No inspections yet");
  } catch (err) {
    showToast("Could not load dashboard: " + err.message, "error");
  }
}

function _countsByStatus(list) {
  const c = { PENDING: 0, PROCESSING: 0, COMPLIANT: 0, NON_COMPLIANT: 0 };
  list.forEach(i => {
    const s = (i.status || "").toUpperCase();
    if (c[s] !== undefined) c[s]++;
  });
  return c;
}

function inspectionRow(i) {
  return `<tr>
    <td class="mono">${i.inspection_number || "—"}</td>
    <td>${i.product_category?.category_name || "—"}</td>
    <td>${statusBadge(i.status)}</td>
    <td>${fmtDate(i.created_at)}</td>
    <td><button class="btn btn-ghost" style="padding:5px 12px;font-size:.8rem;" onclick="openDetail('${i.id}')">View</button></td>
  </tr>`;
}

function emptyRow(cols, msg) {
  return `<tr><td colspan="${cols}" class="empty-cell">${msg}</td></tr>`;
}

/* ═══════════════════════════════════════════════════════════════
   INSPECTIONS
═══════════════════════════════════════════════════════════════ */
async function loadInspections() {
  const status = document.getElementById("status-filter")?.value || "";
  const tbody = document.getElementById("inspections-tbody");
  tbody.innerHTML = `<tr><td colspan="6" class="empty-cell"><span class="spinner-inline"></span> Loading…</td></tr>`;
  try {
    const qs = status ? `?status=${status}` : "";
    const inspections = await apiFetch(`/inspections/${qs}`);
    const list = Array.isArray(inspections) ? inspections : (inspections.items || []);

    tbody.innerHTML = list.length
      ? list.map(i => `<tr>
          <td class="mono">${i.inspection_number || "—"}</td>
          <td>${i.product_category?.category_name || "—"}</td>
          <td>${statusBadge(i.status)}</td>
          <td>${fmtDate(i.created_at)}</td>
          <td>${fmtDate(i.updated_at)}</td>
          <td><button class="btn btn-ghost" style="padding:5px 12px;font-size:.8rem;" onclick="openDetail('${i.id}')">View</button></td>
        </tr>`).join("")
      : emptyRow(6, "No inspections found");
  } catch (err) {
    tbody.innerHTML = emptyRow(6, `Error: ${err.message}`);
  }
}

/* ── New Inspection ─────────────────────────────────────────── */
async function openNewInspectionModal() {
  document.getElementById("insp-category").innerHTML = `<option value="">Loading categories…</option>`;
  openModal("modal-new-inspection");
  try {
    const cats = await apiFetch("/admin/categories");
    STATE.categories = Array.isArray(cats) ? cats : (cats.items || []);
    const sel = document.getElementById("insp-category");
    sel.innerHTML = `<option value="">Select a category…</option>` +
      STATE.categories.map(c => `<option value="${c.id}">${c.category_name}</option>`).join("");
  } catch (err) {
    console.error(err);
    document.getElementById("insp-category").innerHTML = `<option value="">Could not load categories</option>`;
  }
}

async function createInspection() {
  hideError("insp-error");
  const catId = document.getElementById("insp-category").value;
  if (!catId) { showError("insp-error", "Please select a product category."); return; }
  setLoading("create-insp-btn", true);
  try {
    await apiFetch("/inspections/", { method: "POST", body: JSON.stringify({ product_category_id: catId }) });
    showToast("Inspection created successfully.", "success");
    closeModal("modal-new-inspection");
    if (STATE.currentView === "dashboard") loadDashboard();
    else loadInspections();
  } catch (err) {
    showError("insp-error", err.message);
  } finally {
    setLoading("create-insp-btn", false);
  }
}

/* ── Polling state ──────────────────────────────────────────── */
let _pollTimer = null;

function _startPolling(inspectionId) {
  _stopPolling();
  _pollTimer = setInterval(async () => {
    try {
      const fresh = await apiFetch(`/inspections/${inspectionId}`);
      const s = (fresh.status || "").toUpperCase();
      if (s === "COMPLIANT" || s === "NON_COMPLIANT" || s === "PROCESSING_FAILED") {
        _stopPolling();
        // Reload the detail panel with final results
        openDetail(inspectionId);
        // Also refresh the list / dashboard in background
        if (STATE.currentView === "dashboard") loadDashboard();
        else loadInspections();
      }
    } catch (_) { /* ignore transient errors */ }
  }, 3000);
}

function _stopPolling() {
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

/* ── Inspection Detail ──────────────────────────────────────── */
async function openDetail(id) {
  _stopPolling();
  document.getElementById("detail-body").innerHTML = `<span class="spinner-inline"></span> Loading…`;
  document.getElementById("detail-footer").innerHTML = "";
  openModal("modal-inspection-detail");
  try {
    const i = await apiFetch(`/inspections/${id}`);
    document.getElementById("detail-title").textContent = i.inspection_number || "Inspection Details";
    document.getElementById("detail-sub").textContent   = i.product_category?.category_name || "";

    const statusUpper = (i.status || "").toUpperCase();
    const isProcessing    = statusUpper === "PROCESSING";
    const isCompliant     = statusUpper === "COMPLIANT";
    const isNonCompliant  = statusUpper === "NON_COMPLIANT";
    const isPending       = statusUpper === "PENDING";
    const hasImages       = Array.isArray(i.images) && i.images.length > 0;

    // ── Verdict Banner ───────────────────────────────────────────────────
    let verdictBanner = "";
    if (isCompliant) {
      verdictBanner = `
        <div class="verdict-banner verdict-compliant">
          <span class="verdict-icon">✓</span>
          <div>
            <div class="verdict-title">COMPLIANT</div>
            <div class="verdict-sub">All mandatory LMPC fields detected on this product label.</div>
          </div>
        </div>`;
    } else if (isNonCompliant) {
      const failedChecks = (i.findings || []).filter(f => f.status === "FAIL").map(f => f.details?.check || f.finding_type);
      verdictBanner = `
        <div class="verdict-banner verdict-noncompliant">
          <span class="verdict-icon">✕</span>
          <div>
            <div class="verdict-title">NON-COMPLIANT</div>
            <div class="verdict-sub">Missing mandatory fields: ${failedChecks.join(", ") || "see findings below"}</div>
          </div>
        </div>`;
    } else if (isProcessing) {
      verdictBanner = `
        <div class="verdict-banner verdict-processing">
          <span class="spinner-inline"></span>
          <div>
            <div class="verdict-title">Verification in Progress</div>
            <div class="verdict-sub">OCR pipeline running — results will appear automatically.</div>
          </div>
        </div>`;
      _startPolling(id); // auto-refresh until done
    }

    document.getElementById("detail-body").innerHTML = `
      ${verdictBanner}

      <div class="detail-grid">
        <div class="detail-section">
          <div class="detail-label">Status</div>
          <div class="detail-value">${statusBadge(i.status)}</div>
        </div>
        <div class="detail-section">
          <div class="detail-label">Category</div>
          <div class="detail-value">${i.product_category?.category_name || "—"}</div>
        </div>
        <div class="detail-section">
          <div class="detail-label">Created</div>
          <div class="detail-value">${fmtDate(i.created_at)}</div>
        </div>
        <div class="detail-section">
          <div class="detail-label">Last Updated</div>
          <div class="detail-value">${fmtDate(i.updated_at)}</div>
        </div>
      </div>
      <hr class="detail-divider" />

      ${sectionTable("Uploaded Images", ["File", "Pre-Processing", "OCR", "Blur Score", "Glare Score"],
        (i.images || []).map(img => `
          <tr>
            <td class="mono" style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${img.file_path?.split(/[\/\\]/).pop() || "—"}</td>
            <td>${img.preprocessing_status || "—"}</td>
            <td>${img.ocr_status || "—"}</td>
            <td>${img.blur_score != null ? img.blur_score.toFixed(2) : "—"}</td>
            <td>${img.glare_score != null ? img.glare_score.toFixed(2) : "—"}</td>
          </tr>`).join("") || `<tr><td colspan="5" class="empty-cell">No images uploaded yet</td></tr>`,
        isPending ? `<div style="margin-top:12px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <input type="file" id="upload-image-file-${i.id}" accept="image/*" multiple style="display:none;" onchange="handleImageUpload('${i.id}')" />
          <button class="btn btn-primary" style="padding:8px 16px;font-size:.85rem;display:inline-flex;align-items:center;gap:8px;" onclick="document.getElementById('upload-image-file-${i.id}').click()">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
            Take Photo / Upload Images
          </button>
          <span id="upload-status-${i.id}" style="font-size:.8rem;color:var(--c-text-2);"></span>
        </div>` : "")}

      ${(i.extracted_fields || []).length > 0 ? sectionTable(
        "Extracted LMPC Fields",
        ["Field", "Extracted Value", "Normalized", "Unit", "Validated"],
        i.extracted_fields.map(f => `
          <tr>
            <td><strong>${f.field_type || "—"}</strong></td>
            <td>${f.raw_value || "—"}</td>
            <td>${f.normalized_value || "—"}</td>
            <td>${f.unit || "—"}</td>
            <td style="color:${f.is_validated ? 'var(--c-green)' : 'var(--c-red)'}">${f.is_validated ? "✓ Yes" : "✗ No"}</td>
          </tr>`).join("")) : ""}

      ${(i.findings || []).length > 0 ? sectionTable(
        "Rule Check Findings",
        ["LMPC Rule", "Check", "Result", "Details"],
        i.findings.map(f => `
          <tr>
            <td style="font-size:.78rem;color:var(--c-text-2);">${f.details?.rule || "—"}</td>
            <td>${f.details?.check || f.finding_type || "—"}</td>
            <td>${statusBadge(f.status)}</td>
            <td style="font-size:.8rem;word-break:break-word;max-width:280px;">${f.details?.message || "—"}</td>
          </tr>`).join("")) : 
        (isCompliant || isNonCompliant ? "<p style='color:var(--c-text-3);font-size:.85rem;'>No findings recorded.</p>" : "")}
    `;

    // ── Footer ──────────────────────────────────────────────────────────
    let footer = `<button class="btn btn-ghost" onclick="closeModal('modal-inspection-detail');_stopPolling();">Close</button>`;

    if (isCompliant) {
      footer = `<span style="font-size:.85rem;color:var(--c-green);font-weight:600;display:flex;align-items:center;gap:6px;margin-right:auto;">✓ Verified COMPLIANT with LMPC Rules, 2011</span>` + footer;
    } else if (isNonCompliant) {
      footer = `<span style="font-size:.85rem;color:var(--c-red);font-weight:600;display:flex;align-items:center;gap:6px;margin-right:auto;">✕ NON-COMPLIANT — label does not satisfy all LMPC requirements</span>` + footer;
    } else if (isProcessing) {
      footer = `<span style="font-size:.85rem;color:var(--c-primary);display:flex;align-items:center;gap:6px;margin-right:auto;"><span class="spinner-inline"></span> Verifying against LMPC rules…</span>` + footer;
    }

    document.getElementById("detail-footer").innerHTML = footer;
  } catch (err) {
    document.getElementById("detail-body").innerHTML = `<div class="form-error">${err.message}</div>`;
  }
}


async function handleImageUpload(inspectionId) {
  const input = document.getElementById(`upload-image-file-${inspectionId}`);
  const statusEl = document.getElementById(`upload-status-${inspectionId}`);
  if (!input || !input.files || !input.files.length) return;

  const files = Array.from(input.files);
  const total = files.length;
  let successCount = 0;
  const errors = [];

  for (let idx = 0; idx < files.length; idx++) {
    const file = files[idx];
    statusEl.innerHTML = `<span class="spinner-inline"></span> Uploading ${idx + 1}/${total}: ${file.name}…`;

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API}/inspections/${inspectionId}/images`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${STATE.token}` },
        body: formData,
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "Upload failed");
      successCount++;
    } catch (err) {
      errors.push(`${file.name}: ${err.message}`);
    }
  }

  // Reset input so the same files can be re-selected if needed
  input.value = "";

  if (errors.length === 0) {
    showToast(
      total === 1
        ? "Image uploaded! OCR pipeline started."
        : `All ${total} images uploaded! OCR pipeline started.`,
      "success"
    );
    statusEl.textContent = "";
  } else {
    const msg = `${successCount}/${total} uploaded. Errors: ${errors.join(" | ")}`;
    statusEl.textContent = msg;
    showToast(msg, "error");
  }

  openDetail(inspectionId); // Refresh modal to show newly uploaded images
}

function sectionTable(title, headers, rowsHtml, extraHtml = "") {
  return `
    <div>
      <div class="detail-label" style="margin-bottom:8px;">${title}</div>
      <div class="table-card" style="margin:0;">
        <table class="sub-table">
          <thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr></thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
      ${extraHtml}
    </div>`;
}


/* ═══════════════════════════════════════════════════════════════
   USERS
═══════════════════════════════════════════════════════════════ */
async function loadUsers() {
  const tbody = document.getElementById("users-tbody");
  tbody.innerHTML = `<tr><td colspan="6" class="empty-cell"><span class="spinner-inline"></span> Loading…</td></tr>`;
  try {
    const users = await apiFetch("/admin/users");
    const list  = Array.isArray(users) ? users : (users.items || []);
    tbody.innerHTML = list.length
      ? list.map(u => `<tr>
          <td>
            <div style="display:flex;align-items:center;gap:10px;">
              <div style="width:30px;height:30px;border-radius:50%;background:var(--c-primary);color:#fff;display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:700;flex-shrink:0;">${moniker(u.full_name || u.email)}</div>
              ${u.full_name || "—"}
            </div>
          </td>
          <td>${u.email}</td>
          <td>${roleBadge(u)}</td>
          <td>${activeBadge(u.is_active)}</td>
          <td>${fmtDate(u.created_at)}</td>
          <td>
            ${u.id !== STATE.user?.id ? `
              <button class="btn btn-ghost" style="padding:5px 12px;font-size:.8rem;" onclick="toggleUser('${u.id}', ${u.is_active})">
                ${u.is_active ? "Deactivate" : "Activate"}
              </button>` : `<span style="font-size:.8rem;color:var(--c-text-3);">You</span>`}
          </td>
        </tr>`).join("")
      : emptyRow(6, "No users found");
  } catch (err) {
    tbody.innerHTML = emptyRow(6, `Error: ${err.message}`);
  }
}

async function toggleUser(userId, currentlyActive) {
  const action = currentlyActive ? "deactivate" : "activate";
  const verb   = currentlyActive ? "deactivate" : "reactivate";
  if (!confirm(`Are you sure you want to ${verb} this user account?`)) return;

  try {
    await apiFetch(`/admin/users/${userId}/${action}`, { method: "PATCH" });
    showToast(`User ${verb}d successfully.`, "success");
    loadUsers();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── New User ───────────────────────────────────────────────── */
function openNewUserModal() {
  ["new-user-name", "new-user-email", "new-user-password"].forEach(id => {
    document.getElementById(id).value = "";
  });
  hideError("new-user-error");
  openModal("modal-new-user");
}

async function createUser() {
  hideError("new-user-error");
  const roleVal = document.getElementById("new-user-role").value;
  const body = {
    full_name: document.getElementById("new-user-name").value.trim(),
    email:     document.getElementById("new-user-email").value.trim(),
    password:  document.getElementById("new-user-password").value,
    role_name: roleVal,
    role:      roleVal,
  };
  if (!body.full_name || !body.email || !body.password) {
    showError("new-user-error", "All fields are required."); return;
  }
  setLoading("create-user-btn", true);
  try {
    await apiFetch("/admin/users", { method: "POST", body: JSON.stringify(body) });
    showToast("User created successfully.", "success");
    closeModal("modal-new-user");
    loadUsers();
  } catch (err) {
    showError("new-user-error", err.message);
  } finally {
    setLoading("create-user-btn", false);
  }
}

/* ═══════════════════════════════════════════════════════════════
   MODAL HELPERS
═══════════════════════════════════════════════════════════════ */
function openModal(id) {
  document.getElementById(id).style.display = "flex";
}
function closeModal(id) {
  document.getElementById(id).style.display = "none";
}

/* Password toggle */
function togglePw(inputId, btn) {
  const input = document.getElementById(inputId);
  const show  = input.type === "password";
  input.type  = show ? "text" : "password";
  btn.textContent = show ? "Hide" : "Show";
}

/* Close modal on Escape */
document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    document.querySelectorAll(".modal-backdrop").forEach(m => { m.style.display = "none"; });
  }
});

/* ═══════════════════════════════════════════════════════════════
   LMPC RULES MANAGEMENT (ADMIN ONLY)
═══════════════════════════════════════════════════════════════ */
STATE.activeRuleVersion = null;

async function loadRules() {
  const tbody = document.getElementById("rules-tbody");
  tbody.innerHTML = `<tr><td colspan="6" class="empty-cell"><span class="spinner-inline"></span> Loading rules…</td></tr>`;
  try {
    const version = await apiFetch("/admin/rules");
    STATE.activeRuleVersion = version;

    // Populate version banner
    document.getElementById("rule-version-title").textContent = `Version ${version.version_number || "1.0"}`;
    document.getElementById("rule-version-sub").textContent = `Effective from: ${fmtDate(version.effective_from)}`;
    document.getElementById("rule-version-badge").textContent = version.is_active ? "Active Version" : "Inactive";
    document.getElementById("rule-version-badge").className = `badge ${version.is_active ? "badge-active" : "badge-inactive"}`;

    const rules = Array.isArray(version.rules) ? version.rules : [];
    const total = rules.length;
    const mandatoryCount = rules.filter(r => r.parameters?.is_mandatory === true).length;
    const advisoryCount = total - mandatoryCount;

    document.getElementById("rules-total-count").textContent = total;
    document.getElementById("rules-mandatory-count").textContent = mandatoryCount;
    document.getElementById("rules-advisory-count").textContent = advisoryCount;

    if (!rules.length) {
      tbody.innerHTML = emptyRow(6, "No rules configured in this version");
      return;
    }

    tbody.innerHTML = rules.map(r => {
      const isMandatory = r.parameters?.is_mandatory === true;
      const field = r.parameters?.field || "—";
      const ruleRef = r.parameters?.rule_ref || "";

      return `<tr>
        <td>
          <div style="font-weight:600;color:var(--c-text);">${r.rule_code}</div>
          ${ruleRef ? `<span style="font-size:.78rem;color:var(--c-text-2);">${ruleRef}</span>` : ""}
        </td>
        <td style="max-width:300px;font-size:.85rem;color:var(--c-text-2);line-height:1.4;">
          ${r.description || "—"}
        </td>
        <td><span class="mono" style="font-weight:600;font-size:.8rem;">${field}</span></td>
        <td><span class="badge badge-pending">${r.check_type}</span></td>
        <td>
          <span class="badge ${isMandatory ? 'badge-mandatory' : 'badge-advisory'}">
            <span class="badge-dot"></span>${isMandatory ? "Mandatory" : "Advisory"}
          </span>
        </td>
        <td>
          <div style="display:flex;gap:6px;align-items:center;">
            <button class="btn btn-ghost" style="padding:4px 10px;font-size:.78rem;" 
                    onclick="toggleRuleMandatory('${r.id}', ${isMandatory})" 
                    title="${isMandatory ? 'Make advisory' : 'Make mandatory'}">
              ${isMandatory ? "Demote" : "Promote"}
            </button>
            <button class="btn btn-ghost" style="padding:4px 10px;font-size:.78rem;" 
                    onclick="openEditRuleModal('${r.id}')">
              Edit
            </button>
            <button class="btn btn-ghost" style="padding:4px 10px;font-size:.78rem;color:var(--c-red);" 
                    onclick="deleteRule('${r.id}', '${r.rule_code}')">
              &times;
            </button>
          </div>
        </td>
      </tr>`;
    }).join("");

  } catch (err) {
    tbody.innerHTML = emptyRow(6, `Error: ${err.message}`);
    showToast("Could not load LMPC rules: " + err.message, "error");
  }
}

function openNewRuleModal() {
  document.getElementById("rule-modal-title").textContent = "Add LMPC Rule";
  document.getElementById("edit-rule-id").value = "";
  document.getElementById("rule-code").value = "";
  document.getElementById("rule-code").disabled = false;
  document.getElementById("rule-ref").value = "";
  document.getElementById("rule-description").value = "";
  document.getElementById("rule-field").value = "MRP";
  document.getElementById("rule-check-type").value = "DECLARATION";
  document.getElementById("rule-is-mandatory").checked = true;
  hideError("rule-error");
  openModal("modal-rule");
}

function openEditRuleModal(ruleId) {
  const version = STATE.activeRuleVersion;
  if (!version) return;
  const r = (version.rules || []).find(x => x.id === ruleId);
  if (!r) return;

  document.getElementById("rule-modal-title").textContent = `Edit Rule: ${r.rule_code}`;
  document.getElementById("edit-rule-id").value = r.id;
  document.getElementById("rule-code").value = r.rule_code;
  document.getElementById("rule-code").disabled = true; // code is primary identifier
  document.getElementById("rule-ref").value = r.parameters?.rule_ref || "";
  document.getElementById("rule-description").value = r.description || "";
  document.getElementById("rule-field").value = r.parameters?.field || "MRP";
  document.getElementById("rule-check-type").value = r.check_type || "DECLARATION";
  document.getElementById("rule-is-mandatory").checked = r.parameters?.is_mandatory === true;
  hideError("rule-error");
  openModal("modal-rule");
}

async function saveRule() {
  hideError("rule-error");
  const editId = document.getElementById("edit-rule-id").value;
  const ruleCode = document.getElementById("rule-code").value.trim();
  const ruleRef = document.getElementById("rule-ref").value.trim();
  const description = document.getElementById("rule-description").value.trim();
  const field = document.getElementById("rule-field").value;
  const checkType = document.getElementById("rule-check-type").value;
  const isMandatory = document.getElementById("rule-is-mandatory").checked;

  if (!ruleCode) {
    showError("rule-error", "Rule code is required.");
    return;
  }

  setLoading("save-rule-btn", true);
  try {
    if (editId) {
      // Update existing rule
      await apiFetch(`/admin/rules/${editId}`, {
        method: "PUT",
        body: JSON.stringify({
          check_type: checkType,
          description,
          is_mandatory: isMandatory,
          field,
          rule_ref: ruleRef,
        }),
      });
      showToast("Rule updated successfully.", "success");
    } else {
      // Create new rule
      await apiFetch("/admin/rules", {
        method: "POST",
        body: JSON.stringify({
          rule_code: ruleCode,
          check_type: checkType,
          description,
          is_mandatory: isMandatory,
          field,
          rule_ref: ruleRef,
        }),
      });
      showToast("New LMPC rule added successfully.", "success");
    }
    closeModal("modal-rule");
    loadRules();
  } catch (err) {
    showError("rule-error", err.message);
  } finally {
    setLoading("save-rule-btn", false);
  }
}

async function toggleRuleMandatory(ruleId, currentlyMandatory) {
  try {
    await apiFetch(`/admin/rules/${ruleId}`, {
      method: "PUT",
      body: JSON.stringify({ is_mandatory: !currentlyMandatory }),
    });
    showToast(`Rule updated to ${!currentlyMandatory ? "Mandatory" : "Advisory"}.`, "success");
    loadRules();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteRule(ruleId, code) {
  if (!confirm(`Are you sure you want to delete rule "${code}" from this active version?`)) return;
  try {
    await apiFetch(`/admin/rules/${ruleId}`, { method: "DELETE" });
    showToast(`Rule ${code} deleted.`, "success");
    loadRules();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Rule Version ───────────────────────────────────────────── */
function openNewVersionModal() {
  document.getElementById("ver-number").value = "";
  document.getElementById("ver-clone-rules").checked = true;
  hideError("ver-error");
  openModal("modal-rule-version");
}

async function createRuleVersion() {
  hideError("ver-error");
  const versionNumber = document.getElementById("ver-number").value.trim();
  const cloneFromActive = document.getElementById("ver-clone-rules").checked;

  if (!versionNumber) {
    showError("ver-error", "Version number is required.");
    return;
  }

  setLoading("create-ver-btn", true);
  try {
    await apiFetch("/admin/rules/version", {
      method: "POST",
      body: JSON.stringify({
        version_number: versionNumber,
        clone_from_active: cloneFromActive,
      }),
    });
    showToast(`LMPC Rule Version ${versionNumber} published & activated!`, "success");
    closeModal("modal-rule-version");
    loadRules();
  } catch (err) {
    showError("ver-error", err.message);
  } finally {
    setLoading("create-ver-btn", false);
  }
}

/* ═══════════════════════════════════════════════════════════════
   BOOT
═══════════════════════════════════════════════════════════════ */
boot();
