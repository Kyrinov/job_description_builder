console.log('[SETUP] loading vitest.setup.js');
const _store = new Map();

class InMemoryStorage {
  constructor() { this._data = _store; }
  get length() { return this._data.size; }
  key(i) {
    if (i < 0 || i >= this._data.size) return null;
    return Array.from(this._data.keys())[i];
  }
  getItem(k) { return this._data.has(k) ? this._data.get(k) : null; }
  setItem(k, v) { this._data.set(String(k), String(v)); }
  removeItem(k) { this._data.delete(k); }
  clear() { this._data.clear(); }
}

globalThis.localStorage = new InMemoryStorage();
globalThis.Storage = InMemoryStorage;
console.log('[SETUP] polyfill installed');
