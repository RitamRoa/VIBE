/**
 * Journey Mode — calm fullscreen editorial reading.
 * Finite issue (~20) with a satisfying completion screen.
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
  let locked = false;
  /** @type {{mode:string, topics:string[], sourceTopics:string[], seen:string[]}|null} */
  let lastSession = null;

  function esc(s) {
    return global.VibediaUI && VibediaUI.escapeHtml
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

    // Keyboard arrows still work as a quiet desktop shortcut
    document.addEventListener("keydown", (e) => {
      if (!overlay || !overlay.classList.contains("is-reading") || locked) return;
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goNext();
      }
    });

    return overlay;
  }

  async function loadTopics() {
    try {
      const res = await fetch("/wiki/journey/topics");
      if (!res.ok) return;
      const data = await res.json();
      if (data.topics && data.topics.length) topics = data.topics;
    } catch (_) {
      /* keep defaults */
    }
  }

  function renderIntro() {
    const root = ensureOverlay();
    root.classList.remove("is-reading", "is-complete");
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
    root.querySelector("#journey-begin").onclick = () => {
      const mode = surpriseOn || selected.size === 0 ? "surprise" : "topics";
      const topicList = mode === "topics" ? Array.from(selected) : [];
      launchJourney({ mode, topics: topicList, sourceTopics: topicList });
    };
  }

  function renderLoading(message) {
    const root = ensureOverlay();
    root.classList.remove("is-reading", "is-complete");
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
    root.classList.remove("is-reading", "is-complete");
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

  function renderComplete() {
    const root = ensureOverlay();
    root.classList.remove("is-reading");
    root.classList.add("is-open", "is-complete");

    const title = (queue && queue.title) || "Journey";

    root.innerHTML = `
      <div class="journey-intro journey-complete">
        <button type="button" class="journey-close" aria-label="Close">✕</button>
        <div class="journey-intro-body">
          <p class="journey-kicker">${esc(title)}</p>
          <div class="journey-progress" aria-hidden="true">██████████</div>
          <h2 class="journey-headline">You've reached the end of this journey.</h2>

          <div class="journey-complete-actions">
            <button type="button" class="journey-begin" id="journey-again">Begin Again</button>
            <button type="button" class="journey-action-secondary" id="journey-explore">Continue Exploring</button>
            <button type="button" class="journey-surprise" id="journey-surprise-end">✨ Surprise Me</button>
            <button type="button" class="journey-action-ghost" id="journey-close-end">Close Journey</button>
          </div>
        </div>
      </div>`;

    root.querySelector(".journey-close").onclick = closeJourney;
    root.querySelector("#journey-close-end").onclick = closeJourney;

    root.querySelector("#journey-again").onclick = () => {
      const sess = lastSession || { mode: "surprise", topics: [], sourceTopics: [] };
      const mode = sess.mode === "explore" ? "topics" : sess.mode;
      const topicsForAgain =
        mode === "surprise"
          ? []
          : sess.sourceTopics && sess.sourceTopics.length
            ? sess.sourceTopics
            : sess.topics;
      launchJourney({
        mode: mode === "surprise" ? "surprise" : "topics",
        topics: topicsForAgain,
        sourceTopics: topicsForAgain,
        exclude: sess.seen || [],
        variation: String(Date.now()),
      });
    };

    root.querySelector("#journey-explore").onclick = () => {
      const sess = lastSession || { topics: [], sourceTopics: [] };
      const sources =
        sess.sourceTopics && sess.sourceTopics.length
          ? sess.sourceTopics
          : sess.topics && sess.topics.length
            ? sess.topics
            : ["finance"];
      launchJourney({
        mode: "explore",
        topics: sources,
        sourceTopics: sources,
        exclude: sess.seen || [],
        variation: String(Date.now()),
      });
    };

    root.querySelector("#journey-surprise-end").onclick = () => {
      launchJourney({
        mode: "surprise",
        topics: [],
        sourceTopics: [],
        exclude: (lastSession && lastSession.seen) || [],
        variation: String(Date.now()),
      });
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
    root.classList.remove("is-complete");

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

    const isFirst = !queue || !queue.hasPrev();
    const isLast = queue && queue.isLast();
    const pos = queue ? queue.position() : 1;
    const total = queue ? queue.size() : 1;
    const nextLabel = isLast ? "Finish" : "Next";

    const meta = document.createElement("div");
    meta.className = "journey-meta";
    meta.innerHTML = `
      <div class="journey-category">${esc(article.category || "")}</div>
      <h2 class="journey-title">${esc(article.title)}</h2>
      <p class="journey-summary">${esc(article.summary || "")}</p>
      <a class="journey-wiki" href="${esc(article.wikipedia_url)}" target="_blank" rel="noopener noreferrer">Wikipedia ↗</a>`;

    const pager = document.createElement("nav");
    pager.className = "journey-pager";
    pager.setAttribute("aria-label", "Journey pages");
    pager.innerHTML = `
      <button type="button" class="journey-pager-btn" id="journey-prev" ${isFirst ? "disabled" : ""}>Previous</button>
      <span class="journey-pager-count">${pos} / ${total}</span>
      <button type="button" class="journey-pager-btn journey-pager-btn--next" id="journey-next">${esc(nextLabel)}</button>`;

    slide.appendChild(visualWrap);
    slide.appendChild(meta);
    slide.appendChild(pager);

    root.innerHTML = `
      <button type="button" class="journey-close journey-close--light" aria-label="Close">✕</button>`;
    root.appendChild(slide);
    root.querySelector(".journey-close").onclick = closeJourney;
    root.querySelector("#journey-prev").onclick = () => goPrev();
    root.querySelector("#journey-next").onclick = () => goNext();

    slide.scrollTop = 0;

    requestAnimationFrame(() => {
      slide.classList.add("is-visible");
    });
  }

  async function launchJourney(opts) {
    const options = opts || {};
    const mode = options.mode || "surprise";
    const topicList = options.topics || [];
    const sourceTopics = options.sourceTopics || topicList.slice();

    renderLoading("Preparing your path…");

    if (queue) queue.reset();
    queue = new JourneyQueueManager({
      mode,
      topics: topicList,
      sourceTopics,
      limit: 20,
      variation: options.variation || String(Date.now()),
      exclude: options.exclude || [],
    });

    try {
      const first = await queue.start();
      lastSession = {
        mode,
        topics: queue.topics.slice(),
        sourceTopics: sourceTopics.slice(),
        seen: Array.from(queue.seen),
      };
      renderSlide(first, "journey-slide--in");
    } catch (err) {
      renderError(err.message || "Journey unavailable.", () => launchJourney(options));
    }
  }

  async function startJourney() {
    const mode = surpriseOn || selected.size === 0 ? "surprise" : "topics";
    const topicList = mode === "topics" ? Array.from(selected) : [];
    await launchJourney({ mode, topics: topicList, sourceTopics: topicList });
  }

  async function goNext() {
    if (!queue || locked) return;
    try {
      const result = await queue.next();
      if (result.done) {
        if (lastSession) {
          lastSession.seen = Array.from(queue.seen);
        }
        renderComplete();
        return;
      }
      if (lastSession) lastSession.seen = Array.from(queue.seen);
      renderSlide(result.article, "journey-slide--next");
    } catch (err) {
      renderError(err.message || "Could not continue.", () => goNext());
    }
  }

  function goPrev() {
    if (!queue || locked) return;
    const article = queue.prev();
    if (article) renderSlide(article, "journey-slide--prev");
  }

  function closeJourney() {
    if (overlay) {
      overlay.classList.remove("is-open", "is-reading", "is-complete");
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
