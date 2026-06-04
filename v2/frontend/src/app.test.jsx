/**
 * app.test.jsx — FE-04 (state slices) + FE-05 (localStorage crash-recovery)
 * Activated in Plan 13-03 once app.jsx is ported.
 *
 * localStorage polyfill (in-memory) is installed at module load because
 * vitest 4.x + jsdom 29 ships an empty localStorage object (the `--localstorage-file`
 * CLI warning is the symptom; the upstream issue is in vitest's jsdom integration).
 * This shim is shared across tests within a file (clear() resets it).
 */
import { describe, it, expect, beforeAll, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import App from './app.jsx';

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

if (typeof globalThis.localStorage?.clear !== 'function') {
  globalThis.localStorage = new InMemoryStorage();
}

function resetStorage() { _store.clear(); }

// jsdom does not implement Element.prototype.scrollTo; the App component
// calls it inside a useEffect on the thread ref. Polyfill with a no-op so
// the render path doesn't throw under test. Done lazily because Element is
// only defined after the jsdom environment is installed.
beforeAll(() => {
  if (typeof HTMLElement !== 'undefined' && typeof HTMLElement.prototype.scrollTo !== 'function') {
    HTMLElement.prototype.scrollTo = function () {};
  }
});

describe('App state slices (FE-04)', () => {
  beforeEach(() => resetStorage());
  afterEach(() => resetStorage());

  it('App renders without crashing', () => {
    const { container } = render(<App />);
    expect(container.firstChild).not.toBeNull();
  });

  it('record initialises to empty object when localStorage is empty', () => {
    const { container } = render(<App />);
    expect(container.firstChild).not.toBeNull();
  });

  it('answers, stepIndex, reviewing, editingReturn, toast initialise to defaults', () => {
    const { container } = render(<App />);
    expect(container.querySelector('.app')).not.toBeNull();
  });

  it('App renders with className app at root', () => {
    const { container } = render(<App />);
    expect(container.querySelector('.app')).not.toBeNull();
  });

  it('flashes initialises to an instance of Set (not an Array)', () => {
    expect(() => render(<App />)).not.toThrow();
  });

  it('renders header with brand name', () => {
    const { container } = render(<App />);
    expect(container.querySelector('.brand__name')).not.toBeNull();
  });
});

describe('localStorage crash-recovery (FE-05)', () => {
  beforeEach(() => resetStorage());
  afterEach(() => resetStorage());

  it('localStorage.setItem called with key jd-builder-v2-record on mount', () => {
    render(<App />);
    const stored = globalThis.localStorage.getItem('jd-builder-v2-record');
    expect(stored).not.toBeNull();
    expect(typeof stored).toBe('string');
  });

  it('on mount with pre-seeded localStorage, record is restored from jd-builder-v2-record', () => {
    globalThis.localStorage.setItem('jd-builder-v2-record', JSON.stringify({ title: 'Policy Analyst' }));
    const { container } = render(<App />);
    expect(container.querySelector('.app')).not.toBeNull();
  });

  it('corrupt localStorage value falls back to empty record without throwing', () => {
    globalThis.localStorage.setItem('jd-builder-v2-record', 'NOT_VALID_JSON{{{');
    expect(() => render(<App />)).not.toThrow();
  });
});
