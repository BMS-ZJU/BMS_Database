/* Course/page selection only. Text, attachments and submission stay on GitHub. */
(() => {
  "use strict";
  const kinds = {
    material: ["提交资料或学习经验", "提供新的笔记、原始资料或学习经历。还没有资料页时，选择课程主页即可。", "去 GitHub 填写资料"],
    correction: ["纠错或补充页面", "指出所选页面的问题位置、原文或现象，再填写修改建议与依据。不知道怎么修也可以提交。", "去 GitHub 填写纠错"]
  };
  function node(tag, text, className) {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    if (className) el.className = className;
    return el;
  }
  function searchable(select) {
    const wrapper = select.parentElement;
    const shell = node("div", "", "contribution-combobox course-catalog-search-row");
    const input = node("input");
    input.id = select.id + "-search";
    input.type = "text";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.dataset.search = select.dataset.field;
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-haspopup", "listbox");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-required", "true");
    const menu = node("div", "", "contribution-options");
    menu.id = select.id + "-options";
    menu.setAttribute("role", "listbox");
    menu.setAttribute("aria-label", wrapper.querySelector("label").textContent);
    menu.hidden = true;
    input.setAttribute("aria-controls", menu.id);
    const toggle = node("button", "", "contribution-dropdown-toggle");
    toggle.type = "button";
    toggle.tabIndex = -1;
    toggle.setAttribute("aria-label", "展开" + wrapper.querySelector("label").textContent + "选项");
    const chevron = node("span", "", "contribution-chevron");
    chevron.setAttribute("aria-hidden", "true");
    toggle.append(chevron);
    const hint = node("span", "", "contribution-sr-only");
    hint.id = select.id + "-hint";
    hint.setAttribute("role", "status");
    input.setAttribute("aria-describedby", hint.id);
    select.hidden = true;
    wrapper.querySelector("label").htmlFor = input.id;
    shell.append(input, toggle, menu, hint);
    wrapper.append(shell);
    let matches = [];
    let active = -1;
    const normalize = value => value.normalize("NFKC").toLocaleLowerCase();
    function close() {
      menu.hidden = true;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
      active = -1;
    }
    function highlight(index) {
      active = index;
      Array.from(menu.children).forEach((option, i) => {
        option.setAttribute("aria-selected", String(i === active));
      });
      if (active >= 0) {
        const option = menu.children[active];
        input.setAttribute("aria-activedescendant", option.id);
        option.scrollIntoView({block: "nearest"});
      }
    }
    function choose(option) {
      select.value = option.value;
      input.value = option.label;
      input.removeAttribute("aria-invalid");
      input.focus({preventScroll: true});
      close();
      select.dispatchEvent(new Event("change", {bubbles: true}));
    }
    function show(all = false) {
      if (input.disabled) return;
      const tokens = normalize(all ? "" : input.value).trim().split(/\s+/).filter(Boolean);
      matches = Array.from(select.options).filter(option => option.value
        && tokens.every(token => normalize(option.label).includes(token)));
      menu.replaceChildren();
      active = -1;
      input.removeAttribute("aria-activedescendant");
      matches.forEach((option, index) => {
        const item = node("div", option.label, "contribution-option");
        item.id = menu.id + "-" + index;
        item.setAttribute("role", "option");
        item.setAttribute("aria-selected", "false");
        item.tabIndex = -1;
        item.addEventListener("click", () => choose(option));
        menu.append(item);
      });
      if (!matches.length) menu.append(node("p", "没有匹配项，换个关键词试试", "contribution-no-match"));
      hint.textContent = matches.length ? matches.length + " 个匹配选项，用上下键浏览、回车选定。" : "没有匹配选项。";
      menu.hidden = false;
      menu.style.maxHeight = "";
      const rect = input.getBoundingClientRect();
      const viewport = window.visualViewport;
      const top = viewport?.offsetTop || 0;
      const below = top + (viewport?.height || innerHeight) - rect.bottom;
      const above = rect.top - top;
      const opensAbove = below < Math.min(menu.scrollHeight, 300) + 8 && above > below;
      menu.classList.toggle("contribution-options--above", opensAbove);
      menu.style.maxHeight = Math.max(88, Math.min(300, (opensAbove ? above : below) - 12)) + "px";
      input.setAttribute("aria-expanded", "true");
    }
    function refresh() {
      input.value = select.value ? select.selectedOptions[0].label : "";
      input.placeholder = select.disabled ? select.options[0].label
        : "输入关键词，或从列表选择";
      input.disabled = select.disabled;
      toggle.disabled = select.disabled;
      input.removeAttribute("aria-invalid");
      close();
    }
    input.addEventListener("focus", () => {
      if (select.value) input.select();
      show(Boolean(select.value));
    });
    input.addEventListener("click", () => {
      if (menu.hidden) show(Boolean(select.value));
    });
    input.addEventListener("input", () => {
      // Search text is never a committed value, even if it resembles a label.
      if (select.value) {
        select.value = "";
        select.dispatchEvent(new Event("change", {bubbles: true}));
      }
      input.removeAttribute("aria-invalid");
      show();
    });
    input.addEventListener("keydown", event => {
      if (event.isComposing || event.keyCode === 229) return;
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (menu.hidden) show(Boolean(select.value));
        if (matches.length) highlight(event.key === "ArrowDown"
          ? Math.min(active + 1, matches.length - 1)
          : (active < 0 ? matches.length - 1 : Math.max(active - 1, 0)));
      } else if (event.key === "Enter" && !menu.hidden) {
        event.preventDefault();
        if (active >= 0 || matches.length === 1) choose(matches[Math.max(active, 0)]);
      } else if (event.key === "Escape") {
        event.preventDefault();
        close();
      } else if (event.key === "Tab") close();
    });
    shell.addEventListener("focusout", event => {
      if (!shell.contains(event.relatedTarget)) {
        close();
        if (input.value && !select.value) {
          input.setAttribute("aria-invalid", "true");
          hint.textContent = "请从匹配列表选定一项。";
        }
      }
    });
    // Keep mouse selection on the input; touch scrolling remains native.
    menu.addEventListener("mousedown", event => event.preventDefault());
    toggle.addEventListener("mousedown", event => event.preventDefault());
    toggle.addEventListener("click", () => {
      if (!menu.hidden) close();
      else { input.focus({preventScroll: true}); show(true); }
    });
    refresh();
    return {refresh, focus: () => input.focus()};
  }
  async function mount() {
    const root = document.querySelector(".contribution-picker");
    if (!root || root.dataset.mounted) return;
    root.dataset.mounted = "true";
    root.hidden = false;
    const loading = root.querySelector("[data-picker-loading]");
    try {
      const response = await fetch(new URL(root.dataset.catalog, location.href), {cache: "no-cache"});
      if (!response.ok) throw new Error("catalog");
      const data = await response.json();
      if (!root.isConnected) return;
      const list = root.querySelector("[data-picker-list]");
      const status = root.querySelector("[data-picker-status]");
      const add = root.querySelector("[data-picker-add]");
      const params = new URLSearchParams(location.search);
      const selected = data.pages.find(p => p.path === params.get("page"));
      const groups = data.courses.filter(c => data.pages.some(p => p.course === c.id));
      groups.push({id: "unknown", label: "未找到课程或页面 (人工核对)"});
      let sequence = 0;
      const renumber = () => {
        Array.from(list.children).forEach((card, i) => {
          card.querySelector("legend").textContent = "第 " + (i + 1) + " 个页面";
          card.querySelector("[data-remove]").hidden = list.children.length === 1;
        });
      };
      function addCard(initial) {
        const number = ++sequence;
        const card = node("fieldset", "", "contribution-entry");
        card.append(node("legend"));
        function select(label, key) {
          const wrapper = node("div", "", "contribution-field");
          const el = node("select");
          el.id = "contribution-" + number + "-" + key;
          el.dataset.field = key;
          el.required = true;
          const title = node("label", label);
          title.htmlFor = el.id;
          wrapper.append(title, el);
          card.append(wrapper);
          return el;
        }
        const kind = select("这次想做什么", "kind");
        Object.entries(kinds).forEach(([value, labels]) => kind.add(new Option(labels[0], value)));
        kind.value = initial?.kind in kinds ? initial.kind : "material";
        const kindSearch = searchable(kind);
        const help = node("p", "", "contribution-kind-help");
        card.append(help);
        const course = select("课程", "course");
        course.add(new Option("请选择课程", ""));
        groups.forEach(c => course.add(new Option(c.label, c.id)));
        const page = select("页面", "page");
        const courseSearch = searchable(course);
        const pageSearch = searchable(page);
        const view = node("a", "查看页面", "contribution-view");
        view.target = "_blank";
        view.rel = "noopener noreferrer";
        const actions = node("p", "", "resource-page-tools contribution-entry-actions");
        const launch = node("a");
        launch.target = "_blank";
        launch.rel = "noopener noreferrer";
        launch.dataset.launch = "";
        const remove = node("button", "移除", "contribution-remove");
        remove.type = "button";
        remove.dataset.remove = "";
        actions.append(view, launch);
        card.append(remove, actions);
        const state = node("p", "", "contribution-entry-status");
        state.setAttribute("role", "status");
        card.append(state);
        function update() {
          help.textContent = kinds[kind.value]?.[1] || "请从列表选择投稿类型。";
          launch.textContent = (kind.value === "correction" ? "填写纠错" : "填写投稿") + " ↗";
          state.textContent = "";
          const group = groups.find(c => c.id === course.value);
          const item = data.pages.find(p => p.path === page.value && p.course === course.value);
          const valid = kind.value in kinds && group && (item || course.value === "unknown");
          launch.removeAttribute("href");
          launch.setAttribute("aria-disabled", String(!valid));
          if (valid) {
            const url = new URL(data.repository + "/issues/new");
            url.searchParams.set("template", kind.value + ".yml");
            url.searchParams.set("course", group.label);
            url.searchParams.set("page", item ? item.url : "");
            url.searchParams.set("title", (kind.value === "material" ? "[资料] " : "[纠错] ")
              + group.label + (item ? " · " + item.title : ""));
            launch.href = url.href;
          }
          view.hidden = !item;
          view.removeAttribute("href");
          if (item) view.href = item.url;
        }
        function populate(value) {
          page.replaceChildren(new Option(course.value === "unknown" ? "由维护者帮助定位" : "请选择页面", ""));
          const choices = data.pages.filter(p => p.course === course.value);
          // Put the course homepage first, then preserve the catalog's stable order.
          choices.sort((a, b) => Number(b.path === course.value + "/index.md") - Number(a.path === course.value + "/index.md"));
          choices.forEach(p => page.add(new Option(
            p.path === course.value + "/index.md" ? "课程主页 / 新增资料入口" : p.title, p.path)));
          page.disabled = !choices.length;
          if (choices.some(p => p.path === value)) page.value = value;
          pageSearch.refresh();
          update();
        }
        course.addEventListener("change", () => populate());
        page.addEventListener("change", update);
        kind.addEventListener("change", update);
        launch.addEventListener("click", event => {
          if (!launch.hasAttribute("href")) {
            event.preventDefault();
            status.textContent = "请先从列表选定投稿类型、课程和页面。";
            (!(kind.value in kinds) ? kindSearch : !course.value ? courseSearch : pageSearch).focus();
            return;
          }
          state.textContent = "已打开 GitHub，请在那里填写并提交。本页无法确认是否提交成功。";
        });
        remove.addEventListener("click", () => {
          card.remove();
          renumber();
          add.focus();
          status.textContent = "已移除这一页的选择。";
        });
        list.append(card);
        if (initial?.page) course.value = initial.page.course;
        courseSearch.refresh();
        populate(initial?.page?.path);
        renumber();
      }
      addCard({kind: params.get("kind"), page: selected});
      loading.hidden = true;
      add.hidden = false;
      add.addEventListener("click", () => {
        addCard({kind: params.get("kind")});
        status.textContent = "已添加一页，请选择课程和页面。";
      });
      if (params.has("page") && !selected) {
        status.textContent = "原链接的页面已不在当前列表中，请重新选择；仍找不到时交由维护者定位。";
      }
    } catch {
      loading.textContent = "暂时无法读取页面列表。请刷新重试，或使用下方的 GitHub 表单。";
    }
  }
  if (typeof document$ !== "undefined") document$.subscribe(mount);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
