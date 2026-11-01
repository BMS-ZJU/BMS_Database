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

  // Directory cards and their print entry are rendered by hooks/resource_indexes.py.
  const initialize = addPageEntry;

  if (typeof document$ !== "undefined") document$.subscribe(initialize);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();
