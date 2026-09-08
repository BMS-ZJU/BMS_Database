(() => {
  const root = document.documentElement;
  const siteRoot = new URL("../", document.currentScript.src);
  const storageKey = `bms-reading-style:${siteRoot.pathname}`;
  const normalize = (value) => value === "original" ? "original" : "new";
  let initial = "new";
  try { initial = normalize(localStorage.getItem(storageKey)); }
  catch { /* The switch still works when browser storage is unavailable. */ }
  root.dataset.readingStyle = initial;

  const syncButtons = () => {
    const enabled = root.dataset.readingStyle === "new";
    document.querySelectorAll("[data-reading-style-toggle]").forEach((button) => {
      button.setAttribute("aria-pressed", String(enabled));
      button.title = enabled
        ? "当前为新版字体与字号，点击切换为原版"
        : "当前为原版字体与字号，点击切换为新版";
    });
  };

  const choose = (value) => {
    root.dataset.readingStyle = normalize(value);
    syncButtons();
    try { localStorage.setItem(storageKey, root.dataset.readingStyle); }
    catch { /* Keep the selected style for this page and instant navigation. */ }
  };

  const mount = () => {
    const header = document.querySelector("[data-md-component='header'] .md-header__inner");
    if (!header || header.querySelector("[data-reading-style-toggle]")) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "md-header__button md-icon reading-style-toggle";
    button.dataset.readingStyleToggle = "";
    button.setAttribute("aria-label", "使用新版字体与字号");
    button.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M17 8h3v12h1v1h-4v-1h1v-3h-4l-1.5 3H14v1h-4v-1h1zm1 1-3.5 7H18zM5 3h5c1.11 0 2 .89 2 2v11H9v-5H6v5H3V5c0-1.11.89-2 2-2m1 2v4h3V5z"/></svg>';
    button.addEventListener("click", () => {
      choose(root.dataset.readingStyle === "new" ? "original" : "new");
    });
    const palette = header.querySelector("[data-md-component='palette']");
    if (palette) palette.before(button);
    else header.querySelector(".md-header__title")?.after(button);
    syncButtons();
  };

  window.addEventListener("storage", (event) => {
    if (event.key !== storageKey && event.key !== null) return;
    root.dataset.readingStyle = normalize(event.newValue);
    syncButtons();
  });

  document.addEventListener("DOMContentLoaded", () => {
    mount();
    if (typeof document$ !== "undefined") document$.subscribe(mount);
  }, { once: true });
})();
