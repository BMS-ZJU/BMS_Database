(() => {
  const normalizeSearchText = (value) =>
    value.normalize("NFKC").toLocaleLowerCase("zh-CN").replace(/\s+/g, "");

  const initCourseCatalog = () => {
    const input = document.querySelector("[data-course-search-input]");
    const catalog = document.querySelector("[data-course-catalog]");

    if (!input || !catalog || input.dataset.courseSearchReady === "true") {
      return;
    }

    const items = Array.from(catalog.querySelectorAll("[data-course-search]"));
    const groups = Array.from(catalog.querySelectorAll("[data-course-group]"));
    const unavailableGroups = Array.from(
      catalog.querySelectorAll("[data-course-unavailable-group]")
    );
    const count = document.querySelector("[data-course-count]");
    const empty = document.querySelector("[data-course-empty]");

    const filterCourses = () => {
      const query = normalizeSearchText(input.value.trim());
      let visible = 0;

      items.forEach((item) => {
        const matches = normalizeSearchText(item.dataset.courseSearch || "").includes(query);
        item.hidden = !matches;
        visible += matches ? 1 : 0;
      });

      groups.forEach((group) => {
        group.hidden = !Array.from(group.querySelectorAll("[data-course-search]")).some(
          (item) => !item.hidden
        );
      });

      unavailableGroups.forEach((details) => {
        const hasMatch = Array.from(details.querySelectorAll("[data-course-search]")).some(
          (item) => !item.hidden
        );
        details.hidden = query ? !hasMatch : false;

        if (query && hasMatch && !details.open) {
          details.dataset.courseSearchOpened = "true";
          details.open = true;
        } else if (!query && details.dataset.courseSearchOpened === "true") {
          details.open = false;
          delete details.dataset.courseSearchOpened;
        }
      });

      if (count) {
        count.textContent = query ? `${visible} / ${items.length} 门课程` : `${items.length} 门课程`;
      }

      if (empty) {
        empty.hidden = visible !== 0;
      }
    };

    input.dataset.courseSearchReady = "true";
    input.addEventListener("input", filterCourses);
    filterCourses();
  };

  const getActiveTabbedBlock = (tabbedSet) => {
    if (!tabbedSet) {
      return null;
    }

    const inputs = Array.from(tabbedSet.querySelectorAll(":scope > input[type='radio']"));
    const content = tabbedSet.querySelector(":scope > .tabbed-content");
    const blocks = content
      ? Array.from(content.children).filter((element) => element.classList.contains("tabbed-block"))
      : [];
    const activeIndex = inputs.findIndex((input) => input.checked);

    return activeIndex >= 0 ? blocks[activeIndex] || null : null;
  };

  const initCurriculumToc = () => {
    const page = document.querySelector(".md-content .md-typeset");
    const yearTabs = page?.querySelector(":scope > .tabbed-set");
    const toc = document.querySelector(".md-sidebar--secondary .md-nav--secondary");

    if (!yearTabs || !toc || yearTabs.dataset.curriculumTocReady === "true") {
      return;
    }

    const curriculumLinks = Array.from(toc.querySelectorAll("a")).filter((link) =>
      new URL(link.href, window.location.href).hash.startsWith("#curriculum-")
    );
    if (!curriculumLinks.length) {
      return;
    }

    const updateCurriculumToc = () => {
      const yearBlock = getActiveTabbedBlock(yearTabs);
      const planTabs = yearBlock?.querySelector(":scope > .tabbed-set");
      const planBlock = getActiveTabbedBlock(planTabs);
      const marker = planBlock?.querySelector("[data-curriculum-plan]");
      const plan = marker?.dataset.curriculumPlan;

      if (!plan) {
        return;
      }

      const activePrefix = `#curriculum-${plan}-`;
      curriculumLinks.forEach((link) => {
        const item = link.closest("li");
        const visible = new URL(link.href, window.location.href).hash.startsWith(activePrefix);
        if (item) {
          item.hidden = !visible;
          item.setAttribute("aria-hidden", String(!visible));
        }
      });

      toc.dataset.curriculumPlan = plan;
    };

    yearTabs.dataset.curriculumTocReady = "true";
    yearTabs.addEventListener("change", () => requestAnimationFrame(updateCurriculumToc));
    updateCurriculumToc();
  };

  const stripCreditFromToc = () => {
    // 右侧目录由标题生成，会把标题里 <span> 的学分文本一并纳入；
    // 这里去掉每条目录末尾的学分，让目录只保留课程/章节名。
    const creditPattern =
      /\s*(?:选择其中一个模块修读[，,]?)?(?:至少修读|推荐修读|修读|共)\s*[\d.]+\s*学分\s*$/;
    document
      .querySelectorAll(".md-sidebar--secondary .md-nav--secondary .md-nav__link")
      .forEach((link) => {
        const ellipsis = link.querySelector(".md-ellipsis");
        if (!ellipsis) return;
        const cleaned = ellipsis.textContent.replace(creditPattern, "");
        if (cleaned !== ellipsis.textContent) {
          ellipsis.textContent = cleaned;
        }
      });
    document
      .querySelectorAll(".md-sidebar--secondary .md-nav--secondary nav.md-nav")
      .forEach((nav) => {
        const label = nav.getAttribute("aria-label");
        if (label) {
          nav.setAttribute("aria-label", label.replace(creditPattern, ""));
        }
      });
  };

  const collections = new WeakMap();

  const tabPath = (target) => {
    const path = [];
    for (let block = target.closest('.tabbed-block'); block;) {
      const set = block.parentElement?.closest('.tabbed-set');
      if (!set) break;
      const blocks = Array.from(set.querySelectorAll(':scope > .tabbed-content > .tabbed-block'));
      path.unshift(set.querySelectorAll(':scope > input[type="radio"]')[blocks.indexOf(block)]);
      block = set.parentElement?.closest('.tabbed-block');
    }
    return path.filter(Boolean);
  };

  const revealTabs = (target) => {
    let changed = false;
    tabPath(target).forEach((input) => {
      if (input.checked) return;
      input.checked = true;
      input.dispatchEvent(new Event('change', { bubbles: true }));
      changed = true;
    });
    return changed;
  };

  const initResourceCollections = () => {
    document.querySelectorAll('.resource-collection-marker').forEach((marker) => {
      const root = marker.closest('article');
      const set = marker.nextElementSibling;
      if (!root || collections.has(root) || !set?.matches('.tabbed-set')) return;
      const sections = Array.from(set.querySelectorAll('section[id][data-export-title]'));
      const inputs = Array.from(set.querySelectorAll('input[type="radio"]'));
      if (!sections.length) return;
      root.classList.add('resource-collection');
      const current = () => sections.find((section) => tabPath(section).every((input) => input.checked));
      let restoring = false;
      const sync = () => {
        const section = current();
        if (!section) return;
        const summary = root.querySelector('[data-answer-summary]');
        if (summary) summary.hidden = section.dataset.exportGroup !== summary.dataset.exportGroup;
        const hash = '#' + section.id;
        if (!restoring && location.hash !== hash) history.pushState(history.state, '', hash);
      };
      const selectTarget = (target) => {
        restoring = true;
        const destination = target.matches('.resource-category-anchor')
          ? target.closest('.tabbed-block').querySelector('section[data-export-title]')
          : target.closest('[data-answer-summary]') ? sections[0] : target;
        const changed = revealTabs(destination);
        sync();
        restoring = false;
        return changed;
      };
      // Native radios retain each category's selection. Keep stable material URLs
      // and instant-navigation history without Material's generated-ID replacement.
      set.addEventListener('click', (event) => {
        if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        const label = event.target.closest('label');
        const input = label?.control;
        if (!inputs.includes(input)) return;
        event.preventDefault();
        event.stopPropagation();
        input.click();
        sync();
      }, true);
      inputs.forEach((input) => input.addEventListener('change', sync));
      collections.set(root, { selectTarget, reset: () => selectTarget(sections[0]) });
      selectTarget(sections[0]);
    });
  };

  const revealPaperSection = (hash) => {
    // 资料合集的目录可以指向未选中的套卷；先展开对应标签，再沿用章节锚点。
    if (!/\/(?:mandatory|elective)\/[^/]+\/(?:exams|quizzes)\//.test(window.location.pathname)) {
      return null;
    }
    let id;
    try {
      id = decodeURIComponent(hash.replace(/^#/, ""));
    } catch {
      return null;
    }
    const target = id && (document.getElementById(id) ||
      document.querySelector(`.md-content section[id][data-legacy-fragment~="${CSS.escape(id)}"]`));
    if (!target || !target.closest(".md-content")) return null;

    // Retired fragments point to existing material, without an empty heading.
    const redirected = target.id !== id;
    if (redirected) history.replaceState(history.state, '', '#' + target.id);
    const controller = collections.get(target.closest('.resource-collection'));
    const changed = controller ? controller.selectTarget(target) : revealTabs(target);
    return changed || redirected ? target : null;
  };

  const revealCurriculumSection = (hash) => {
    if (!/\/curricula\/(?:index\.html)?$/.test(window.location.pathname)) return null;
    let id;
    try {
      id = decodeURIComponent(hash.replace(/^#/, ""));
    } catch {
      return null;
    }
    const target = id.startsWith("curriculum-") && document.getElementById(id);
    const block = target && target.closest(".tabbed-block");
    if (!block?.querySelector(".curriculum-plan-marker")) return null;
    if (!revealTabs(target)) return null;
    // 旧章节别名是空 span, 用实际标题定位; 普通说明定位到提示框。
    return target.closest("h4, h5, .admonition") || target;
  };

  const revealPageHash = () => {
    if (!window.location.hash) {
      document.querySelectorAll('.resource-collection').forEach((root) => collections.get(root)?.reset());
      return;
    }
    const curriculumTarget = revealCurriculumSection(window.location.hash);
    const target = curriculumTarget || revealPaperSection(window.location.hash);
    if (target) requestAnimationFrame(() => {
      target.scrollIntoView();
      if (curriculumTarget) {
        // 别名和提示框不一定有主题的标题滚动留白, 避免被固定页眉遮住。
        const headerBottom = document.querySelector(".md-header")?.getBoundingClientRect().bottom || 0;
        const offset = target.getBoundingClientRect().top - headerBottom - 8;
        if (offset < 0) window.scrollBy(0, offset);
      }
    });
  };

  document.addEventListener("click", (event) => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest?.(".md-nav--secondary a[href]");
    if (!link) return;
    const url = new URL(link.href, window.location.href);
    if (url.origin === window.location.origin && url.pathname === window.location.pathname && url.hash) {
      revealPaperSection(url.hash);
    }
  }, true);
  window.addEventListener("hashchange", revealPageHash);
  window.addEventListener("popstate", revealPageHash);

  const initialize = () => {
    initCourseCatalog();
    initCurriculumToc();
    stripCreditFromToc();
    initResourceCollections();
    requestAnimationFrame(revealPageHash);
  };

  if (typeof document$ !== "undefined") {
    document$.subscribe(initialize);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }
})();
