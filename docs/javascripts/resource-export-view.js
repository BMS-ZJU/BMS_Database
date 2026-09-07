(() => {
  const siteRoot = new URL("./", location.href);
  const paper = document.querySelector(".paper");
  const status = document.querySelector("#export-status");
  const printButton = document.querySelector("#print-resource");
  const answerMode = document.querySelector("#answer-mode");
  let title = "资料";
  const papers = [];
  let supportsEndAnswers = false;
  let mathAssetsReady = null;
  let ready = false;

  const withTimeout = (promise, message, duration = 20000) => {
    let timer;
    return Promise.race([
      promise,
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(message)), duration); }),
    ]).finally(() => clearTimeout(timer));
  };

  const sourceError = "此链接不是可导出的站内试卷或小测，请从资料列表重新选择。";

  const validateSource = (value) => {
    let url;
    let path;
    try {
      url = new URL(value, siteRoot);
      path = decodeURIComponent(url.pathname.slice(siteRoot.pathname.length));
    } catch { throw new Error(sourceError); }
    const match = /^(mandatory|elective)\/([^/]+)\/(exams|quizzes)\/([^/]+?)(?:\/|\.html)$/.exec(path);
    if (url.origin !== location.origin || !url.pathname.startsWith(siteRoot.pathname) ||
        url.username || url.password || url.search || url.hash || !match ||
        /[%\\?#\u0000-\u0020]/.test(path) ||
        [match[2], match[4]].some((part) => [".", "..", "index"].includes(part.toLowerCase()))) {
      throw new Error(sourceError);
    }
    // Normalize percent-encoded spellings before deduplication and index checks.
    url.pathname = siteRoot.pathname + path;
    return url;
  };

  const sourceIndex = (url) => new URL(url.pathname.endsWith("/") ? "../" : "./", url);

  const getSources = () => {
    const values = new URL(location.href).searchParams.getAll("source");
    if (!values.length) throw new Error("请从试卷或小测资料列表选择要导出的资料。");
    const unique = new Map();
    values.forEach((value, index) => {
      let url;
      try {
        if (!value) throw new Error(sourceError);
        url = validateSource(value);
      } catch (error) {
        throw new Error(values.length > 1 ? `第 ${index + 1} 份资料的地址无效。${error.message}` : error.message);
      }
      if (!unique.has(url.href)) unique.set(url.href, url);
    });
    const sources = Array.from(unique.values());
    if (sources.some((url) => sourceIndex(url).href !== sourceIndex(sources[0]).href)) {
      throw new Error("请从同一个试卷或小测资料列表选择要合并的资料。");
    }
    return sources;
  };

  const namespaceReferences = (content, sourceUrl, prefix) => {
    const nodes = [content, ...content.querySelectorAll("*")];
    const id = (value) => `${prefix}${value}`;
    const fragment = (value) => {
      try { return `#${encodeURIComponent(id(decodeURIComponent(value.slice(1))))}`; }
      catch { return `#${encodeURIComponent(id(value.slice(1)))}`; }
    };
    const references = ["for", "headers", "list", "form", "aria-labelledby", "aria-describedby",
      "aria-controls", "aria-owns", "aria-flowto", "aria-activedescendant", "aria-details", "aria-errormessage"];
    nodes.forEach((node) => {
      if (node.id) node.id = id(node.id);
      if (node.matches("a[name], map[name]")) node.setAttribute("name", id(node.getAttribute("name")));
      references.forEach((attribute) => {
        if (node.hasAttribute(attribute)) node.setAttribute(attribute,
          node.getAttribute(attribute).split(/\s+/).filter(Boolean).map(id).join(" "));
      });
      ["href", "xlink:href", "usemap"].forEach((attribute) => {
        if (!node.hasAttribute(attribute)) return;
        const value = node.getAttribute(attribute);
        const url = new URL(value, sourceUrl);
        if (value.startsWith("#") || (url.origin === sourceUrl.origin &&
            url.pathname === sourceUrl.pathname && url.search === sourceUrl.search && url.hash)) {
          const target = fragment(value.startsWith("#") ? value : url.hash);
          if (attribute === "xlink:href") node.setAttributeNS("http://www.w3.org/1999/xlink", attribute, target);
          else node.setAttribute(attribute, target);
        }
      });
      // SVG paint/filter references and inline styles can also refer to an in-document ID.
      Array.from(node.attributes).forEach((attribute) => {
        const value = attribute.value.replace(/url\(\s*(["']?)#([^\s)'"]+)\1\s*\)/g,
          (_, quote, target) => `url(${quote}${fragment(`#${target}`)}${quote})`);
        if (value !== attribute.value) node.setAttribute(attribute.name, value);
      });
    });
  };

  const formatPaperHeader = (content) => {
    const heading = content.querySelector(":scope > h1");
    if (!heading) return;
    heading.classList.add("paper-title");
    let node = heading.nextElementSibling;
    while (node) {
      if (node.matches("blockquote")) {
        // Only simple, short metadata before the first section/question is rearranged.
        if (!Array.from(node.children).every((child) => child.matches("p")) ||
            node.querySelector("img, .arithmatex, table, ul, ol") || node.textContent.length > 240) break;
        const fields = [];
        node.querySelectorAll(":scope > p").forEach((paragraph) => {
          let field = document.createDocumentFragment();
          Array.from(paragraph.childNodes).forEach((child) => {
            if (child.nodeName === "BR") {
              if (field.textContent.trim()) fields.push(field);
              field = document.createDocumentFragment();
            } else field.append(child.cloneNode(true));
          });
          if (field.textContent.trim()) fields.push(field);
        });
        node.classList.add("paper-header-meta");
        node.replaceChildren(...fields.map((field) => {
          const item = document.createElement("span");
          item.className = "paper-header-field";
          item.append(field);
          return item;
        }));
      } else if (node.matches(".admonition") &&
                 ["回忆卷说明", "试卷说明"].includes(node.querySelector(":scope > .admonition-title")?.textContent.trim())) {
        node.classList.add("paper-header-note");
      } else if (node.matches("p") && /^本页/.test(node.textContent.trim()) &&
                 !node.querySelector("img, .arithmatex")) {
        node.classList.add("paper-header-text");
      } else if (node.matches("hr")) {
        node.classList.add("paper-header-rule");
        node = node.nextElementSibling;
        break;
      } else break;
      node = node.nextElementSibling;
    }
    // Stop at the first body block: never restyle notes embedded in questions.
    if (node?.matches("h2, h3, ol, ul, .tabbed-set")) node.classList.add("paper-body-start");
  };

  const formatWrittenQuestions = (content) => {
    content.querySelectorAll(".exam-section--short, .exam-section--analysis").forEach((heading) => {
      const analysis = heading.classList.contains("exam-section--analysis");
      const level = Number(heading.tagName.slice(1));
      let inCase = false;
      let node = heading.nextElementSibling;
      while (node) {
        if (/^H[1-6]$/.test(node.tagName) && Number(node.tagName.slice(1)) <= level) break;
        if (node.matches(".exam-section")) break;
        if (analysis && /^H[3-6]$/.test(node.tagName)) {
          inCase = true;
          node.classList.add("paper-case-title");
        } else if (node.matches("ol")) {
          node.classList.add(inCase ? "paper-case-questions" : "paper-question-list");
          if (!inCase) {
            node.classList.add(analysis ? "paper-question-list--analysis" : "paper-question-list--short");
            node.querySelectorAll(":scope > li").forEach((item) => {
              item.classList.add("paper-written-question");
              const first = item.firstElementChild;
              if (first?.matches("p") && !first.querySelector("img")) first.classList.add("paper-question-stem");
              item.querySelectorAll(":scope > p").forEach((paragraph) => {
                // Existing parenthesized subquestion labels remain untouched.
                if (/^[（(]\d+[）)]/.test(paragraph.textContent.trim())) paragraph.classList.add("paper-subquestion");
              });
            });
          }
        } else if (inCase && node.matches("p")) {
          if (!node.querySelector("img")) node.classList.add("paper-case-text");
        }
        node = node.nextElementSibling;
      }
    });
  };

  const cleanArticle = (sourceArticle, sourceUrl) => {
    const result = sourceArticle.cloneNode(true);
    result.querySelectorAll(
      "script, style, link, iframe, object, embed, form, button, " +
      ".md-content__button, .headerlink, .footnote-backref, .md-source-file, " +
      ".md-feedback, .giscus, #__comments, .resource-page-tools, .md-typeset__scrollwrap > .md-annotation"
    ).forEach((node) => node.remove());

    // Source-attribution comments stay private to source; do not turn them into a byline.
    const walker = document.createTreeWalker(result, NodeFilter.SHOW_COMMENT);
    const comments = [];
    while (walker.nextNode()) comments.push(walker.currentNode);
    comments.forEach((node) => node.remove());

    result.querySelectorAll(".tabbed-set").forEach((tabs) => {
      const labels = Array.from(tabs.querySelectorAll(":scope > .tabbed-labels label"));
      const blocks = tabs.querySelectorAll(":scope > .tabbed-content > .tabbed-block");
      blocks.forEach((block, index) => {
        if (!labels[index]) return;
        const heading = document.createElement("h3");
        heading.textContent = labels[index].textContent;
        block.prepend(heading);
      });
      tabs.querySelectorAll(":scope > input, :scope > .tabbed-labels").forEach((node) => node.remove());
    });

    result.querySelectorAll("details").forEach((details) => {
      const summary = details.querySelector(":scope > summary");
      const label = summary?.textContent.trim();
      const quizAnswer = details.classList.contains("quiz-answer");
      // These exact headings are standalone answer blocks in the current papers.
      if (quizAnswer || ["参考答案", "答案要点", "给分标准"].includes(label)) {
        const answer = document.createElement("aside");
        answer.className = "quiz-answer";
        if (details.id) answer.id = details.id;
        answer.setAttribute("aria-label", quizAnswer ? "答案" : label);
        if (!quizAnswer) {
          const heading = document.createElement("strong");
          heading.textContent = label;
          answer.append(heading);
        }
        summary?.remove();
        answer.append(...details.childNodes);
        details.replaceWith(answer);
      } else details.open = true;
    });

    result.querySelectorAll("*").forEach((element) => {
      Array.from(element.attributes).forEach((attribute) => {
        if (/^on/i.test(attribute.name) || attribute.name === "srcdoc") element.removeAttribute(attribute.name);
      });
      if (element.hasAttribute("href")) {
        const value = element.getAttribute("href");
        if (!value.startsWith("#")) {
          const url = new URL(value, sourceUrl);
          if (["https:", "http:", "mailto:"].includes(url.protocol)) element.setAttribute("href", url.href);
          else element.removeAttribute("href");
        }
      }
    });
    result.querySelectorAll("img").forEach((img) => {
      const url = new URL(img.getAttribute("src"), sourceUrl);
      if (!["http:", "https:", "data:"].includes(url.protocol)) throw new Error("此资料中有无法加载的题图。");
      img.src = url.href;
      img.removeAttribute("srcset");
      img.loading = "eager";
    });
    result.querySelectorAll(".exam-section").forEach((heading) => {
      const introduction = heading.nextElementSibling;
      // Only the short, italic question-count/score line; never chain case text or images.
      if (introduction?.matches("p") && introduction.children.length === 1 &&
          introduction.firstElementChild.matches("em") && !introduction.querySelector("img") &&
          introduction.textContent.length < 200) introduction.classList.add("keep-with-next");
    });
    formatPaperHeader(result);
    formatWrittenQuestions(result);
    return result;
  };

  const loadAsset = (url, type) => withTimeout(new Promise((resolve, reject) => {
    const element = document.createElement(type === "css" ? "link" : "script");
    if (type === "css") { element.rel = "stylesheet"; element.href = url; }
    else element.src = url;
    element.onload = resolve;
    element.onerror = () => reject(new Error("公式组件加载失败，请检查网络后刷新重试。"));
    document.head.append(element);
  }), "公式组件加载超时，请检查网络后刷新重试。");

  const formatQuestions = ({ answers }) => {
    answers.forEach((answer) => {
      const item = answer.closest("li");
      if (!item) return;
      item.classList.add("quiz-question");
      const paragraphs = Array.from(answer.children);
      if (paragraphs.length === 2 && paragraphs.every((node) => node.matches("p")) &&
          !answer.querySelector("img, .arithmatex, br") && answer.textContent.length < 130) {
        answer.classList.add("quiz-answer--brief");
      }
      item.querySelectorAll(":scope > p").forEach((paragraph) => {
        const lines = [];
        let line = document.createDocumentFragment();
        Array.from(paragraph.childNodes).forEach((node) => {
          if (node.nodeName === "BR") {
            if (line.textContent.trim()) lines.push(line);
            line = document.createDocumentFragment();
          } else line.append(node.cloneNode(true));
        });
        if (line.textContent.trim()) lines.push(line);
        // Only unambiguous true/false options are compacted. Keep long/complex options as-is.
        if (lines.length !== 2 || !lines.every((part) =>
          /^[A-D][.．]\s*(对|错|正确|错误|是|否|True|False|Yes|No)$/i.test(part.textContent.trim()))) return;
        paragraph.classList.add("quiz-options");
        paragraph.replaceChildren(...lines.map((part) => {
          const option = document.createElement("span");
          option.className = "quiz-option";
          option.append(part);
          return option;
        }));
      });
    });
  };

  const questionReference = (answer) => {
    const item = answer.closest("li");
    const list = item?.parentElement;
    if (!list?.matches("ol")) return null;
    const items = Array.from(list.children).filter((node) => node.matches("li"));
    let number = list.hasAttribute("start") ? list.start : list.reversed ? items.length : 1;
    for (const sibling of items) {
      if (sibling.hasAttribute("value")) number = sibling.value;
      if (sibling === item) return { item, list, number };
      number += list.reversed ? -1 : 1;
    }
    return null;
  };

  const answerGroupTitle = (list, article) => {
    const tab = list.closest(".tabbed-block");
    const scope = tab || article;
    const tabTitle = tab?.querySelector(":scope > h3")?.textContent.trim();
    const headings = Array.from(scope.querySelectorAll("h2, h3")).filter((heading) =>
      !heading.closest("li") && (heading.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING));
    const sectionTitle = headings.at(-1)?.textContent.trim();
    return Array.from(new Set([tabTitle, sectionTitle].filter(Boolean))).join(" · ");
  };

  const buildAnswerKey = (entry) => {
    const { article, answers } = entry;
    const references = answers.map(questionReference);
    // Do not invent numbers for answer blocks that have no explicit ordered-list question.
    const supported = answers.length > 0 && references.every(Boolean);
    if (!supported) return false;
    const answerKey = document.createElement("section");
    answerKey.className = "export-answer-key";
    answerKey.hidden = true;
    const heading = document.createElement("h2");
    heading.textContent = "答案与说明";
    answerKey.append(heading);
    const groups = new Map();
    const entries = new Map();
    answers.forEach((answer, index) => {
      const reference = references[index];
      let group = groups.get(reference.list);
      if (!group) {
        group = document.createElement("ol");
        const groupTitle = answerGroupTitle(reference.list, article);
        if (groupTitle) {
          const subheading = document.createElement("h3");
          subheading.textContent = groupTitle;
          answerKey.append(subheading);
        }
        answerKey.append(group);
        groups.set(reference.list, group);
      }
      let entry = entries.get(reference.item);
      if (!entry) {
        entry = document.createElement("li");
        entry.value = reference.number;
        group.append(entry);
        entries.set(reference.item, entry);
      }
      const copy = answer.cloneNode(true);
      copy.hidden = false;
      copy.removeAttribute("id");
      copy.querySelectorAll("[id]").forEach((node) => node.removeAttribute("id"));
      // Markdown details can leave an empty paragraph before the actual answer.
      copy.querySelectorAll(":scope > p").forEach((paragraph) => {
        if (!paragraph.children.length && !paragraph.textContent.trim()) paragraph.remove();
      });
      entry.append(copy);
    });
    groups.forEach((group) => {
      let shortAnswers = 0;
      Array.from(group.children).forEach((entry) => {
        const answer = entry.firstElementChild;
        // Keep explanations and complex answers at full width, without splitting their text.
        const short = entry.children.length === 1 &&
          answer.textContent.replace(/\s/g, "").length <= 10 &&
          answer.querySelectorAll("p").length <= 1 &&
          !answer.querySelector("br, img, .arithmatex, ul, ol, table, pre, blockquote") &&
          Array.from(answer.children).every((node) => node.matches("p, strong"));
        if (short) {
          entry.classList.add("export-answer-short");
          shortAnswers += 1;
        }
      });
      if (shortAnswers > 1) group.classList.add("export-answer-grid");
    });
    article.append(answerKey);
    entry.answerKey = answerKey;
    return true;
  };

  const renderMath = async (article, sourceDocument, sourceUrl) => {
    if (!article.querySelector(".arithmatex")) return;
    const asset = (selector, attribute, pattern) => {
      const node = Array.from(sourceDocument.querySelectorAll(selector)).find((item) => pattern.test(item.getAttribute(attribute)));
      if (!node) throw new Error("此资料的公式暂时无法排版，请返回原文或稍后重试。");
      const url = new URL(node.getAttribute(attribute), sourceUrl);
      if (!["https:", "http:"].includes(url.protocol)) throw new Error("公式组件地址无效。");
      return url.href;
    };
    if (!mathAssetsReady) {
      const css = asset("link[href]", "href", /\/katex(?:\.min)?\.css(?:\?|$)/);
      const core = asset("script[src]", "src", /\/katex\.min\.js(?:\?|$)/);
      const auto = asset("script[src]", "src", /\/auto-render(?:\.min)?\.js(?:\?|$)/);
      mathAssetsReady = (async () => {
        await Promise.all([loadAsset(css, "css"), loadAsset(core, "js")]);
        await loadAsset(auto, "js");
      })();
    }
    await mathAssetsReady;
    let mathFailed = false;
    window.renderMathInElement(article, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false },
        { left: "\\[", right: "\\]", display: true },
      ],
      throwOnError: true,
      errorCallback: () => { mathFailed = true; },
    });
    if (mathFailed || article.querySelector(".katex-error")) throw new Error("部分公式未能正确排版，请返回原文核对。");
  };

  const groupShortQuestions = (article) => {
    // Measure at the actual printable width, independent of the phone viewport.
    const measuring = document.createElement("div");
    measuring.className = "export-measure";
    // beforeprint also runs under print media, where non-paper UI is hidden.
    measuring.style.setProperty("display", "block", "important");
    measuring.setAttribute("aria-hidden", "true");
    const copy = article.cloneNode(true);
    copy.removeAttribute("id");
    copy.querySelectorAll("[id]").forEach((node) => node.removeAttribute("id"));
    measuring.append(copy);
    document.body.append(measuring);
    const originals = article.querySelectorAll("li");
    const measuredItems = new Map();
    copy.querySelectorAll("li").forEach((item, index) => {
      originals[index].classList.remove("paper-keep-next-question");
      const written = !!item.closest(".paper-question-list, .paper-case-questions");
      const multipart = item.classList.contains("paper-written-question") &&
        !!item.querySelector("ol, ul, img, table, blockquote, .paper-subquestion");
      // Keep small text questions/subquestions together; let multipart case material flow.
      const limit = written ? 190 : 340;
      const keep = !multipart && item.getBoundingClientRect().height < limit;
      originals[index].classList.toggle("keep-together", keep);
      measuredItems.set(item, { original: originals[index], keep });
    });
    copy.querySelectorAll(".paper-question-list--short").forEach((list) => {
      const items = Array.from(list.children).filter((node) => node.matches("li"));
      const previous = items.at(-2);
      const last = items.at(-1);
      if (!previous || !measuredItems.get(previous)?.keep || !measuredItems.get(last)?.keep) return;
      // Avoid a lone final question without locking a long pair or an entire section together.
      if (last.getBoundingClientRect().bottom - previous.getBoundingClientRect().top < 110) {
        measuredItems.get(previous).original.classList.add("paper-keep-next-question");
      }
    });
    measuring.remove();
  };

  const updateAnswers = () => {
    if (answerMode.value === "end" && !supportsEndAnswers) answerMode.value = "answers";
    papers.forEach(({ article, answers, answerKey }) => {
      answers.forEach((answer) => { answer.hidden = answerMode.value !== "answers"; });
      if (answerKey) answerKey.hidden = answerMode.value !== "end";
      groupShortQuestions(article);
    });
    const labels = { questions: "仅题目", answers: "答案随题", end: "答案附后" };
    const suffix = papers.some((entry) => entry.answers.length) ? `（${labels[answerMode.value]}）` : "";
    document.title = `${title}${suffix}`;
  };

  const fetchSource = async (sourceUrl) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(sourceUrl, { signal: controller.signal, credentials: "same-origin" });
      if (!response.ok) throw new Error("资料加载失败，请返回原文或刷新重试。");
      const finalUrl = validateSource(response.url);
      if (sourceIndex(finalUrl).href !== sourceIndex(sourceUrl).href) {
        throw new Error("资料地址已改变，请返回资料列表重新选择。");
      }
      return { sourceUrl: finalUrl, html: await response.text() };
    } finally { clearTimeout(timer); }
  };

  const prepare = async () => {
    let sources = [];
    let completed = 0;
    let currentLabel = "";
    let currentIndex = 0;
    ready = false;
    printButton.disabled = true;
    try {
      sources = getSources();
      const batch = sources.length > 1;
      document.body.classList.toggle("resource-export-batch", batch);
      const sourceLink = document.querySelector("#source-link");
      sourceLink.href = batch ? sourceIndex(sources[0]).href : sources[0].href;
      sourceLink.textContent = batch ? "返回资料列表" : "返回原文";
      title = batch ? `资料合集（${sources.length} 份）` : "资料";
      paper.replaceChildren();

      // Fetch and prepare one paper at a time, keeping the user's selection order.
      for (const [index, requestedUrl] of sources.entries()) {
        currentIndex = index + 1;
        currentLabel = decodeURIComponent(requestedUrl.pathname.split("/").filter(Boolean).at(-1)).replace(/\.html$/, "");
        status.textContent = batch ? `已准备 ${completed}/${sources.length} 份资料。正在准备第 ${currentIndex} 份…` : "正在准备资料…";
        const { sourceUrl, html } = await fetchSource(requestedUrl);
        if (papers.some((entry) => entry.sourceUrl.href === sourceUrl.href)) {
          throw new Error("资料重定向后与已选资料重复，请返回资料列表重新选择。");
        }
        const parsed = new DOMParser().parseFromString(html, "text/html");
        const original = parsed.querySelector("article.md-content__inner");
        if (!original?.querySelector("h1")) throw new Error("未找到试卷正文，请返回资料列表重新选择。");
        const cleaned = cleanArticle(original, sourceUrl);
        const article = document.createElement("article");
        article.className = "paper-content";
        if (cleaned.id) article.id = cleaned.id;
        article.append(...cleaned.childNodes);
        paper.append(article);
        currentLabel = article.querySelector("h1").textContent.trim();
        const entry = { article, sourceUrl, title: currentLabel, answers: Array.from(article.querySelectorAll(".quiz-answer")), answerKey: null };
        if (!batch) title = entry.title;

        await Promise.all([
          renderMath(article, parsed, sourceUrl),
          withTimeout(Promise.all(Array.from(article.querySelectorAll("img")).map((img) => img.decode())),
            "题图加载超时，请检查网络后刷新重试。"),
        ]);
        // Flush layout so fonts used by this paper enter the font-loading set.
        article.getBoundingClientRect();
        await withTimeout(document.fonts.ready, "字体加载超时，请刷新重试。");
        formatQuestions(entry);
        entry.supportsEndAnswers = buildAnswerKey(entry);
        if (batch) namespaceReferences(article, sourceUrl, `export-paper-${currentIndex}-`);
        papers.push(entry);
        completed += 1;
      }

      const hasAnswers = papers.some((entry) => entry.answers.length);
      supportsEndAnswers = hasAnswers && papers.every((entry) => !entry.answers.length || entry.supportsEndAnswers);
      const endOption = answerMode.querySelector("option[value='end']");
      endOption.textContent = batch ? "答案集中在每份资料后" : "答案集中卷末";
      endOption.hidden = !supportsEndAnswers;
      endOption.disabled = !supportsEndAnswers;
      document.querySelector("#answer-options").hidden = !hasAnswers;
      updateAnswers();
      paper.setAttribute("aria-busy", "false");
      printButton.disabled = false;
      ready = true;
      status.textContent = batch ? `已准备 ${completed}/${sources.length} 份资料。可直接打印，或在打印窗口中保存 PDF。` :
        "已就绪。可直接打印，或在打印窗口中保存 PDF。";
    } catch (error) {
      ready = false;
      printButton.disabled = true;
      paper.replaceChildren();
      papers.length = 0;
      paper.setAttribute("aria-busy", "false");
      status.setAttribute("role", "alert");
      const message = error.name === "AbortError" ? "资料加载超时，请刷新重试。" :
        error instanceof DOMException ? "题图未能完整加载，请检查网络后刷新重试。" : error.message;
      status.textContent = sources.length > 1 ?
        `第 ${currentIndex} 份“${currentLabel}”准备失败：${message} 已准备 ${completed}/${sources.length} 份，整批打印未启用。` : message;
    }
  };

  answerMode.addEventListener("change", () => { if (ready) updateAnswers(); });
  printButton.addEventListener("click", () => { if (ready) window.print(); });
  window.addEventListener("beforeprint", () => { if (ready) papers.forEach(({ article }) => groupShortQuestions(article)); });
  prepare();
})();
