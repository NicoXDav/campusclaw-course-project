/* 登录页逻辑 — R1.1 / R1.2 / R10.2 */
(function () {
  const form = document.getElementById("login-form");
  const errEl = document.getElementById("login-error");
  const btn = document.getElementById("login-btn");

  // 深浅色偏好
  const theme = localStorage.getItem("wk03-theme");
  if (theme) document.documentElement.dataset.theme = theme;
  document.getElementById("theme-toggle").addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = cur;
    localStorage.setItem("wk03-theme", cur);
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    btn.disabled = true;
    errEl.hidden = true;
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: document.getElementById("username").value.trim(),
          password: document.getElementById("password").value,
        }),
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        location.href = "/materials";
      } else {
        // R1.2 统一文案，由服务端返回
        errEl.textContent = data.message || "用户名或密码错误";
        errEl.hidden = false;
      }
    } catch {
      errEl.textContent = "网络异常，请重试";
      errEl.hidden = false;
    } finally {
      btn.disabled = false;
    }
  });
})();
