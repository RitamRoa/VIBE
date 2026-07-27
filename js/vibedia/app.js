/**
 * Vibedia app — router + pages.
 * Routes:
 *   /vibedia
 *   /vibedia/{topic}
 *   /vibedia/article/{title}
 *   /vibedia/search?q=
 */
(function () {
  "use strict";

  /** Default category order / labels (mirrored from backend config). */
  const DEFAULT_CATEGORIES = [
    { id: "finance", label: "Finance" },
    { id: "technology", label: "Technology" },
    { id: "business", label: "Business" },
    { id: "random", label: "Random" },
  ];

  let categories = DEFAULT_CATEGORIES.slice();
  let topicObserver = null;
  let topicState = { topic: null, continueToken: null, loading: false, hasMore: true };

  const appRoot = () => document.getElementById("vibedia-app");

  function parseRoute() {
    const path = window.location.pathname.replace(/\/+$/, "") || "/";
    const params = new URLSearchParams(window.location.search);

    if (path === "/vibedia" || path === "/vibedia/") {
      const q = params.get("q");
      if (q) return { name: "search", query: q };
      return { name: "home" };
    }

    const articleMatch = path.match(/^\/vibedia\/article\/(.+)$/);
    if (articleMatch) {
      return { name: "article", title: decodeURIComponent(articleMatch[1]) };
    }

    const topicMatch = path.match(/^\/vibedia\/([^/]+)$/);
    if (topicMatch) {
      const id = decodeURIComponent(topicMatch[1]).toLowerCase();
      if (id === "search") {
        return { name: "search", query: params.get("q") || "" };
      }
      return { name: "topic", topic: id };
    }

    return { name: "home" };
  }

  function navigate(url, { replace } = {}) {
    if (replace) history.replaceState({}, "", url);
    else history.pushState({}, "", url);
    render();
  }

  function wireInternalLinks(root) {
    root.addEventListener("click", (e) => {
      const a = e.target.closest("a[data-vibedia-link]");
      if (!a) return;
      const href = a.getAttribute("href");
      if (!href || !href.startsWith("/vibedia")) return;
      e.preventDefault();
      navigate(href);
    });
  }

  function setChrome(route) {
    const back = document.getElementById("vibedia-back");
    const brandLink = document.getElementById("vibedia-brand-link");
    if (brandLink) brandLink.href = "/vibedia";

    if (!back) return;
    if (route.name === "home") {
      back.href = "/";
      back.textContent = "← News";
      back.setAttribute("data-external", "1");
    } else {
      back.href = "/vibedia";
      back.textContent = "← Vibedia";
      back.removeAttribute("data-external");
    }
  }

  /* -------------------- Pages -------------------- */

  async function renderHome(root) {
    const search = VibediaUI.SearchBar({
      onSubmit(q) {
        if (!q) return;
        navigate(`/vibedia/search?q=${encodeURIComponent(q)}`);
      },
    });
    root.appendChild(search);

    const feed = document.createElement("div");
    feed.className = "vibedia-feed";
    feed.appendChild(VibediaUI.SkeletonHome(categories));
    root.appendChild(feed);

    try {
      const data = await VibediaAPI.getHome();
      feed.innerHTML = "";
      categories.forEach((cat) => {
        const articles = data[cat.id] || [];
        feed.appendChild(VibediaUI.CategorySection(cat, articles));
      });
    } catch (err) {
      feed.innerHTML = "";
      feed.appendChild(
        VibediaUI.ErrorState(
          err.message || "Wikipedia is temporarily unavailable. Please try again."
        )
      );
    }
  }

  async function renderSearch(root, query) {
    const search = VibediaUI.SearchBar({
      value: query || "",
      onSubmit(q) {
        navigate(`/vibedia/search?q=${encodeURIComponent(q)}`);
      },
    });
    root.appendChild(search);

    const heading = document.createElement("div");
    heading.className = "vibedia-section-header";
    heading.innerHTML = `<h2 class="vibedia-section-title">Search</h2>`;
    root.appendChild(heading);

    if (!query) {
      root.appendChild(VibediaUI.EmptyState("Type a query to search Vibedia."));
      return;
    }

    const gridHost = document.createElement("div");
    gridHost.appendChild(VibediaUI.SkeletonGrid(8));
    root.appendChild(gridHost);

    try {
      const data = await VibediaAPI.search(query);
      gridHost.innerHTML = "";
      if (!data.articles || data.articles.length === 0) {
        gridHost.appendChild(
          VibediaUI.EmptyState(`No results for “${query}”. Try another term.`)
        );
        return;
      }
      VibediaUI.ArticleGrid(data.articles, gridHost);
      gridHost.classList.add("vibedia-grid");
    } catch (err) {
      gridHost.innerHTML = "";
      gridHost.appendChild(VibediaUI.ErrorState(err.message));
    }
  }

  async function renderTopic(root, topic) {
    const meta = categories.find((c) => c.id === topic) || {
      id: topic,
      label: topic.charAt(0).toUpperCase() + topic.slice(1),
    };

    const search = VibediaUI.SearchBar({
      onSubmit(q) {
        if (!q) return;
        navigate(`/vibedia/search?q=${encodeURIComponent(q)}`);
      },
    });
    root.appendChild(search);

    const header = document.createElement("div");
    header.className = "vibedia-section-header vibedia-topic-header";
    header.innerHTML = `<h2 class="vibedia-section-title">${VibediaUI.escapeHtml(meta.label)}</h2>`;
    root.appendChild(header);

    const gridEl = VibediaUI.SkeletonGrid(10);
    root.appendChild(gridEl);

    const sentinel = document.createElement("div");
    sentinel.className = "vibedia-scroll-sentinel";
    sentinel.innerHTML = `<div class="loading">Loading more…</div>`;
    sentinel.hidden = true;
    root.appendChild(sentinel);

    topicState = { topic, continueToken: null, loading: false, hasMore: true };

    async function loadMore(reset) {
      if (topicState.loading || (!topicState.hasMore && !reset)) return;
      topicState.loading = true;
      sentinel.hidden = false;

      try {
        const data = await VibediaAPI.getTopic(
          topic,
          reset ? null : topicState.continueToken
        );
        if (reset) {
          gridEl.innerHTML = "";
          gridEl.className = "vibedia-grid";
        }
        const articles = data.articles || [];
        if (reset && articles.length === 0) {
          gridEl.appendChild(VibediaUI.EmptyState("No articles in this section."));
        } else {
          articles.forEach((article, i) => {
            gridEl.appendChild(VibediaUI.ArticleCard(article, i));
          });
        }
        topicState.continueToken = data.continue_token || null;
        topicState.hasMore = Boolean(data.has_more);
        if (!topicState.hasMore) {
          sentinel.innerHTML = `<div class="padding-box">End of section.</div>`;
        }
      } catch (err) {
        if (reset) {
          gridEl.innerHTML = "";
          gridEl.appendChild(VibediaUI.ErrorState(err.message));
        }
        topicState.hasMore = false;
        sentinel.innerHTML = `<div class="error">${VibediaUI.escapeHtml(err.message)}</div>`;
      } finally {
        topicState.loading = false;
        if (!topicState.hasMore && sentinel.querySelector(".loading")) {
          sentinel.hidden = true;
        }
      }
    }

    await loadMore(true);

    if (topicObserver) topicObserver.disconnect();
    topicObserver = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) loadMore(false);
      },
      { rootMargin: "240px" }
    );
    topicObserver.observe(sentinel);
    sentinel.hidden = false;
  }

  async function renderArticle(root, title) {
    root.appendChild(VibediaUI.SkeletonGrid(1));
    const host = root;

    try {
      const article = await VibediaAPI.getArticle(title);
      host.innerHTML = "";
      host.appendChild(VibediaUI.ArticlePage(article));
      document.title = `${article.title} — Vibedia`;
    } catch (err) {
      host.innerHTML = "";
      host.appendChild(VibediaUI.ErrorState(err.message || "Article not found."));
    }
  }

  /* -------------------- Render orchestrator -------------------- */

  async function render() {
    const root = appRoot();
    if (!root) return;

    if (topicObserver) {
      topicObserver.disconnect();
      topicObserver = null;
    }

    const route = parseRoute();
    setChrome(route);
    root.innerHTML = "";
    document.title =
      route.name === "home"
        ? "Vibedia — VIBE"
        : route.name === "topic"
          ? `${route.topic} — Vibedia`
          : route.name === "search"
            ? `Search — Vibedia`
            : "Vibedia — VIBE";

    if (route.name === "home") await renderHome(root);
    else if (route.name === "search") await renderSearch(root, route.query);
    else if (route.name === "topic") await renderTopic(root, route.topic);
    else if (route.name === "article") await renderArticle(root, route.title);
    else await renderHome(root);
  }

  function toggleMenu() {
    const panel = document.getElementById("menu-panel");
    const overlay = document.getElementById("menu-overlay");
    const isOpen = panel.classList.contains("open");
    panel.classList.toggle("open", !isOpen);
    overlay.classList.toggle("open", !isOpen);
    document.body.style.overflow = isOpen ? "auto" : "hidden";
  }

  function openModal(id) {
    const modal = document.getElementById(id + "-modal");
    if (modal) {
      modal.classList.add("open");
      document.body.style.overflow = "hidden";
    }
  }

  function closeModal(id) {
    const modal = document.getElementById(id + "-modal");
    if (modal) {
      modal.classList.remove("open");
      document.body.style.overflow = "auto";
    }
  }

  // Expose menu helpers for inline handlers
  window.toggleMenu = toggleMenu;
  window.openModal = openModal;
  window.closeModal = closeModal;

  document.addEventListener("DOMContentLoaded", async () => {
    wireInternalLinks(document.body);

    const back = document.getElementById("vibedia-back");
    if (back) {
      back.addEventListener("click", (e) => {
        if (back.getAttribute("data-external") === "1") return; // allow full nav to news
        e.preventDefault();
        navigate(back.getAttribute("href") || "/vibedia");
      });
    }

    document.querySelectorAll(".menu-item").forEach((item) => {
      item.addEventListener("click", () => {
        document.getElementById("menu-panel").classList.remove("open");
        document.getElementById("menu-overlay").classList.remove("open");
        document.body.style.overflow = "auto";
      });
    });

    document.querySelectorAll(".modal").forEach((modal) => {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          closeModal(modal.id.replace("-modal", ""));
        }
      });
    });

    window.addEventListener("popstate", () => render());

    try {
      const catData = await VibediaAPI.getCategories();
      if (catData && catData.categories && catData.categories.length) {
        categories = catData.categories.map((c) => ({
          id: c.id,
          label: c.label,
        }));
      }
    } catch (_) {
      /* keep defaults */
    }

    render();
  });
})();
