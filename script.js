const root = document.documentElement;
const toggle = document.getElementById("themeToggle");
const stored = localStorage.getItem("theme");

if (stored) {
  root.dataset.theme = stored;
} else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
  root.dataset.theme = "dark";
}

function updateIcon() {
  toggle.textContent = root.dataset.theme === "dark" ? "☀" : "☾";
}
updateIcon();

toggle.addEventListener("click", () => {
  const next = root.dataset.theme === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  localStorage.setItem("theme", next);
  updateIcon();
});

document.getElementById("year").textContent = new Date().getFullYear();
