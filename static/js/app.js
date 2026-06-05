if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {});
  });
}

const themeToggle = document.querySelector("#themeToggle");

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("rangelog-theme", theme);
  window.dispatchEvent(new CustomEvent("rangelog:theme-change"));
}

if (themeToggle) {
  themeToggle.checked = document.documentElement.dataset.theme === "dark";
  themeToggle.addEventListener("change", () => {
    setTheme(themeToggle.checked ? "dark" : "light");
  });
}

document.querySelectorAll("[data-filter-group]").forEach((group) => {
  const buttons = group.querySelectorAll("button");
  const cards = document.querySelectorAll("[data-kind][data-weapon]");
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      buttons.forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      const filter = button.dataset.filter;
      cards.forEach((card) => {
        const visible = filter === "all" || card.dataset.kind === filter || card.dataset.weapon === filter;
        card.hidden = !visible;
      });
    });
  });
});
