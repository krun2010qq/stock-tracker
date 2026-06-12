const adminLabel = document.getElementById("admin-label");
const adminStats = document.getElementById("admin-stats");
const usersTableBody = document.getElementById("users-table-body");
const adminMessage = document.getElementById("admin-message");
const userSearch = document.getElementById("user-search");
const refreshUsersBtn = document.getElementById("refresh-users-btn");

let currentAdmin = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatDate(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function requireAdminSession() {
  if (!isLoggedIn()) {
    window.location.href = "/login.html";
    return false;
  }
  return true;
}

function renderStats(stats) {
  const cards = [
    ["总用户数", stats.total_users],
    ["活跃用户", stats.active_users],
    ["禁用用户", stats.inactive_users],
    ["管理员", stats.admin_users],
    ["已设偏好", stats.users_with_preferences],
  ];

  adminStats.innerHTML = cards
    .map(
      ([label, value]) => `
        <div class="stat-card">
          <strong>${escapeHtml(value)}</strong>
          <span>${escapeHtml(label)}</span>
        </div>
      `
    )
    .join("");
}

function renderUsers(users) {
  if (!users.length) {
    usersTableBody.innerHTML = `<tr><td colspan="7" class="empty-cell">暂无用户</td></tr>`;
    return;
  }

  usersTableBody.innerHTML = users
    .map((user) => {
      const symbols = (user.preferences?.favorite_symbols || []).join(", ") || "--";
      const statusBadge = user.is_active
        ? `<span class="badge ok">正常</span>`
        : `<span class="badge warn">已禁用</span>`;
      const roleBadge = user.is_admin
        ? `<span class="badge admin">管理员</span>`
        : `<span class="badge user">普通用户</span>`;

      return `
        <tr>
          <td>${escapeHtml(user.display_name)}</td>
          <td>${escapeHtml(user.email)}</td>
          <td>${statusBadge}</td>
          <td>${roleBadge}</td>
          <td>${escapeHtml(symbols)}</td>
          <td>${formatDate(user.created_at)}</td>
          <td>
            <div class="admin-actions">
              <button type="button" data-action="toggle-active" data-id="${escapeHtml(user.id)}" data-active="${user.is_active}">
                ${user.is_active ? "禁用" : "启用"}
              </button>
              <button type="button" data-action="toggle-admin" data-id="${escapeHtml(user.id)}" data-admin="${user.is_admin}">
                ${user.is_admin ? "取消管理员" : "设为管理员"}
              </button>
              <button type="button" class="danger" data-action="delete" data-id="${escapeHtml(user.id)}">删除</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function ensureAdmin() {
  const me = await apiFetch("/api/auth/me");
  if (!me.user.is_admin) {
    window.location.href = "/";
    return false;
  }
  currentAdmin = me.user;
  adminLabel.textContent = `${me.user.display_name || me.user.email} · 管理员`;
  return true;
}

async function loadStats() {
  const data = await apiFetch("/api/admin/stats");
  renderStats(data.stats || {});
}

async function loadUsers() {
  const query = userSearch.value.trim();
  const suffix = query ? `?q=${encodeURIComponent(query)}` : "";
  const data = await apiFetch(`/api/admin/users${suffix}`);
  renderUsers(data.users || []);
}

async function handleUserAction(action, userId, dataset) {
  showMessage(adminMessage, "");

  if (action === "delete") {
    if (!window.confirm("确定删除该用户吗？此操作不可恢复。")) return;
    await apiFetch(`/api/admin/users/${userId}`, { method: "DELETE" });
    showMessage(adminMessage, "用户已删除", "success");
    await Promise.all([loadStats(), loadUsers()]);
    return;
  }

  if (action === "toggle-active") {
    await apiFetch(`/api/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: dataset.active !== "true" }),
    });
    showMessage(adminMessage, "用户状态已更新", "success");
  }

  if (action === "toggle-admin") {
    await apiFetch(`/api/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_admin: dataset.admin !== "true" }),
    });
    showMessage(adminMessage, "管理员权限已更新", "success");
  }

  await Promise.all([loadStats(), loadUsers()]);
}

usersTableBody.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  try {
    await handleUserAction(button.dataset.action, button.dataset.id, button.dataset);
  } catch (error) {
    showMessage(adminMessage, error.message, "error");
  }
});

refreshUsersBtn.addEventListener("click", () => {
  loadUsers().catch((error) => showMessage(adminMessage, error.message, "error"));
});

userSearch.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    loadUsers().catch((error) => showMessage(adminMessage, error.message, "error"));
  }
});

document.getElementById("logout-btn").addEventListener("click", (event) => {
  event.preventDefault();
  logout();
});

(async function init() {
  if (!requireAdminSession()) return;

  try {
    const ok = await ensureAdmin();
    if (!ok) return;
    await Promise.all([loadStats(), loadUsers()]);
  } catch (error) {
    clearToken();
    window.location.href = "/login.html";
  }
})();
