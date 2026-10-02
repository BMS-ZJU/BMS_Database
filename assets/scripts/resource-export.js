(() => {
  // Resolve from this asset so project sites and local previews share the same paths.
  const scriptUrl = new URL(document.currentScript.src);
  const siteRoot = new URL(scriptUrl.pathname.replace(/\/(?:assets\/scripts|javascripts)\/[^/]+$/, "/"), scriptUrl);
  const previewUrl = new URL("resource-export.html", siteRoot);

  const resourceUrl = (value) => {
    let url;
    try { url = new URL(value, location.href); }
    catch { return null; }
    const path = url.pathname.slice(siteRoot.pathname.length);
    if (url.origin !== location.origin || !url.pathname.startsWith(siteRoot.pathname) ||
        url.search || url.hash ||
        !/^(courses)\/[^/]+\/(exams|quizzes)\/[^/]+(?:\/|\.html)$/.test(path) ||
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

  const rotatingDivider = () => {
    const divider = document.createElement("span");
    divider.className = "divider";
    divider.textContent = "|";
    divider.setAttribute("aria-hidden", "true");
    return divider;
  };

  const formatPaperHeading = (heading) => {
    if (heading.querySelector(":scope > .resource-title-term")) return;
    const text = heading.firstChild;
    if (!text || text.nodeType !== Node.TEXT_NODE) return;
    const term = text.textContent.match(/^(\d{4}-\d{4}\s*学年(?:(?:春夏|秋冬|春|夏|秋|冬)学期)?\s*)/);
    if (!term || !text.textContent.slice(term[0].length).trim()) return;
    // Preserve the exact title text, permalink and anchor; CSS controls the line break.
    const name = text.splitText(term[0].length);
    const line = document.createElement("span");
    line.className = "resource-title-term";
    text.replaceWith(line);
    line.append(text);
    // Keep short material names intact when the course name wraps on narrow screens.
    const kind = name.textContent.match(/(?:期中|期末|缓考)?(?:回忆卷|试卷)$|(?:小测题整理|题目整理|试题及答案|参考答案|小测合集|练习与小测|三次小测题目|线上自测合集|（回忆整理）)$/);
    if (kind) {
      const label = document.createElement("span");
      label.className = "resource-title-kind";
      const tail = name.splitText(kind.index);
      tail.replaceWith(label);
      label.append(tail);
    }
  };

  const addPageEntry = () => {
    const source = resourceUrl(new URL(location.pathname, location.origin));
    const article = document.querySelector("article.md-content__inner");
    // Classify reading typography before export controls can return early.
    article?.classList.toggle("reading-paper", Boolean(source));
    const heading = article?.querySelector(":scope > h1");
    if (!source || !heading) return;
    formatPaperHeading(heading);
    if (article.querySelector(".resource-page-tools")) return;
    const tools = document.createElement("p");
    tools.className = "resource-page-tools";
    heading.after(tools);
    const link = exportLink([source.pathname], "打印 / 保存 PDF");
    const target = new URL(link.href);
    target.searchParams.set("select", "first");
    link.href = target.href;
    link.className = "resource-export-link";
    link.title = "打开打印预览，可通过浏览器保存为 PDF";
    const title = heading.cloneNode(true);
    title.querySelectorAll(".headerlink").forEach((anchor) => anchor.remove());
    link.setAttribute("aria-label", `${title.textContent.trim()}：打印 / 保存 PDF（新标签页）`);
    tools.append(link);
  };

  const addIndexPrintEntry = () => {
    if (document.querySelector(".resource-index-print")) return;
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
    toolbar.className = "resource-batch-toolbar resource-index-print";
    const link = exportLink(cards.map((card) => card.dataset.exportSource), "打印 / 保存 PDF");
    link.title = "在打印预览中选择资料，再打印或保存为 PDF";
    link.setAttribute("aria-label", "打印 / 保存 PDF（新标签页）");
    toolbar.setAttribute("role", "group");
    toolbar.setAttribute("aria-label", "资料打印");
    const target = new URL(link.href);
    target.searchParams.set("select", "first");
    link.href = target.href;
    toolbar.append(link);
    // These controls cover every group on the current directory.
    let toolbarAnchor = grids[0];
    if (grids.length > 1) {
      let previous = grids[0].previousElementSibling;
      while (previous && !/^H[12]$/.test(previous.tagName)) previous = previous.previousElementSibling;
      if (previous?.tagName === "H2") toolbarAnchor = previous;
    }
    toolbarAnchor.before(toolbar);
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
              if (node.nodeType === Node.TEXT_NODE) return /^[\s·|]*$/.test(node.textContent);
              if (node.nodeType === Node.COMMENT_NODE) return true;
              return node.nodeType === Node.ELEMENT_NODE && node.matches("a[href], .divider");
            });
          paragraph.classList.toggle("resource-index-actions", Boolean(isAction));
          paragraph.classList.toggle("resource-index-note", index > 0 && !isAction);
        });

        // Markdown may put reading and practice links in separate paragraphs.
        // Keep any additional reading and practice links in one action row.
        const rows = Array.from(card.querySelectorAll(":scope > p.resource-index-actions"));
        if (rows.length > 1) {
          rows.slice(1).forEach((row) => {
            rows[0].append(...row.childNodes);
            row.remove();
          });
        }
        const actions = rows[0];
        if (actions) {
          // Normalize literal Markdown separators as well as generated dividers.
          Array.from(actions.childNodes).filter((node) => node.nodeType === Node.TEXT_NODE)
            .forEach((node) => node.remove());
          const practice = actions.querySelector(":scope > .resource-practice-link");
          const read = actions.querySelector(":scope > .resource-read-link");
          if (practice && read) {
            actions.prepend(read);
            read.after(practice);
          }
          // Rebuild separators after merging/reordering links; instant navigation may repeat this.
          actions.querySelectorAll(":scope > .divider").forEach((divider) => divider.remove());
          const links = Array.from(actions.querySelectorAll(":scope > a[href]"));
          actions.classList.toggle("link-divider", links.length > 1);
          links.slice(1).forEach((link) => link.before(rotatingDivider()));
        }

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

    // Index export belongs to the shared toolbar; cards retain reading and practice.
    document.querySelectorAll(".course-resource-grid.resource-export-index > ul > li").forEach((card) => {
      const links = Array.from(card.querySelectorAll(":scope > p.resource-index-actions > a[href]"));
      // An original-post reference does not prevent exporting the local paper.
      const targets = links.map((link) => resourceUrl(link.href))
        .filter((url) => url && url.pathname.startsWith(section[1]));
      const unique = new Map(targets.map((url) => [url.pathname, url]));
      if (unique.size !== 1) return;
      const target = unique.values().next().value;
      card.dataset.exportSource = target.pathname;
    });
    addIndexPrintEntry();
  };

  if (typeof document$ !== "undefined") document$.subscribe(initialize);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();
