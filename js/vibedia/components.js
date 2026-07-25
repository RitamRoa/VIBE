/**
 * Reusable Vibedia UI components (vanilla DOM factories).
 * Matches existing VIBE news-card language — no Wikipedia chrome.
 */
(function (global) {
  "use strict";

  const BOOKMARK_KEY = "vibedia_bookmarks";

  function escapeHtml(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function getBookmarks() {
    try {
      return JSON.parse(localStorage.getItem(BOOKMARK_KEY) || "[]");
    } catch (_) {
      return [];
    }
  }

  function isBookmarked(title) {
    return getBookmarks().includes(title);
  }

  function toggleBookmark(title) {
    const list = getBookmarks();
    const idx = list.indexOf(title);
    if (idx >= 0) list.splice(idx, 1);
    else list.push(title);
    localStorage.setItem(BOOKMARK_KEY, JSON.stringify(list));
    return list.includes(title);
  }

  /** Lazy image with IntersectionObserver fallback. */
  function lazyImage(src, alt) {
    if (!src) {
      return `<div class="card-image card-image--empty" aria-hidden="true"></div>`;
    }
    return `
      <div class="card-image">
        <img src="${escapeHtml(src)}" alt="${escapeHtml(alt || "")}" loading="lazy" decoding="async">
      </div>`;
  }

  /**
   * ArticleCard — thumbnail, title, one-line summary.
   * @param {object} article
   * @param {number} [index]
   * @returns {HTMLElement}
   */
  function ArticleCard(article, index) {
    const el = document.createElement("article");
    el.className = "news-card vibedia-card";
    if (typeof index === "number") {
      el.style.animationDelay = `${Math.min(index, 12) * 0.04}s`;
    }
    const href = `/vibedia/article/${encodeURIComponent(article.title)}`;
    const summary = article.summary || "No summary available.";
    el.innerHTML = `
      <a href="${href}" data-vibedia-link>
        ${lazyImage(article.thumbnail, article.title)}
        <div class="card-content">
          <h2>${escapeHtml(article.title)}</h2>
          <p>${escapeHtml(summary)}</p>
        </div>
      </a>`;
    return el;
  }

  /**
   * ArticleGrid — responsive 2-col mobile / 5-col desktop.
   * @param {object[]} articles
   * @param {HTMLElement} [container]
   * @returns {HTMLElement}
   */
  function ArticleGrid(articles, container) {
    const grid = container || document.createElement("div");
    grid.className = "vibedia-grid";
    grid.innerHTML = "";
    if (!articles || articles.length === 0) {
      grid.innerHTML = `<div class="padding-box">Nothing here yet. Silence is golden.</div>`;
      return grid;
    }
    articles.forEach((article, i) => {
      grid.appendChild(ArticleCard(article, i));
    });
    return grid;
  }

  /**
   * CategorySection — label, grid of 10, See More link.
   * @param {{id:string,label:string}} category
   * @param {object[]} articles
   * @returns {HTMLElement}
   */
  function CategorySection(category, articles) {
    const section = document.createElement("section");
    section.className = "vibedia-section";
    section.dataset.topic = category.id;

    const header = document.createElement("div");
    header.className = "vibedia-section-header";
    header.innerHTML = `<h2 class="vibedia-section-title">${escapeHtml(category.label)}</h2>`;
    section.appendChild(header);

    section.appendChild(ArticleGrid(articles || []));

    const footer = document.createElement("div");
    footer.className = "vibedia-section-footer";
    footer.innerHTML = `
      <a class="vibedia-see-more" href="/vibedia/${encodeURIComponent(category.id)}" data-vibedia-link>
        See More →
      </a>`;
    section.appendChild(footer);
    return section;
  }

  /**
   * SearchBar — controlled search input.
   * @param {{placeholder?:string, value?:string, onSubmit:(q:string)=>void}} opts
   * @returns {HTMLElement}
   */
  function SearchBar(opts) {
    const options = opts || {};
    const wrap = document.createElement("form");
    wrap.className = "vibedia-search";
    wrap.setAttribute("role", "search");
    wrap.innerHTML = `
      <input
        type="search"
        name="q"
        class="vibedia-search-input"
        placeholder="${escapeHtml(options.placeholder || "Search Wikipedia...")}"
        value="${escapeHtml(options.value || "")}"
        autocomplete="off"
        enterkeyhint="search"
      >
      <button type="submit" class="vibedia-search-btn" aria-label="Search">Search</button>`;

    wrap.addEventListener("submit", (e) => {
      e.preventDefault();
      const q = wrap.querySelector("input").value.trim();
      if (typeof options.onSubmit === "function") options.onSubmit(q);
    });
    return wrap;
  }

  /**
   * Skeleton loaders for home / grids — reserve space, no layout shift.
   */
  function SkeletonGrid(count) {
    const n = count || 10;
    const grid = document.createElement("div");
    grid.className = "vibedia-grid vibedia-skeleton-grid";
    grid.setAttribute("aria-hidden", "true");
    for (let i = 0; i < n; i++) {
      const card = document.createElement("div");
      card.className = "vibedia-skeleton-card";
      card.innerHTML = `
        <div class="vibedia-skeleton-img"></div>
        <div class="vibedia-skeleton-lines">
          <div class="vibedia-skeleton-line"></div>
          <div class="vibedia-skeleton-line short"></div>
        </div>`;
      grid.appendChild(card);
    }
    return grid;
  }

  function SkeletonHome(categories) {
    const frag = document.createDocumentFragment();
    (categories || []).forEach((cat) => {
      const section = document.createElement("section");
      section.className = "vibedia-section";
      section.innerHTML = `<div class="vibedia-section-header"><h2 class="vibedia-section-title">${escapeHtml(cat.label)}</h2></div>`;
      section.appendChild(SkeletonGrid(10));
      frag.appendChild(section);
    });
    return frag;
  }

  /**
   * ArticlePage — large image, title, summary, wiki link, related, bookmark.
   * @param {object} article
   * @returns {HTMLElement}
   */
  function ArticlePage(article) {
    const root = document.createElement("article");
    root.className = "vibedia-article";

    const bookmarked = isBookmarked(article.title);
    const img = article.thumbnail
      ? `<div class="vibedia-article-hero"><img src="${escapeHtml(article.thumbnail)}" alt="${escapeHtml(article.title)}" loading="eager"></div>`
      : `<div class="vibedia-article-hero vibedia-article-hero--empty"></div>`;

    const desc = article.description
      ? `<p class="vibedia-article-desc">${escapeHtml(article.description)}</p>`
      : "";

    root.innerHTML = `
      ${img}
      <div class="vibedia-article-body">
        <div class="vibedia-article-actions">
          <button type="button" class="vibedia-bookmark-btn ${bookmarked ? "is-active" : ""}" aria-pressed="${bookmarked}">
            ${bookmarked ? "★ Bookmarked" : "☆ Bookmark"}
          </button>
          <a class="vibedia-wiki-link" href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer">
            View on Wikipedia ↗
          </a>
        </div>
        <h1 class="vibedia-article-title">${escapeHtml(article.title)}</h1>
        ${desc}
        <div class="vibedia-article-extract">${escapeHtml(article.extract || article.summary || "No summary available.")}</div>
      </div>`;

    const btn = root.querySelector(".vibedia-bookmark-btn");
    btn.addEventListener("click", () => {
      const on = toggleBookmark(article.title);
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-pressed", String(on));
      btn.textContent = on ? "★ Bookmarked" : "☆ Bookmark";
    });

    if (article.related && article.related.length) {
      const related = document.createElement("section");
      related.className = "vibedia-section vibedia-related";
      related.innerHTML = `<div class="vibedia-section-header"><h2 class="vibedia-section-title">Related</h2></div>`;
      related.appendChild(ArticleGrid(article.related));
      root.appendChild(related);
    }

    return root;
  }

  function ErrorState(message) {
    const el = document.createElement("div");
    el.className = "error vibedia-error";
    el.textContent = message || "Something went wrong.";
    return el;
  }

  function EmptyState(message) {
    const el = document.createElement("div");
    el.className = "padding-box";
    el.textContent = message || "No results.";
    return el;
  }

  global.VibediaUI = {
    escapeHtml,
    ArticleCard,
    ArticleGrid,
    CategorySection,
    SearchBar,
    SkeletonGrid,
    SkeletonHome,
    ArticlePage,
    ErrorState,
    EmptyState,
    isBookmarked,
    toggleBookmark,
  };
})(window);
