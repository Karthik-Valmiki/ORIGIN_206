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
    PENDING:   ["pending",   "Pending"],
    SUBMITTED: ["submitted", "Submitted"],
    APPROVED:  ["approved",  "Approved"],
    REJECTED:  ["rejected",  "Rejected"],
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
async function boot() {
  // Check if system is initialized
  let setupNeeded = false;
  try {
    const r = await fetch(API + "/setup/status");
    const d = await r.json();
    setupNeeded = !d.initialized;
  } catch {
    // API not reachable – show login anyway
  }

  if (setupNeeded) {
    show("setup-card");
  } else if (STATE.token) {
    // Try to use existing token
    try {
      STATE.user = await apiFetch("/auth/me");
      enterApp();
    } catch {
      STATE.token = null;
      localStorage.removeItem("lmpc_token");
      show("login-card");
    }
  } else {
    show("login-card");
  }
}

function show(cardId) {
  ["setup-card", "login-card"].forEach(id => {
    document.getElementById(id).style.display = id === cardId ? "block" : "none";
  });
}

/* ── Setup ──────────────────────────────────────────────────── */
document.getElementById("setup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError("setup-error");
  setLoading("setup-btn", true);
  try {
    const body = {
      full_name: document.getElementById("setup-name").value.trim(),
      email:     document.getElementById("setup-email").value.trim(),
      password:  document.getElementById("setup-password").value,
    };
    await apiFetch("/setup/", { method: "POST", body: JSON.stringify(body) });
    showToast("System initialized! Please sign in.", "success");
    show("login-card");
    document.getElementById("login-email").value = body.email;
  } catch (err) {
    showError("setup-error", err.message);
  } finally {
    setLoading("setup-btn", false);
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

/* ── Enter App ─────────────────────────────────────────────── */
function enterApp() {
  document.getElementById("auth-overlay").style.display = "none";
  document.getElementById("app").style.display = "flex";

  const u = STATE.user;
  const userRole = getUserRole(u);

  document.getElementById("user-name-display").textContent  = u.full_name || u.email;
  document.getElementById("user-role-display").textContent  = userRole;
  document.getElementById("user-avatar-initials").textContent = moniker(u.full_name || u.email);
  document.getElementById("greeting-text").textContent = `${greeting()}, ${(u.full_name || "").split(" ")[0] || "Officer"}`;

  // Show admin nav item if role is ADMIN
  if (userRole === "ADMIN") {
    document.querySelectorAll(".nav-item-admin").forEach(el => el.classList.remove("hidden"));
  } else {
    document.querySelectorAll(".nav-item-admin").forEach(el => el.classList.add("hidden"));
  }

  navigate("dashboard");
}

function logout() {
  STATE.token = null;
  STATE.user = null;
  localStorage.removeItem("lmpc_token");
  // Cleanly hide admin nav items
  document.querySelectorAll(".nav-item-admin").forEach(el => el.classList.add("hidden"));
  document.getElementById("app").style.display = "none";
  document.getElementById("auth-overlay").style.display = "flex";
  show("login-card");
}

/* ═══════════════════════════════════════════════════════════════
   NAVIGATION
═══════════════════════════════════════════════════════════════ */
function navigate(view) {
  event?.preventDefault();
  STATE.currentView = view;

  // Highlight nav item
  document.querySelectorAll(".nav-item").forEach(el => {
    el.classList.toggle("active", el.id === `nav-${view}`);
  });

  // Show/hide views
  document.querySelectorAll(".view").forEach(el => {
    el.style.display = el.id === `view-${view}` ? "" : "none";
  });

  // Load data
  if (view === "dashboard")   loadDashboard();
  if (view === "inspections") loadInspections();
  if (view === "users")       loadUsers();
}

/* ═══════════════════════════════════════════════════════════════
   DASHBOARD
═══════════════════════════════════════════════════════════════ */
async function loadDashboard() {
  try {
    const inspections = await apiFetch("/inspections/?limit=100");
    const list = Array.isArray(inspections) ? inspections : (inspections.items || []);

    const counts = { PENDING: 0, SUBMITTED: 0, APPROVED: 0, REJECTED: 0 };
    list.forEach(i => { const s = i.status?.toUpperCase(); if (counts[s] !== undefined) counts[s]++; });

    document.getElementById("stat-pending").textContent   = counts.PENDING;
    document.getElementById("stat-submitted").textContent = counts.SUBMITTED;
    document.getElementById("stat-approved").textContent  = counts.APPROVED;
    document.getElementById("stat-rejected").textContent  = counts.REJECTED;

    const recent = list.slice(0, 7);
    const tbody = document.getElementById("recent-tbody");
    tbody.innerHTML = recent.length ? recent.map(inspectionRow).join("") : emptyRow(5, "No inspections yet");
  } catch (err) {
    showToast("Could not load dashboard: " + err.message, "error");
  }
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

/* ── Inspection Detail ──────────────────────────────────────── */
async function openDetail(id) {
  document.getElementById("detail-body").innerHTML = `<span class="spinner-inline"></span> Loading…`;
  document.getElementById("detail-footer").innerHTML = "";
  openModal("modal-inspection-detail");
  try {
    const i = await apiFetch(`/inspections/${id}`);
    document.getElementById("detail-title").textContent = i.inspection_number || "Inspection Details";
    document.getElementById("detail-sub").textContent   = i.product_category?.category_name || "";

    const isReviewable = ["SUBMITTED"].includes((i.status || "").toUpperCase());
    const isAdmin      = getUserRole(STATE.user) === "ADMIN";

    document.getElementById("detail-body").innerHTML = `
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

      ${sectionTable("Images", ["File", "Pre-Processing", "OCR", "Blur", "Glare"], (i.images || []).map(img => `
        <tr>
          <td class="mono" style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${img.file_path || "—"}</td>
          <td>${img.preprocessing_status || "—"}</td>
          <td>${img.ocr_status || "—"}</td>
          <td>${img.blur_score != null ? img.blur_score.toFixed(2) : "—"}</td>
          <td>${img.glare_score != null ? img.glare_score.toFixed(2) : "—"}</td>
        </tr>`).join("") || `<tr><td colspan="5" class="empty-cell">No images uploaded</td></tr>`, (i.status || "").toUpperCase() === "PENDING" ? `<div style="margin-top:10px;display:flex;align-items:center;gap:10px;">
          <input type="file" id="upload-image-file-${i.id}" accept="image/*" style="display:none;" onchange="handleImageUpload('${i.id}')" />
          <button class="btn btn-ghost" style="padding:6px 14px;font-size:.825rem;" onclick="document.getElementById('upload-image-file-${i.id}').click()">
            📷 Select & Upload Image
          </button>
          <span id="upload-status-${i.id}" style="font-size:.8rem;color:var(--c-text-2);"></span>
        </div>` : "")}

      ${sectionTable("Extracted Fields", ["Field Type", "Raw Value", "Normalized", "Unit", "Validated"], (i.extracted_fields || []).map(f => `
        <tr>
          <td>${f.field_type || "—"}</td>
          <td>${f.raw_value || "—"}</td>
          <td>${f.normalized_value || "—"}</td>
          <td>${f.unit || "—"}</td>
          <td>${f.is_validated ? "✓" : "✗"}</td>
        </tr>`).join("") || `<tr><td colspan="5" class="empty-cell">No extracted fields</td></tr>`)}

      ${sectionTable("Findings", ["Finding Type", "Status", "Details"], (i.findings || []).map(f => `
        <tr>
          <td>${f.finding_type || "—"}</td>
          <td>${statusBadge(f.status)}</td>
          <td style="font-size:.8rem;word-break:break-word;max-width:320px;">${f.details ? (f.details.message || JSON.stringify(f.details)) : "—"}</td>
        </tr>`).join("") || `<tr><td colspan="3" class="empty-cell">No findings</td></tr>`)}

      ${sectionTable("Review History", ["Action", "Comments", "Reviewed At"], (i.reviews || []).map(r => `
        <tr>
          <td>${r.action || "—"}</td>
          <td>${r.comments || "—"}</td>
          <td>${fmtDate(r.reviewed_at)}</td>
        </tr>`).join("") || `<tr><td colspan="3" class="empty-cell">No reviews yet</td></tr>`)}
    `;

    // Footer actions
    let footerButtons = `<button class="btn btn-ghost" onclick="closeModal('modal-inspection-detail')">Close</button>`;
    if (isAdmin && isReviewable) {
      STATE.reviewTargetId = id;
      footerButtons += `<button class="btn btn-primary" onclick="openReviewModal('${id}')">Review Inspection</button>`;
    }
    document.getElementById("detail-footer").innerHTML = footerButtons;
  } catch (err) {
    document.getElementById("detail-body").innerHTML = `<div class="form-error">${err.message}</div>`;
  }
}

async function handleImageUpload(inspectionId) {
  const input = document.getElementById(`upload-image-file-${inspectionId}`);
  const statusEl = document.getElementById(`upload-status-${inspectionId}`);
  if (!input || !input.files || !input.files[0]) return;

  const file = input.files[0];
  statusEl.innerHTML = `<span class="spinner-inline"></span> Uploading ${file.name}…`;

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

    showToast("Image uploaded successfully! OCR pipeline started.", "success");
    openDetail(inspectionId); // Refresh modal
  } catch (err) {
    statusEl.textContent = `Upload error: ${err.message}`;
    showToast(`Upload failed: ${err.message}`, "error");
  }
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

/* ── Review ─────────────────────────────────────────────────── */
function openReviewModal(id) {
  STATE.reviewTargetId = id;
  closeModal("modal-inspection-detail");
  document.getElementById("review-comments").value = "";
  document.querySelector('input[name="review-action"][value="ACCEPT"]').checked = true;
  hideError("review-error");
  openModal("modal-review");
}

async function submitReview() {
  hideError("review-error");
  const action   = document.querySelector('input[name="review-action"]:checked')?.value;
  const comments = document.getElementById("review-comments").value.trim();
  if (!action) { showError("review-error", "Please select an action."); return; }
  setLoading("submit-review-btn", true);
  try {
    await apiFetch(`/inspections/${STATE.reviewTargetId}/review`, {
      method: "POST",
      body: JSON.stringify({ action, comments: comments || null }),
    });
    showToast("Review submitted successfully.", "success");
    closeModal("modal-review");
    if (STATE.currentView === "dashboard") loadDashboard();
    else loadInspections();
  } catch (err) {
    showError("review-error", err.message);
  } finally {
    setLoading("submit-review-btn", false);
  }
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
  const action = currentlyActive ? "deactivate" : "reactivate";
  try {
    await apiFetch(`/admin/users/${userId}/${action}`, { method: "PATCH" });
    showToast(`User ${action}d successfully.`, "success");
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
   BOOT
═══════════════════════════════════════════════════════════════ */
boot();
