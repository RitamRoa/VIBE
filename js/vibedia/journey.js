/**
 * Journey Mode — calm fullscreen editorial reading.
 * Intro → path selection → swipeable article slides.
 */
(function (global) {
  "use strict";

  const DEFAULT_TOPICS = [
    { id: "finance", label: "Finance" },
    { id: "technology", label: "Technology" },
    { id: "business", label: "Business" },
    { id: "science", label: "Science" },
    { id: "history", label: "History" },
    { id: "space", label: "Space" },
  ];

  let overlay = null;
  let queue = null;
  let topics = DEFAULT_TOPICS.slice();
  let selected = new Set();
  let surpriseOn = true;
  let touchStartY = 0;
  let touchEndY = 0;
  let locked = false;

  function esc(s) {
    return (global.VibediaUI && VibediaUI.escapeHtml)
      ? VibediaUI.escapeHtml(s)
      : String(s == null ? "" : s)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;");
  }

  function ensureOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement("div");
    overlay.id = "journey-overlay";
    overlay.className = "journey-overlay";
    overlay.setAttribute("aria-hidden", "true");
    document.body.appendChild(overlay);

    overlay.addEventListener(
      "touchstart",
      (e) => {
        if (!overlay.classList.contains("is-reading")) return;
        touchStartY = e.changedTouches[0].screenY;
      },
      { passive: true }
    );
    overlay.addEventListener(
      "touchend",
      (e) => {
        if (!overlay.classList.contains("is-reading")) return;
        touchEndY = e.changedTouches[0].screenY;
        handleSwipe();
      },
      { passive: true }
    );
    overlay.addEventListener(
      "wheel",
      (e) => {
        if (!overlay.classList.contains("is-reading") || locked) return;
        locked = true;
        setTimeout(() => (locked = false), 650);
        if (e.deltaY > 30) goNext();
        else if (e.deltaY < -30) goPrev();
      },
      { passive: true }
    );
    return overlay;
  }

  function handleSwipe() {
    if (locked) return;
    const dy = touchStartY - touchEndY;
    if (Math.abs(dy) < 48) return;
    locked = true;
    setTimeout(() => (locked = false), 650);
    if (dy > 0) goNext();
    else goPrev();
  }

  async function loadTopics() {
    try {
      const res = await fetch("/wiki/journey/topics");
      if (!res.ok) return;
      const data = await res.json();
      if (data.topics && data.topics.length) {
        topics = data.topics;
      }
    } catch (_) {
      /* keep defaults */
    }
  }

  function renderIntro() {
    const root = ensureOverlay();
    root.classList.remove("is-reading");
    root.classList.add("is-open");
    root.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";

    const topicButtons = topics
      .map((t) => {
        const on = !surpriseOn && selected.has(t.id);
        return `<button type="button" class="journey-topic-btn ${on ? "is-selected" : ""}" data-topic="${esc(t.id)}">${esc(t.label)}</button>`;
      })
      .join("");

    root.innerHTML = `
      <div class="journey-intro">
        <button type="button" class="journey-close" aria-label="Close">✕</button>
        <div class="journey-intro-body">
          <p class="journey-kicker">Journey</p>
          <h2 class="journey-headline">Choose today's path.</h2>

          <button type="button" class="journey-surprise ${surpriseOn ? "is-active" : ""}" id="journey-surprise">
            ✨ Surprise Me
          </button>

          <p class="journey-or">or choose a topic</p>

          <div class="journey-topics" id="journey-topics">
            ${topicButtons}
          </div>

          <button type="button" class="journey-begin" id="journey-begin">Begin →</button>
        </div>
      </div>`;

    root.querySelector(".journey-close").onclick = closeJourney;
    root.querySelector("#journey-surprise").onclick = () => {
      surpriseOn = true;
      selected.clear();
      renderIntro();
    };
    root.querySelectorAll(".journey-topic-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-topic");
        surpriseOn = false;
        if (selected.has(id)) selected.delete(id);
        else selected.add(id);
        if (selected.size === 0) surpriseOn = true;
        renderIntro();
      });
    });
    root.querySelector("#journey-begin").onclick = startJourney;
  }

  function renderLoading(message) {
    const root = ensureOverlay();
    root.classList.add("is-open");
    root.innerHTML = `
      <div class="journey-intro">
        <button type="button" class="journey-close" aria-label="Close">✕</button>
        <div class="journey-intro-body">
          <p class="journey-kicker">Journey</p>
          <p class="journey-status">${esc(message || "Preparing your path…")}</p>
        </div>
      </div>`;
    root.querySelector(".journey-close").onclick = closeJourney;
  }

  function renderError(message, retryFn) {
    const root = ensureOverlay();
    root.classList.remove("is-reading");
    root.innerHTML = `
      <div class="journey-intro">
        <button type="button" class="journey-close" aria-label="Close">✕</button>
        <div class="journey-intro-body">
          <p class="journey-kicker">Journey</p>
          <h2 class="journey-headline">Path unavailable.</h2>
          <p class="journey-status">${esc(message || "Please try again.")}</p>
          <button type="button" class="journey-begin" id="journey-retry">Try again →</button>
        </div>
      </div>`;
    root.querySelector(".journey-close").onclick = closeJourney;
    root.querySelector("#journey-retry").onclick = () => {
      if (typeof retryFn === "function") retryFn();
      else renderIntro();
    };
  }

  function articleToVisualPayload(article) {
    return {
      title: article.title,
      thumbnail: article.image,
      image: {
        image_type: article.image_type || (article.image ? "thumbnail" : "editorial"),
        image_url: article.image || null,
        title: article.title,
        category: article.category || "Knowledge",
      },
    };
  }

  function renderSlide(article, direction) {
    const root = ensureOverlay();
    root.classList.add("is-open", "is-reading");

    const slide = document.createElement("div");
    slide.className = `journey-slide ${direction || "journey-slide--in"}`;

    const visualWrap = document.createElement("div");
    visualWrap.className = "journey-visual";
    if (global.VibediaUI && VibediaUI.ArticleVisual) {
      visualWrap.appendChild(
        VibediaUI.ArticleVisual(articleToVisualPayload(article), { hero: true })
      );
    } else {
      visualWrap.innerHTML = article.image
        ? `<div class="vibedia-article-hero"><img src="${esc(article.image)}" alt=""></div>`
        : `<div class="editorial-cover editorial-cover--hero"><div class="editorial-cover-inner"><div class="editorial-cover-title">${esc(article.title)}</div><div class="editorial-cover-rule"></div><div class="editorial-cover-category">${esc(article.category)}</div></div></div>`;
    }

    const meta = document.createElement("div");
    meta.className = "journey-meta";
    meta.innerHTML = `
      <div class="journey-category">${esc(article.category || "")}</div>
      <h2 class="journey-title">${esc(article.title)}</h2>
      <p class="journey-summary">${esc(article.summary || "")}</p>
      <a class="journey-wiki" href="${esc(article.wikipedia_url)}" target="_blank" rel="noopener noreferrer">Wikipedia ↗</a>
      <div class="journey-hint">Swipe for next</div>`;

    slide.appendChild(visualWrap);
    slide.appendChild(meta);

    root.innerHTML = `
      <button type="button" class="journey-close journey-close--light" aria-label="Close">✕</button>`;
    root.appendChild(slide);
    root.querySelector(".journey-close").onclick = closeJourney;

    requestAnimationFrame(() => {
      slide.classList.add("is-visible");
    });
  }

  async function startJourney() {
    const mode = surpriseOn || selected.size === 0 ? "surprise" : "topics";
    const topicList = mode === "topics" ? Array.from(selected) : [];

    renderLoading("Preparing your path…");

    if (queue) queue.reset();
    queue = new JourneyQueueManager({
      mode,
      topics: topicList,
      limit: 20,
    });

    try {
      const first = await queue.start();
      renderSlide(first, "journey-slide--in");
      queue.prefetchIfNeeded();
    } catch (err) {
      renderError(err.message || "Journey unavailable.", startJourney);
    }
  }

  async function goNext() {
    if (!queue || locked) return;
    try {
      const article = await queue.next();
      if (!article) {
        renderError("End of this path. Choose another.", renderIntro);
        return;
      }
      renderSlide(article, "journey-slide--up");
    } catch (err) {
      renderError(err.message || "Could not continue.", () => goNext());
    }
  }

  function goPrev() {
    if (!queue) return;
    const article = queue.prev();
    if (article) renderSlide(article, "journey-slide--down");
  }

  function closeJourney() {
    if (overlay) {
      overlay.classList.remove("is-open", "is-reading");
      overlay.setAttribute("aria-hidden", "true");
      overlay.innerHTML = "";
    }
    if (queue) {
      queue.reset();
      queue = null;
    }
    document.body.style.overflow = "";
    surpriseOn = true;
    selected.clear();
  }

  async function openJourney() {
    await loadTopics();
    surpriseOn = true;
    selected.clear();
    renderIntro();
  }

  global.JourneyMode = {
    open: openJourney,
    close: closeJourney,
  };

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-open-journey]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        openJourney();
      });
    });

    const params = new URLSearchParams(window.location.search);
    if (params.get("journey") === "1" || params.get("journey") === "open") {
      openJourney();
      if (window.history && window.history.replaceState) {
        const url = new URL(window.location.href);
        url.searchParams.delete("journey");
        window.history.replaceState({}, "", url.pathname + url.search + url.hash);
      }
    }
  });
})(window);
