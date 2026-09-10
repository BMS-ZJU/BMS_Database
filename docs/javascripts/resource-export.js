(() => {
  // Resolve from this asset so project sites and local previews share the same paths.
  const siteRoot = new URL("../", document.currentScript.src);
  const previewUrl = new URL("resource-export.html", siteRoot);

  const resourceUrl = (value) => {
    let url;
    try { url = new URL(value, location.href); }
    catch { return null; }
    const path = url.pathname.slice(siteRoot.pathname.length);
    if (url.origin !== location.origin || !url.pathname.startsWith(siteRoot.pathname) ||
        url.search || url.hash ||
        !/^(mandatory|elective)\/[^/]+\/(exams|quizzes)\/[^/]+(?:\/|\.html)$/.test(path) ||
        /\/index\.html$/.test(path) || /\.(?:pdf|docx?|zip)\/?$/i.test(path)) return null;
    return url;
  };

  const exportUrl = (sources) => {
    const url = new URL(previewUrl);
    sources.forEach((source) => url.searchParams.append("source", source));
    return url.href;
  };

  const exportLink = (sources, text) => {
    const link = document.createElement("a");
    link.href = exportUrl(sources);
    link.textContent = text;
    link.target = "_blank";
    link.rel = "noopener";
    link.dataset.instant = "false";
    return link;
  };

  // Native selection controls for resource directory cards.
  const selectionControls = (choices, id) => {
    const controls = document.createElement("div");
    controls.id = id;
    controls.className = "resource-batch-selection";
    const allLabel = document.createElement("label");
    const all = document.createElement("input");
    all.type = "checkbox";
    allLabel.append(all, "全选");
    const count = document.createElement("span");
    count.setAttribute("role", "status");
    count.setAttribute("aria-live", "polite");
    const selected = exportLink([], "导出所选");
    const help = document.createElement("small");
    help.textContent = "按资料原有顺序合并，每份资料另起一页。";
    selected.title = help.textContent;
    controls.append(allLabel, count, selected, help);
    const update = () => {
      const sources = choices.filter((choice) => choice.checkbox.checked).map((choice) => choice.source);
      count.textContent = `已选 ${sources.length} / ${choices.length} 份`;
      all.checked = sources.length === choices.length;
      all.indeterminate = sources.length > 0 && sources.length < choices.length;
      selected.setAttribute("aria-disabled", String(!sources.length));
      if (sources.length) selected.href = exportUrl(sources);
      else selected.removeAttribute("href");
    };
    choices.forEach(({ checkbox }) => checkbox.addEventListener("change", update));
    all.addEventListener("change", () => {
      choices.forEach(({ checkbox }) => { checkbox.checked = all.checked; });
      update();
    });
    selected.addEventListener("click", (event) => {
      if (selected.getAttribute("aria-disabled") === "true") event.preventDefault();
    });
    update();
    return { controls, update };
  };

  const currentResource = (sections) => sections.find((section) => {
    let block = section.closest(".tabbed-block");
    if (!block) return sections.length === 1;
    while (block) {
      const set = block.parentElement.closest(".tabbed-set");
      const blocks = Array.from(set.querySelectorAll(":scope > .tabbed-content > .tabbed-block"));
      const input = set.querySelectorAll(':scope > input[type="radio"]')[blocks.indexOf(block)];
      if (!input?.checked) return false;
      block = set.parentElement.closest(".tabbed-block");
    }
    return true;
  });

  const addPageEntry = () => {
    const source = resourceUrl(new URL(location.pathname, location.origin));
    const article = document.querySelector("article.md-content__inner");
    // Classify reading typography before export controls can return early.
    article?.classList.toggle("reading-paper", Boolean(source));
    const heading = article?.querySelector(":scope > h1");
    if (!source || !heading || article.querySelector(".resource-page-tools")) return;
    const tools = document.createElement("p");
    tools.className = "resource-page-tools";
    heading.after(tools);
    const sections = Array.from(article.querySelectorAll('section[id][data-export-title]'));
    const link = exportLink([source.pathname], "打印 / 导出");
    link.className = "resource-export-link";
    link.title = "打开打印预览，可通过浏览器保存为 PDF";
    const title = heading.cloneNode(true);
    title.querySelectorAll(".headerlink").forEach((anchor) => anchor.remove());
    link.setAttribute("aria-label", `${title.textContent.trim()}：打印 / 导出（新标签页）`);
    tools.append(link);
    if (sections.length) {
      const updateTarget = () => {
        const current = currentResource(sections);
        const target = new URL(exportUrl([source.pathname + (current ? "#" + current.id : "")]));
        if (!current) target.searchParams.set("select", "none");
        link.href = target.href;
        link.setAttribute("aria-label", `${current?.dataset.exportTitle || '合集'}：打印 / 导出（新标签页）`);
      };
      article.addEventListener("change", updateTarget);
      link.addEventListener("click", updateTarget);
      link.addEventListener("contextmenu", updateTarget);
      updateTarget();
    }
  };

  const addBatchControls = () => {
    if (document.querySelector(".resource-batch-toolbar")) return;
    const seen = new Set();
    const cards = Array.from(document.querySelectorAll(".resource-export-index > ul > li[data-export-source]"))
      .filter((card) => {
        const source = card.dataset.exportSource;
        if (seen.has(source)) return false;
        seen.add(source);
        return true;
      });
    if (!cards.length) return;
    const grids = document.querySelectorAll(".resource-export-index");
    const toolbar = document.createElement("div");
    toolbar.className = "resource-batch-toolbar";
    toolbar.setAttribute("role", "group");
    toolbar.setAttribute("aria-label", "批量导出资料");
    const total = document.createElement("span");
    total.className = "resource-batch-total";
    total.textContent = `${cards.length} 份站内资料`;
    const all = exportLink(cards.map((card) => card.dataset.exportSource), "导出全部");
    all.title = "合并为一份打印稿，再保存为 PDF";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.textContent = "勾选导出";
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", "resource-batch-selection");
    const choices = cards.map((card) => {
      const label = document.createElement("label");
      label.className = "resource-batch-choice";
      label.hidden = true;
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      const heading = card.querySelector("p:first-child strong");
      const title = heading?.textContent.trim() || "此资料";
      checkbox.setAttribute("aria-label", `选择${title}`);
      label.append(checkbox);
      if (heading) heading.before(label);
      else card.append(label);
      return { label, checkbox, source: card.dataset.exportSource };
    });
    const { controls, update } = selectionControls(choices, "resource-batch-selection");
    controls.hidden = true;
    toolbar.append(total, all, controls, toggle);
    toggle.addEventListener("click", () => {
      const active = controls.hidden;
      controls.hidden = !active;
      toggle.setAttribute("aria-expanded", String(active));
      toggle.textContent = active ? "取消" : "勾选导出";
      grids.forEach((grid) => grid.classList.toggle("resource-selecting", active));
      choices.forEach(({ checkbox, label }) => {
        label.hidden = !active;
        if (!active) checkbox.checked = false;
      });
      update();
    });
    update();
    grids[0].before(toolbar);
  };

  const initialize = () => {
    // A direct paper can itself be named exams or quizzes; classify it before an index.
    addPageEntry();
    if (resourceUrl(new URL(location.pathname, location.origin))) return;
    const section = location.pathname.match(/^(.*\/(?:exams|quizzes)\/)(?:index\.html)?$/);
    if (!section) return;

    // Give every resource in an exam/quiz index the same appearance, including external links.
    document.querySelectorAll(".course-resource-grid").forEach((grid) => {
      grid.classList.add("resource-export-index");
      grid.querySelectorAll(":scope > ul > li").forEach((card) => {
        const paragraphs = Array.from(card.querySelectorAll(":scope > p"));
        paragraphs.forEach((paragraph, index) => {
          // Source notes can follow the links; identify actions by their contents.
          const isAction = paragraph.querySelector(":scope > a[href]") &&
            Array.from(paragraph.childNodes).every((node) => {
              if (node.nodeType === Node.TEXT_NODE) return !node.textContent.trim();
              if (node.nodeType === Node.COMMENT_NODE) return true;
              return node.nodeType === Node.ELEMENT_NODE && node.matches("a[href], .divider");
            });
          paragraph.classList.toggle("resource-index-actions", Boolean(isAction));
          paragraph.classList.toggle("resource-index-note", index > 0 && !isAction);
        });

        // Match the catalog: the resource name itself is the primary entry.
        const title = card.querySelector(":scope > p:first-child > strong");
        const source = card.querySelector(":scope > p.resource-index-actions > a[href]:not(.resource-export-link)");
        if (title && source && !title.querySelector("a")) {
          const titleLink = source.cloneNode(false);
          titleLink.className = "resource-index-title";
          titleLink.removeAttribute("id");
          titleLink.removeAttribute("aria-label");
          titleLink.append(...title.childNodes);
          title.append(titleLink);
        }

        // Keep actions under their title; existing badges and descriptions follow them.
        const heading = card.querySelector(":scope > p:first-child");
        if (heading?.querySelector(":scope > strong")) {
          const metadata = heading.querySelectorAll(":scope > .exam-resource-tag, :scope > .course-resource-detail");
          const notes = card.querySelectorAll(":scope > p.resource-index-note");
          card.append(...metadata, ...notes);
        }
      });
    });

    document.querySelectorAll(".course-resource-grid.resource-export-index > ul > li > p.resource-index-actions").forEach((actions) => {
      const links = Array.from(actions.parentElement.querySelectorAll(":scope > p.resource-index-actions > a[href]:not(.resource-export-link)"));
      // An original-post reference does not prevent exporting the local paper.
      const targets = links.map((link) => resourceUrl(link.href))
        .filter((url) => url && url.pathname.startsWith(section[1]));
      const unique = new Map(targets.map((url) => [url.pathname, url]));
      if (unique.size !== 1) return;
      const target = unique.values().next().value;
      const primary = links.find((link) => resourceUrl(link.href)?.pathname === target.pathname);
      if (primary.parentElement !== actions) return;
      actions.parentElement.dataset.exportSource = target.pathname;
      if (actions.classList.contains("resource-export-actions")) return;

      const divider = document.createElement("span");
      divider.className = "divider";
      divider.textContent = "|";
      divider.setAttribute("aria-hidden", "true");

      const link = exportLink([target.pathname], "打印 / 导出");
      link.className = "resource-export-link";
      if (primary.classList.contains("resource-collection-link")) {
        const selection = new URL(link.href);
        selection.searchParams.set("select", "none");
        link.href = selection.href;
      }
      const title = actions.parentElement.querySelector("p:first-child strong")?.textContent.trim();
      link.setAttribute("aria-label", `${title || "此资料"}：打印 / 导出（新标签页）`);
      actions.classList.add("resource-export-actions", "link-divider");
      actions.parentElement.classList.add("resource-export-card");
      actions.append(divider, link);
    });
    addBatchControls();
  };

  if (typeof document$ !== "undefined") document$.subscribe(initialize);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();
