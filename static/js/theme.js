/* Theme toggle — light / dark using Bootstrap 5.3 data-bs-theme */
(function () {
  const STORAGE_KEY = "shop-theme";

  function getPreferred() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
    localStorage.setItem(STORAGE_KEY, theme);

    const btn = document.getElementById("themeToggleBtn");
    if (btn) {
      const icon = btn.querySelector("i");
      icon.className = theme === "dark" ? "bi bi-sun-fill" : "bi bi-moon-fill";
      btn.setAttribute(
        "title",
        theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
      );
    }
  }

  apply(getPreferred());

  document.addEventListener("DOMContentLoaded", function () {
    apply(getPreferred());

    var btn = document.getElementById("themeToggleBtn");
    if (btn) {
      btn.addEventListener("click", function () {
        var current =
          document.documentElement.getAttribute("data-bs-theme") || "light";
        apply(current === "dark" ? "light" : "dark");
      });
    }
  });
})();
