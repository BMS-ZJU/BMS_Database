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

  const initialize = () => {
    initCourseCatalog();
    initCurriculumToc();
  };

  if (typeof document$ !== "undefined") {
    document$.subscribe(initialize);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }
})();
