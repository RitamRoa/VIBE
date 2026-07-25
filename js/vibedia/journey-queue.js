/**
 * JourneyQueueManager — session-only article queue with prefetch.
 * No persistence. Closing Journey clears everything.
 */
(function (global) {
  "use strict";

  const PREFETCH_AT = 5;
  const BATCH_SIZE = 20;

  function JourneyQueueManager(options) {
    const opts = options || {};
    this.mode = opts.mode || "surprise";
    this.topics = opts.topics || [];
    this.limit = opts.limit || BATCH_SIZE;
    this.queue = [];
    this.index = 0;
    this.seen = new Set();
    this.cursor = null;
    this.loading = false;
    this.exhausted = false;
    this._prefetchPromise = null;
  }

  JourneyQueueManager.prototype._buildUrl = function (cursor) {
    const params = new URLSearchParams();
    params.set("mode", this.mode);
    params.set("limit", String(this.limit));
    if (this.mode === "topics" && this.topics.length) {
      params.set("topics", this.topics.join(","));
    }
    if (cursor) params.set("cursor", cursor);
    if (this.seen.size) {
      params.set("exclude", Array.from(this.seen).slice(-120).join(","));
    }
    return `/wiki/journey?${params.toString()}`;
  };

  JourneyQueueManager.prototype._appendBatch = function (articles, nextCursor) {
    let added = 0;
    (articles || []).forEach((article) => {
      if (!article || !article.id) return;
      if (this.seen.has(article.id)) return;
      this.seen.add(article.id);
      this.queue.push(article);
      added += 1;
    });
    this.cursor = nextCursor || null;
    if (!nextCursor || added === 0) {
      if (!nextCursor) this.exhausted = true;
    }
    return added;
  };

  /** Load the first batch. */
  JourneyQueueManager.prototype.start = async function () {
    this.queue = [];
    this.index = 0;
    this.seen = new Set();
    this.cursor = null;
    this.exhausted = false;
    this.loading = true;
    try {
      const res = await fetch(this._buildUrl(null));
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Journey unavailable (${res.status})`);
      }
      const data = await res.json();
      this._appendBatch(data.articles, data.next_cursor);
      if (!this.queue.length) {
        throw new Error("No articles for this path. Try another topic.");
      }
      return this.current();
    } finally {
      this.loading = false;
    }
  };

  /** Prefetch next batch when remaining ≤ PREFETCH_AT. */
  JourneyQueueManager.prototype.prefetchIfNeeded = function () {
    const remaining = this.queue.length - this.index - 1;
    if (remaining > PREFETCH_AT) return;
    if (this.exhausted || this.loading || this._prefetchPromise) return;
    if (!this.cursor) return;

    this.loading = true;
    this._prefetchPromise = fetch(this._buildUrl(this.cursor))
      .then((res) => {
        if (!res.ok) throw new Error("Could not load more articles.");
        return res.json();
      })
      .then((data) => {
        this._appendBatch(data.articles, data.next_cursor);
      })
      .catch((err) => {
        console.warn("Journey prefetch failed:", err);
      })
      .finally(() => {
        this.loading = false;
        this._prefetchPromise = null;
      });
  };

  JourneyQueueManager.prototype.current = function () {
    return this.queue[this.index] || null;
  };

  JourneyQueueManager.prototype.hasNext = function () {
    return this.index < this.queue.length - 1 || Boolean(this.cursor);
  };

  JourneyQueueManager.prototype.hasPrev = function () {
    return this.index > 0;
  };

  JourneyQueueManager.prototype.next = async function () {
    if (this.index < this.queue.length - 1) {
      this.index += 1;
      this.prefetchIfNeeded();
      return this.current();
    }
    // Need more articles
    if (this.cursor && !this.loading) {
      this.loading = true;
      try {
        const res = await fetch(this._buildUrl(this.cursor));
        if (!res.ok) throw new Error("Could not load more articles.");
        const data = await res.json();
        const added = this._appendBatch(data.articles, data.next_cursor);
        if (added === 0) return null;
        this.index += 1;
        return this.current();
      } finally {
        this.loading = false;
      }
    }
    if (this._prefetchPromise) {
      await this._prefetchPromise;
      if (this.index < this.queue.length - 1) {
        this.index += 1;
        return this.current();
      }
    }
    return null;
  };

  JourneyQueueManager.prototype.prev = function () {
    if (this.index <= 0) return this.current();
    this.index -= 1;
    return this.current();
  };

  JourneyQueueManager.prototype.reset = function () {
    this.queue = [];
    this.index = 0;
    this.seen = new Set();
    this.cursor = null;
    this.loading = false;
    this.exhausted = false;
    this._prefetchPromise = null;
  };

  global.JourneyQueueManager = JourneyQueueManager;
})(window);
