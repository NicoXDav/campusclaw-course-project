/* 材料页逻辑 — R9.2/R9.3/R9.5, R10.2-R10.7 */
"use strict";

/* ---------------- fetch 封装: 401 一律回登录页 (R9.3) ---------------- */
async function api(path, options) {
  const res = await fetch(path, options);
  if (res.status === 401) { location.href = "/login"; throw new Error("unauthorized"); }
  return res;
}

/* ---------------- toast (R10.6) ---------------- */
function toast(message, ok = true) {
  const el = document.createElement("div");
  el.className = "toast" + (ok ? "" : " err");
  el.textContent = message;
  document.getElementById("toasts").appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

/* ---------------- 安全的 Markdown 渲染 (R9.5 + R10.7) ---------------- */
function escapeHTML(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function safeUrl(u) {
  return /^(https?:|mailto:)/i.test(u) ? u : "#";
}
function inline(s) {
  return s
    .replace(/`([^`]+)`/g, (_, c) => "<code>" + c + "</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, t, u) => '<a href="' + safeUrl(u) + '" target="_blank" rel="noopener">' + t + "</a>");
}
function renderMarkdown(src) {
  const out = [];
  const blocks = escapeHTML(src).split(/```/);
  blocks.forEach((block, i) => {
    if (i % 2 === 1) {                       // 代码块
      out.push("<pre><code>" + block.replace(/^\w*\n/, "") + "</code></pre>");
      return;
    }
    let para = [], listType = null;
    const flushList = () => {
      if (listType) { out.push(`<${listType}>` + para.join("") + `</${listType}>`); para = []; listType = null; }
    };
    for (const raw of block.split("\n")) {
      const line = raw.trimEnd();
      const h = line.match(/^(#{1,3})\s+(.*)/);
      const ul = line.match(/^\s*[-*]\s+(.*)/);
      const ol = line.match(/^\s*\d+\.\s+(.*)/);
      const bq = line.match(/^&gt;\s?(.*)/) || line.match(/^>\s?(.*)/);
      if (/^---+$/.test(line)) { flushList(); out.push("<hr>"); }
      else if (h) { flushList(); out.push(`<h${h[1].length}>` + inline(h[2]) + `</h${h[1].length}>`); }
      else if (ul) { if (listType !== "ul") { flushList(); listType = "ul"; } para.push("<li>" + inline(ul[1]) + "</li>"); }
      else if (ol) { if (listType !== "ol") { flushList(); listType = "ol"; } para.push("<li>" + inline(ol[1]) + "</li>"); }
      else if (bq) { flushList(); out.push("<blockquote>" + inline(bq[1]) + "</blockquote>"); }
      else if (line === "") { flushList(); }
      else { flushList(); out.push("<p>" + inline(line) + "</p>"); }
    }
    flushList();
  });
  return out.join("\n");
}

/* ---------------- 全局状态 ---------------- */
let ME = null;
let ITEMS = [];
let VIEW = localStorage.getItem("wk03-view") || "list";
let KEYWORD = "";

/* ---------------- 主题 / 视图 (R10.2 / R10.3) ---------------- */
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  localStorage.setItem("wk03-theme", t);
}
function applyView(v) {
  VIEW = v;
  localStorage.setItem("wk03-view", v);
  document.getElementById("list").hidden = v !== "list";
  document.getElementById("grid").hidden = v !== "grid";
  document.getElementById("view-list").classList.toggle("active", v === "list");
  document.getElementById("view-grid").classList.toggle("active", v === "grid");
}

/* ---------------- 渲染 ---------------- */
function filtered() {
  if (!KEYWORD) return ITEMS;
  const k = KEYWORD.toLowerCase();
  return ITEMS.filter(it =>
    it.title.toLowerCase().includes(k) || (it.excerpt || "").toLowerCase().includes(k));
}
function render() {
  const items = filtered();
  const list = document.getElementById("list"), grid = document.getElementById("grid");
  document.getElementById("empty").hidden = items.length > 0;
  list.innerHTML = ""; grid.innerHTML = "";
  for (const it of items) {
    const li = document.createElement("div");
    li.className = "material-item";
    li.innerHTML = `
      <div class="ext-tag">${escapeHTML(it.ext || "txt")}</div>
      <div style="flex:1">
        <div class="t">${escapeHTML(it.title)}</div>
        <div class="meta">上传者 ${escapeHTML(it.uploader)} · ${escapeHTML(it.created_at)} · ${escapeHTML(it.filename)}</div>
      </div>
      <button class="btn btn-ghost btn-dl">⬇ 下载</button>`;
    li.querySelector(".btn-dl").addEventListener("click", (e) => {
      e.stopPropagation();
      location.href = `/api/materials/${it.id}/download`;
    });
    li.addEventListener("click", () => openDetail(it.id));
    list.appendChild(li);

    const card = document.createElement("div");
    card.className = "material-card";
    card.innerHTML = `
      <div class="ext-tag" style="margin-bottom:10px">${escapeHTML(it.ext || "txt")}</div>
      <div class="t">${escapeHTML(it.title)}</div>
      <div class="excerpt">${escapeHTML(it.excerpt || "")}</div>
      <div class="meta" style="margin-top:10px">${escapeHTML(it.uploader)} · ${escapeHTML(it.created_at)}</div>`;
    card.addEventListener("click", () => openDetail(it.id));
    grid.appendChild(card);
  }
}

/* ---------------- 详情 (R3.2 / R9.5 / R10.7) ---------------- */
async function openDetail(id) {
  const res = await api(`/api/materials/${id}`);
  const data = await res.json();
  if (!data.ok) { toast(data.message, false); return; }
  const it = data.item;
  const body = document.getElementById("detail-body");
  const isMd = it.ext === "md";
  body.innerHTML = `
    <h3>${escapeHTML(it.title)}</h3>
    <p class="muted" style="margin:6px 0 14px">${escapeHTML(it.filename)} · 上传者 ${escapeHTML(it.uploader)} · ${escapeHTML(it.created_at)}</p>
    ${isMd ? '<div class="md">' + renderMarkdown(it.content) + "</div>"
           : '<pre class="txt-pre">' + escapeHTML(it.content) + "</pre>"}`;
  document.getElementById("detail-download").href = `/api/materials/${id}/download`;
  document.getElementById("detail-dialog").showModal();
}

/* ---------------- 上传 (R4 / R10.6) ---------------- */
function bindUpload() {
  const btn = document.getElementById("upload-btn");
  if (ME.role !== "teacher") return;          // 学生前端隐藏; 服务端仍有 403 兜底 (R2.3)
  btn.hidden = false;
  const dialog = document.getElementById("upload-dialog");
  const form = document.getElementById("upload-form");
  const fileInput = document.getElementById("file-input");
  const progress = document.getElementById("progress");
  const bar = document.getElementById("progress-bar");
  const ptext = document.getElementById("progress-text");

  btn.addEventListener("click", () => { form.reset(); progress.hidden = true; ptext.hidden = true; dialog.showModal(); });
  document.getElementById("upload-cancel").addEventListener("click", () => dialog.close());

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) return;
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/materials");
    xhr.upload.addEventListener("progress", (ev) => {
      if (ev.lengthComputable) {
        progress.hidden = false; ptext.hidden = false;
        const pct = Math.round(ev.loaded / ev.total * 100);
        bar.style.width = pct + "%";
        ptext.textContent = `上传中 ${pct}%`;
      }
    });
    xhr.addEventListener("load", () => {
      let data = {};
      try { data = JSON.parse(xhr.responseText); } catch {}
      if (xhr.status === 200 && data.ok) {
        toast(data.message || "上传成功");
        dialog.close();
        refresh();
      } else {
        toast(data.message || `上传失败（HTTP ${xhr.status}）`, false);
      }
      progress.hidden = true; ptext.hidden = true;
    });
    xhr.addEventListener("error", () => toast("网络异常，上传失败", false));
    const fd = new FormData();
    fd.append("file", file);
    xhr.send(fd);
  });
}

/* ---------------- 命令面板 (R10.5) ---------------- */
const COMMANDS = [
  { name: "切换深浅色主题", key: "R10.2", run: () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark") },
  { name: "切换 列表/网格 视图", key: "R10.3", run: () => applyView(VIEW === "list" ? "grid" : "list") },
  { name: "上传材料", key: "R4", teacherOnly: true, run: () => document.getElementById("upload-btn").click() },
  { name: "聚焦本班搜索", key: "R10.4", run: () => document.getElementById("search").focus() },
  { name: "退出登录", key: "R1", run: async () => { await api("/api/logout", { method: "POST" }); location.href = "/login"; } },
];
function bindPalette() {
  const dlg = document.getElementById("palette");
  const input = document.getElementById("palette-input");
  const ul = document.getElementById("palette-list");
  let sel = 0, current = [];

  function renderList() {
    const q = input.value.trim().toLowerCase();
    current = COMMANDS.filter(c => !c.teacherOnly || ME.role === "teacher")
                      .filter(c => !q || c.name.toLowerCase().includes(q));
    ul.innerHTML = "";
    current.forEach((c, i) => {
      const li = document.createElement("li");
      li.className = i === sel ? "sel" : "";
      li.innerHTML = `${escapeHTML(c.name)}<span class="k">${c.key}</span>`;
      li.addEventListener("click", () => { dlg.close(); c.run(); });
      ul.appendChild(li);
    });
  }
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault(); sel = 0; input.value = ""; renderList(); dlg.showModal(); input.focus();
    }
  });
  input.addEventListener("input", () => { sel = 0; renderList(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { sel = Math.min(sel + 1, current.length - 1); renderList(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { sel = Math.max(sel - 1, 0); renderList(); e.preventDefault(); }
    else if (e.key === "Enter" && current[sel]) { dlg.close(); current[sel].run(); }
  });
  document.getElementById("palette-btn").addEventListener("click", () => { sel = 0; input.value = ""; renderList(); dlg.showModal(); input.focus(); });
}

/* ---------------- 初始化 ---------------- */
async function refresh() {
  const res = await api("/api/materials");
  const data = await res.json();
  ITEMS = data.items || [];
  render();
}

(async function init() {
  const theme = localStorage.getItem("wk03-theme");
  if (theme) document.documentElement.dataset.theme = theme;
  applyView(VIEW);
  document.getElementById("theme-toggle").addEventListener("click",
    () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
  document.getElementById("view-list").addEventListener("click", () => applyView("list"));
  document.getElementById("view-grid").addEventListener("click", () => applyView("grid"));
  document.getElementById("detail-close").addEventListener("click", () => document.getElementById("detail-dialog").close());
  document.getElementById("search").addEventListener("input", (e) => { KEYWORD = e.target.value.trim(); render(); });
  document.getElementById("logout-btn").addEventListener("click", async () => {
    await api("/api/logout", { method: "POST" }); location.href = "/login";
  });

  try {
    const res = await api("/api/me");        // R9.2
    ME = (await res.json()).user;
  } catch { return; }                        // 401 已由 api() 跳转登录
  document.getElementById("me-name").textContent = ME.username;
  document.getElementById("me-role").textContent = ME.role === "teacher" ? "教师" : "学生";
  document.getElementById("class-name").textContent = ` · ${ME.class_name}（class_id=${ME.class_id}）`;
  bindUpload();
  bindPalette();
  refresh();
})();
