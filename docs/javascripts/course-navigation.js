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

  const initialize = () => {
    initCourseCatalog();
    initCurriculumToc();
    stripCreditFromToc();
  };

  if (typeof document$ !== "undefined") {
    document$.subscribe(initialize);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }
})();
