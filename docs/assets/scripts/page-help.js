(() => {
  const script = document.currentScript;
  const siteRoot = new URL('../../', script.src);
  const guideUrl = new URL('guide/#quick-start', siteRoot).href;
  const seenKey = `bms-page-help-seen:${siteRoot.pathname}`;
  const modeKey = `bms-page-help-open:${siteRoot.pathname}`;
  const read = (storage, key) => {
    try { return window[storage].getItem(key); } catch { return null; }
  };
  const write = (storage, key, value) => {
    try { window[storage].setItem(key, value); } catch { /* Optional preference only. */ }
  };
  let active = read('sessionStorage', modeKey) === 'true';
  let seen = read('localStorage', seenKey) === 'true';
  let hints = [];
  let nextFrame = 0;
  let serial = 0;

  const dismissInvite = () => {
    seen = true;
    write('localStorage', seenKey, 'true');
    document.querySelectorAll('.bms-help-invite').forEach(node => node.remove());
  };

  const clearHints = () => {
    hints.forEach(({target, note}) => {
      const ids = (target.getAttribute('aria-describedby') || '').split(/\s+/).filter(id => id && id !== note.id);
      if (ids.length) target.setAttribute('aria-describedby', ids.join(' '));
      else target.removeAttribute('aria-describedby');
      target.classList.remove('bms-help-target');
      note.remove();
    });
    hints = [];
    document.querySelectorAll('.bms-help-toolbar').forEach(node => node.remove());
  };

  const addHint = (target, text, position = 'after', anchor = target) => {
    if (!target || !anchor) return;
    const note = document.createElement('p');
    note.className = 'bms-context-hint';
    note.id = `bms-help-note-${++serial}`;
    note.textContent = text;
    anchor[position === 'before' ? 'before' : 'after'](note);
    const ids = (target.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
    target.setAttribute('aria-describedby', [...ids, note.id].join(' '));
    target.classList.add('bms-help-target');
    hints.push({target, note});
  };

  const setMode = value => {
    active = value;
    write('sessionStorage', modeKey, String(active));
    if (active) dismissInvite();
    render();
  };

  const render = () => {
    clearHints();
    const control = document.querySelector('[data-page-help]');
    const article = document.querySelector('article.md-content__inner');
    if (!control || !article) return;
    control.setAttribute('aria-pressed', String(active));
    control.setAttribute('aria-label', active ? '关闭页面帮助' : '打开页面帮助');
    control.title = active ? '收起本页操作提示' : '看看这页怎么用';
    document.documentElement.classList.toggle('bms-help-open', active);
    if (!active) return;

    const toolbar = document.createElement('div');
    toolbar.className = 'bms-help-toolbar';
    const status = document.createElement('span');
    status.textContent = '本页操作提示已展开';
    const guide = document.createElement('a');
    guide.href = guideUrl;
    guide.textContent = '完整使用说明';
    const close = document.createElement('button');
    close.type = 'button';
    close.textContent = '收起';
    close.setAttribute('aria-label', '收起本页操作提示');
    close.addEventListener('click', () => { control.focus(); setMode(false); });
    toolbar.append(status, guide, close);
    article.prepend(toolbar);

    const path = location.pathname.slice(siteRoot.pathname.length).replace(/index\.html$/, '');
    const courseSearch = article.querySelector('[data-course-search-input]');
    if (courseSearch) {
      addHint(courseSearch, '输入课程名、课程号或英文名，筛选下面的课程。想找题目或术语，可以使用页面顶部的搜索。', 'after', courseSearch.closest('.course-catalog-search-row'));
    } else if (!path) {
      addHint(article.querySelector('.course-links'), '从「课程资料」开始找课；也可以在页面顶部搜索题目或术语。', 'before');
    } else if (/^courses\/[^/]+\/$/.test(path)) {
      addHint(article.querySelector('.course-links'), '从这里进入本课程已收录的资料；使用前请核对页面标注的学年。', 'before');
    }

    const exportTools = article.querySelector('.resource-page-tools');
    if (exportTools) {
      addHint(exportTools.querySelector('a.resource-export-link'), '点「打印 / 保存 PDF」，在新标签页选择资料、调整答案位置并核对预览。', 'after', exportTools);
      const tabs = article.querySelector('.tabbed-set > .tabbed-labels');
      addHint(tabs, '切换标签查看对应材料；打印前再核对所选范围。', 'before');
      const answer = [...article.querySelectorAll('details')].find(node => {
        const label = node.querySelector(':scope > summary')?.textContent.trim();
        // Match the answer formats already recognized by resource-export-view.js.
        const isAnswer = node.classList.contains('quiz-answer') || ['参考答案', '答案要点', '给分标准'].includes(label);
        return isAnswer && node.getClientRects().length;
      });
      addHint(answer?.querySelector(':scope > summary'), '点击答案标题可展开或收起；展开后仍可继续阅读题目。', 'before', answer);
    }

    const batchTools = article.querySelector('.resource-index-print');
    if (batchTools && article.querySelector('.resource-export-index')) {
      addHint(batchTools, '点标题或「查看资料」阅读；「合并打印」打开全部站内资料，「勾选打印」可先选一份或多份。打印前请在预览中核对范围。');
    }

    const search = document.querySelector('[data-md-component="search-query"]');
    addHint(search, '搜索全站的页面、题目或术语。图片和附件中的文字可能搜不到。', 'before', document.querySelector('[data-md-component="search-result"]'));
    if (hints.length === 0) {
      addHint(article.querySelector('h1'), '可以在页面顶部搜索题目或术语；点击站名回到首页。详细操作可查看完整使用说明。');
    }
  };

  const mount = () => {
    let control = document.querySelector('[data-page-help]');
    const article = document.querySelector('article.md-content__inner');
    if (!control || !article) return;
    // A real button avoids Material's delegated link navigation. Without JS the
    // original anchor remains a working link to the complete guide.
    if (control.tagName === 'A') {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = control.className;
      button.dataset.pageHelp = '';
      button.textContent = control.textContent;
      control.replaceWith(button);
      control = button;
    }
    if (!control.dataset.pageHelpReady) {
      control.dataset.pageHelpReady = 'true';
      control.addEventListener('click', () => setMode(!active));
    }
    if (!seen && !active && !article.querySelector('.bms-help-invite')) {
      const invite = document.createElement('div');
      invite.className = 'bms-help-invite';
      const text = document.createElement('span');
      text.textContent = '第一次来？点「帮助」看看这页怎么用。';
      const close = document.createElement('button');
      close.type = 'button';
      close.textContent = '×';
      close.setAttribute('aria-label', '不再显示首次帮助提示');
      close.addEventListener('click', () => { control.focus(); dismissInvite(); });
      invite.append(text, close);
      article.querySelector('h1')?.after(invite);
    }
    // Resource tools subscribe before this script; reconcile after their insertion.
    queueMicrotask(render);
  };

  document.addEventListener('change', event => {
    if (!active || !event.target.matches('.tabbed-set > input')) return;
    cancelAnimationFrame(nextFrame);
    nextFrame = requestAnimationFrame(render);
  });
  window.addEventListener('storage', event => {
    if (event.key === seenKey && event.newValue === 'true') {
      seen = true;
      document.querySelectorAll('.bms-help-invite').forEach(node => node.remove());
    }
  });
  if (typeof document$ !== 'undefined') document$.subscribe(mount);
  else if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once:true});
  else mount();
})();
