/**
 * JourneyQueueManager — finite session queue (~20 articles).
 * No endless feed. No persistence.
 */
(function (global) {
  "use strict";

  const ISSUE_SIZE = 20;

  function JourneyQueueManager(options) {
    const opts = options || {};
    this.mode = opts.mode || "surprise";
    this.topics = opts.topics || [];
    this.sourceTopics = opts.sourceTopics || this.topics.slice();
    this.limit = opts.limit || ISSUE_SIZE;
    this.variation = opts.variation || String(Date.now());
    this.excludeExtra = opts.exclude || [];
    this.queue = [];
    this.index = 0;
    this.seen = new Set();
    this.title = "Journey";
    this.loading = false;
    this.complete = false;
  }

  JourneyQueueManager.prototype._buildUrl = function () {
    const params = new URLSearchParams();
    params.set("mode", this.mode);
    params.set("limit", String(this.limit));
    params.set("variation", this.variation);
    if (this.topics.length) {
      params.set("topics", this.topics.join(","));
    }
    const exclude = Array.from(
      new Set([].concat(this.excludeExtra, Array.from(this.seen)))
    ).slice(-150);
    if (exclude.length) {
      params.set("exclude", exclude.join(","));
    }
    return `/wiki/journey?${params.toString()}`;
  };

  /** Load one finite issue. */
  JourneyQueueManager.prototype.start = async function () {
    this.queue = [];
    this.index = 0;
    this.seen = new Set();
    this.complete = false;
    this.loading = true;
    try {
      const res = await fetch(this._buildUrl());
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Journey unavailable (${res.status})`);
      }
      const data = await res.json();
      this.title = data.title || "Journey";
      (data.articles || []).forEach((article) => {
        if (!article || !article.id || this.seen.has(article.id)) return;
        this.seen.add(article.id);
        this.queue.push(article);
      });
      if (!this.queue.length) {
        throw new Error("No articles for this path. Try another topic.");
      }
      return this.current();
    } finally {
      this.loading = false;
    }
  };

  JourneyQueueManager.prototype.current = function () {
    return this.queue[this.index] || null;
  };

  JourneyQueueManager.prototype.size = function () {
    return this.queue.length;
  };

  JourneyQueueManager.prototype.position = function () {
    return this.index + 1;
  };

  JourneyQueueManager.prototype.isLast = function () {
    return this.index >= this.queue.length - 1;
  };

  JourneyQueueManager.prototype.hasPrev = function () {
    return this.index > 0;
  };

  /**
   * Advance to the next article.
   * Returns { article } or { done: true } when the issue ends.
   */
  JourneyQueueManager.prototype.next = async function () {
    if (this.index < this.queue.length - 1) {
      this.index += 1;
      return { article: this.current(), done: false };
    }
    this.complete = true;
    return { article: null, done: true };
  };

  JourneyQueueManager.prototype.prev = function () {
    if (this.index <= 0) return this.current();
    this.index -= 1;
    this.complete = false;
    return this.current();
  };

  JourneyQueueManager.prototype.reset = function () {
    this.queue = [];
    this.index = 0;
    this.seen = new Set();
    this.loading = false;
    this.complete = false;
  };

  global.JourneyQueueManager = JourneyQueueManager;
})(window);
