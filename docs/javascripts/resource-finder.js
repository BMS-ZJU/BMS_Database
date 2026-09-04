/* Local-only filtering. Static resource links remain usable without JavaScript. */
(() => {
  "use strict";
  const normalize = value => String(value || "").normalize("NFKC").toLowerCase().replace(/\s+/g, " ").trim();
  const keys = { query: "resource_q", kind: "resource_type", year: "resource_year" };
  function initialize() {
    const root = document.querySelector("[data-resource-finder]");
    if (!root) return;
    if (root.dataset.initialized === "true") {
      if (typeof root.resourceFinderRefresh === "function") root.resourceFinderRefresh();
      return;
    }
    root.dataset.initialized = "true";
    const form = root.querySelector("[data-resource-controls]");
    const query = root.querySelector("[data-resource-query]");
    const kind = root.querySelector("[data-resource-kind]");
    const year = root.querySelector("[data-resource-year]");
    const reset = root.querySelector("[data-resource-reset]");
    const count = root.querySelector("[data-resource-count]");
    const empty = root.querySelector("[data-resource-empty]");
    const rows = [...root.querySelectorAll("[data-resource-item]")];
    const groups = [...root.querySelectorAll("[data-resource-group]")];
    const originalPath = window.location.pathname;
    let urlTimer = null;
    const urlNotice = document.createElement("p");
    urlNotice.className = "resource-finder-url-note";
    urlNotice.dataset.resourceUrlNote = "";
    urlNotice.setAttribute("role", "status");
    urlNotice.hidden = true;
    urlNotice.textContent = "筛选仍可使用；当前浏览器未能保存筛选链接。";
    count.insertAdjacentElement("afterend", urlNotice);
    const optionsContain = (select, value) => [...select.options].some(option => option.value === value);
    const fromUrl = () => {
      if (urlTimer !== null) window.clearTimeout(urlTimer);
      urlTimer = null;
      const params = new URL(window.location.href).searchParams;
      query.value = params.get(keys.query) || "";
      const newKind = params.get(keys.kind) || "";
      const newYear = params.get(keys.year) || "";
      kind.value = optionsContain(kind, newKind) ? newKind : "";
      year.value = optionsContain(year, newYear) ? newYear : "";
    };
    const writeUrl = () => {
      urlTimer = null;
      if (!root.isConnected || document.querySelector("[data-resource-finder]") !== root || window.location.pathname !== originalPath) return;
      if (!["http:", "https:"].includes(window.location.protocol)) return;
      const url = new URL(window.location.href);
      for (const [key, value] of [[keys.query, query.value.trim()], [keys.kind, kind.value], [keys.year, year.value]]) {
        if (value) url.searchParams.set(key, value);
        else url.searchParams.delete(key);
      }
      try {
        if (url.href !== window.location.href) window.history.replaceState(window.history.state, "", url);
        urlNotice.hidden = true;
      } catch {
        // Filtering is still useful in constrained browsers or when History API is throttled.
        urlNotice.hidden = false;
      }
    };
    const scheduleUrl = immediate => {
      if (urlTimer !== null) window.clearTimeout(urlTimer);
      if (immediate) writeUrl();
      else urlTimer = window.setTimeout(writeUrl, 180);
    };
    const filter = (syncUrl = true, immediate = false) => {
      const tokens = normalize(query.value).split(" ").filter(Boolean);
      let visible = 0;
      const courses = new Set();
      for (const row of rows) {
        const matches = tokens.every(token => normalize(row.dataset.query).includes(token)) &&
          (!kind.value || row.dataset.kind === kind.value) &&
          (!year.value || row.dataset.years.split(" ").includes(year.value));
        row.hidden = !matches;
        if (matches) { visible++; courses.add(row.dataset.course); }
      }
      for (const group of groups) {
        group.hidden = ![...group.querySelectorAll("[data-resource-item]")].some(row => !row.hidden);
      }
      count.textContent = "显示 " + visible + " / " + rows.length + " 个资料入口 · " + courses.size + " 门课程";
      empty.hidden = visible !== 0;
      if (syncUrl) scheduleUrl(immediate);
    };
    root.resourceFinderRefresh = () => { fromUrl(); filter(false); };
    fromUrl();
    form.hidden = false;
    filter(false);
    form.addEventListener("submit", event => { event.preventDefault(); filter(true, true); });
    query.addEventListener("input", () => filter());
    kind.addEventListener("change", () => filter(true, true));
    year.addEventListener("change", () => filter(true, true));
    reset.addEventListener("click", () => {
      query.value = "";
      kind.value = "";
      year.value = "";
      filter(true, true);
      query.focus();
    });
  }
  document.addEventListener("DOMContentLoaded", initialize);
  if (typeof document$ !== "undefined") document$.subscribe(initialize);
  window.addEventListener("popstate", () => {
    const root = document.querySelector("[data-resource-finder]");
    if (root && typeof root.resourceFinderRefresh === "function") root.resourceFinderRefresh();
  });
  initialize();
})();
