/**
 * Vibedia API client — talks only to our FastAPI /wiki proxies.
 */
(function (global) {
  "use strict";

  const BASE = "/wiki";

  async function request(path) {
    const response = await fetch(`${BASE}${path}`);
    let data = null;
    try {
      data = await response.json();
    } catch (_) {
      data = null;
    }
    if (!response.ok) {
      const detail =
        (data && (data.detail || data.error || data.message)) ||
        `Request failed (${response.status})`;
      const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      err.status = response.status;
      throw err;
    }
    return data;
  }

  const VibediaAPI = {
    /** Single call for the magazine home — all sections. */
    getHome() {
      return request("/home");
    },

    search(q) {
      return request(`/search?q=${encodeURIComponent(q)}`);
    },

    getTopic(topic, continueToken) {
      let path = `/topic/${encodeURIComponent(topic)}`;
      if (continueToken) {
        path += `?continue=${encodeURIComponent(continueToken)}`;
      }
      return request(path);
    },

    getArticle(title) {
      return request(`/article/${encodeURIComponent(title)}`);
    },

    getCategories() {
      return request("/categories");
    },
  };

  global.VibediaAPI = VibediaAPI;
})(window);
