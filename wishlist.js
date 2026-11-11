/* Account-free favourites, stored only in this browser. */
(() => {
  'use strict';
  const key = 'badroses.wishlist.v1';
  const parse = value => {
    const ids = JSON.parse(value || '[]');
    if (!Array.isArray(ids)) throw new Error('Invalid wishlist');
    return new Set(ids.filter(id => typeof id === 'string' && /^(item|horse)-\d+$/.test(id)));
  };
  function createStore(storage) {
    let ids = new Set();
    let persistent = true;
    try {
      storage = storage || globalThis.localStorage;
      ids = parse(storage.getItem(key));
    } catch { persistent = false; }
    return {
      has: id => ids.has(id),
      get persistent() { return persistent; },
      toggle(id) {
        if (!/^(item|horse)-\d+$/.test(id)) return false;
        if (ids.has(id)) ids.delete(id); else ids.add(id);
        try {
          storage.setItem(key, JSON.stringify([...ids]));
          persistent = true;
        } catch { persistent = false; }
        return ids.has(id);
      },
      sync(value) {
        try { ids = parse(value); } catch { /* Ignore malformed external updates. */ }
      }
    };
  }
  globalThis.BadRosesWishlist = { key, createStore };
})();
