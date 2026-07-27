/**
 * Reusable Vibedia UI components (vanilla DOM factories).
 * Matches existing VIBE news-card language — no Wikipedia chrome.
 */
(function (global) {
  "use strict";

  function escapeHtml(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /**
   * Split a title into display lines for editorial covers.
   * Prefers natural word breaks; max 3 lines.
   */
  function splitTitleLines(title) {
    const words = String(title || "")
      .replace(/\s*\([^)]*\)\s*/g, " ")
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    if (words.length === 0) return ["Untitled"];
    if (words.length === 1) return [words[0].toUpperCase()];
    if (words.length === 2) {
      return [words[0].toUpperCase(), words[1].toUpperCase()];
    }

    const lines = [];
    let current = "";
    words.forEach((word) => {
      const next = current ? `${current} ${word}` : word;
      if (next.length > 14 && current) {
        lines.push(current.toUpperCase());
        current = word;
      } else {
        current = next;
      }
    });
    if (current) lines.push(current.toUpperCase());

    if (lines.length <= 3) return lines;
    return [lines[0], lines[1], lines.slice(2).join(" ")].slice(0, 3);
  }

  function coverSizeClass(title) {
    const len = String(title || "").length;
    if (len <= 16) return "editorial-cover--short";
    if (len <= 36) return "editorial-cover--medium";
    return "editorial-cover--long";
  }

  /**
   * EditorialCover — intentional magazine cover when no photo exists.
   * @param {string} title
   * @param {string} category
   * @param {{hero?: boolean}} [opts]
   * @returns {HTMLElement}
   */
  function EditorialCover(title, category, opts) {
    const options = opts || {};
    const el = document.createElement("div");
    el.className =
      "editorial-cover " +
      coverSizeClass(title) +
      (options.hero ? " editorial-cover--hero" : "");
    el.setAttribute("role", "img");
    el.setAttribute(
      "aria-label",
      `${title}${category ? ` — ${category}` : ""}`
    );

    const lines = splitTitleLines(title)
      .map((line) => `<span class="editorial-cover-line">${escapeHtml(line)}</span>`)
      .join("");

    el.innerHTML = `
      <div class="editorial-cover-inner">
        <div class="editorial-cover-title">${lines}</div>
        <div class="editorial-cover-rule" aria-hidden="true"></div>
        <div class="editorial-cover-category">${escapeHtml(category || "Knowledge")}</div>
      </div>`;
    return el;
  }

  /**
   * Resolve visual node from article.image payload.
   * Frontend never cares which Wikipedia path produced a photo URL.
   */
  function ArticleVisual(article, opts) {
    const options = opts || {};
    const image = article.image || {};
    const type = image.image_type;
    const url = image.image_url || article.thumbnail || null;
    const title = image.title || article.title || "";
    const category = image.category || "Knowledge";

    if (type === "editorial" || !url) {
      return EditorialCover(title, category, { hero: options.hero });
    }

    const wrap = document.createElement("div");
    wrap.className = options.hero
      ? "vibedia-article-hero"
      : "card-image";
    const img = document.createElement("img");
    img.src = url;
    img.alt = title;
    img.loading = options.hero ? "eager" : "lazy";
    img.decoding = "async";
    img.addEventListener("error", () => {
      const cover = EditorialCover(title, category, { hero: options.hero });
      wrap.replaceWith(cover);
    });
    wrap.appendChild(img);
    return wrap;
  }

  /**
   * ArticleCard — visual, title, one-line summary.
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

    const link = document.createElement("a");
    link.href = href;
    link.setAttribute("data-vibedia-link", "");
    link.appendChild(ArticleVisual(article));

    const content = document.createElement("div");
    content.className = "card-content";
    content.innerHTML = `
      <h2>${escapeHtml(article.title)}</h2>
      <p>${escapeHtml(summary)}</p>`;
    link.appendChild(content);
    el.appendChild(link);
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
        placeholder="${escapeHtml(options.placeholder || "Search Vibedia...")}"
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
   * ArticlePage — large visual, title, summary, wiki link, related.
   * @param {object} article
   * @returns {HTMLElement}
   */
  function ArticlePage(article) {
    const root = document.createElement("article");
    root.className = "vibedia-article";

    root.appendChild(ArticleVisual(article, { hero: true }));

    const body = document.createElement("div");
    body.className = "vibedia-article-body";

    const desc = article.description
      ? `<p class="vibedia-article-desc">${escapeHtml(article.description)}</p>`
      : "";

    body.innerHTML = `
      <div class="vibedia-article-actions">
        <a class="vibedia-wiki-link" href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer">
          View on Wikipedia ↗
        </a>
      </div>
      <h1 class="vibedia-article-title">${escapeHtml(article.title)}</h1>
      ${desc}
      <div class="vibedia-article-extract">${escapeHtml(article.extract || article.summary || "No summary available.")}</div>`;

    root.appendChild(body);

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
    EditorialCover,
    ArticleVisual,
    ArticleCard,
    ArticleGrid,
    CategorySection,
    SearchBar,
    SkeletonGrid,
    SkeletonHome,
    ArticlePage,
    ErrorState,
    EmptyState,
  };
})(window);
