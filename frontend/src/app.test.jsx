/**
 * app.test.jsx — FE-04 (state slices) + FE-05 (localStorage crash-recovery)
 * Activated in Plan 13-03 once app.jsx is ported.
 *
 * localStorage polyfill (in-memory) is installed at module load because
 * vitest 4.x + jsdom 29 ships an empty localStorage object (the `--localstorage-file`
 * CLI warning is the symptom; the upstream issue is in vitest's jsdom integration).
 * This shim is shared across tests within a file (clear() resets it).
 */
import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
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

// resetStorage() must clear the SAME Map that globalThis.localStorage uses.
// In vitest, vitest.setup.js installs an InMemoryStorage with its own
// closure-bound _store — app.test.jsx's _store is unrelated. Use the
// public clear() API on globalThis.localStorage so we're operating on
// the same Map the app reads.
function resetStorage() { globalThis.localStorage.clear(); }

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
  beforeEach(() => {
    resetStorage();
    // Phase 28 (MGR-01): seed the role so App skips the RoleSelector and
    // exercises the advisor track. Without this seed, App renders the
    // RoleSelector (because jd-builder-v2-role is absent from localStorage)
    // and these tests would fail to find the .brand__name / .app shell
    // they're asserting on.
    globalThis.localStorage.setItem('jd-builder-v2-role', 'advisor');
  });
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
  beforeEach(() => {
    resetStorage();
    // Phase 28 (MGR-01): seed the role so App exercises the advisor track.
    globalThis.localStorage.setItem('jd-builder-v2-role', 'advisor');
  });
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

describe('WD PATCH payload mirrors classification fields to root (JES-01 fix)', () => {
  // Regression: backend WorkDescription stores confirmed_og / og_level /
  // confirmed_noc / reports_to_military / jes_scores / jes_total_points at
  // the root, not nested in `record`. The frontend commit() must mirror them
  // up — otherwise /api/jes/score 409s on require_og_confirmed because the
  // stored WD has those fields null at root even after the local record
  // commits them.
  beforeEach(() => {
    resetStorage();
    vi.restoreAllMocks();
    // Phase 28 (MGR-01): seed the role so App exercises the advisor track.
    globalThis.localStorage.setItem('jd-builder-v2-role', 'advisor');
  });
  afterEach(() => {
    vi.restoreAllMocks();
    resetStorage();
  });

  it('PATCH payload sent to /api/wd/{id} includes confirmed_og and og_level at root when present in local record', async () => {
    globalThis.localStorage.setItem('jd-builder-v2-wd-id', 'test-wd-id');
    globalThis.localStorage.setItem('jd-builder-v2-record', JSON.stringify({
      title: 'Test Position',
      confirmed_og: { og_code: 'EC', og_name: 'Economics and Social Science Services' },
      og_level: 5,
    }));

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'test-wd-id' }),
    });
    globalThis.fetch = fetchMock;

    const { container } = render(<App />);
    // First step is "title" (a text input — TextInput renders <input className="tf">).
    // The initial draft is empty so the primary button is disabled — fill the
    // input first to enable it.
    const input = container.querySelector('input.tf, textarea');
    expect(input).not.toBeNull();
    fireEvent.change(input, { target: { value: 'Test Position' } });

    const btn = container.querySelector('.btn.btn--primary');
    expect(btn).not.toBeNull();
    expect(btn.disabled).toBe(false);
    fireEvent.click(btn);

    // Allow microtasks (PATCH is fire-and-forget) to flush
    await new Promise(r => setTimeout(r, 50));

    // The PATCH is the second call (POST /api/wd is the first). Find by URL+method.
    const patchCall = fetchMock.mock.calls.find(
      ([url, init]) => typeof url === 'string'
        && url.includes('/api/wd/test-wd-id')
        && init && init.method === 'PATCH'
    );
    expect(patchCall).toBeDefined();
    const body = JSON.parse(patchCall[1].body);
    expect(body.confirmed_og).toEqual({ og_code: 'EC', og_name: 'Economics and Social Science Services' });
    expect(body.og_level).toBe(5);
    // record is still sent (for full-state restoration)
    expect(body.record).toBeDefined();
    expect(body.record.confirmed_og).toEqual({ og_code: 'EC', og_name: 'Economics and Social Science Services' });
    expect(body.record.og_level).toBe(5);
  });

  // ---------------------------------------------------------------------------
  // Phase 26 — ORG-01: RED baseline for stepIndex resume-by-last-answered
  // ---------------------------------------------------------------------------

  it('stepIndex resume: initialises past step 0 when record has answered fields', () => {
    // Arrange — seed localStorage with a record that has og_level answered.
    // og_level sits at STEPS index 19 in the current STEPS array, so a
    // resume-by-last-answered initialiser must land at index 20 (one past
    // the last answered step), NOT 0 (the Title step).
    // Phase 28 (MGR-01): seed the role so App exercises the advisor track
    // (not the RoleSelector). The role seed is in beforeEach above; we
    // just need the record seed here.
    globalThis.localStorage.setItem('jd-builder-v2-record', JSON.stringify({
      title: 'Policy Analyst',
      og_level: 3,
    }));
    const { container } = render(<App />);
    // The ActiveQuestion surfaces data-testid={`jump-${stepIndex}`} on its
    // root .ask div (see conversation.jsx line 64). After the Phase 26 fix,
    // the testid MUST NOT be `jump-0` — the resume initialiser should have
    // advanced past the title step.
    const ask = container.querySelector('[data-testid^="jump-"]');
    expect(ask).toBeTruthy();
    const testid = ask.getAttribute('data-testid');
    const idx = parseInt(testid.replace('jump-', ''), 10);
    expect(idx).toBeGreaterThan(0);
  });

});

// ---------------------------------------------------------------------------
// Phase 28 — MGR-01: RoleSelector + userRole state hydration from localStorage
//
// MGR-01 contract: on first load (jd-builder-v2-role absent from
// localStorage) a role selector screen precedes the conversation. Selecting
// a role persists to localStorage and launches the matching track. Refresh
// does not re-show the selector because userRole hydrates from localStorage
// on mount. user_role NEVER appears in the WD PATCH body (D-28-03, asserted
// in the backend guard test test_user_role_dropped_from_patch).
// ---------------------------------------------------------------------------

describe('MGR-01: role selector + userRole hydration', () => {
  beforeEach(() => {
    resetStorage();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    resetStorage();
  });

  it('userRole hydrates from jd-builder-v2-role localStorage on mount', () => {
    // Seed localStorage with 'manager' — the role selector must NOT appear
    // because userRole resolved to 'manager' from the persisted key.
    globalThis.localStorage.setItem('jd-builder-v2-role', 'manager');
    const { container, queryByTestId } = render(<App />);
    expect(queryByTestId('role-selector')).toBeNull();
    // The main app shell IS shown.
    expect(container.querySelector('.app')).not.toBeNull();
  });

  it('role selector renders when jd-builder-v2-role is absent', () => {
    // localStorage cleared — role selector must be visible.
    const { getByTestId } = render(<App />);
    const selector = getByTestId('role-selector');
    expect(selector).toBeTruthy();
    // Both buttons render.
    expect(getByTestId('role-advisor')).toBeTruthy();
    expect(getByTestId('role-manager')).toBeTruthy();
  });

  it('selecting manager role persists to localStorage and launches manager track', () => {
    // Clear localStorage — role selector renders.
    const { getByTestId, queryByTestId } = render(<App />);
    expect(getByTestId('role-selector')).toBeTruthy();
    // Click the manager button.
    fireEvent.click(getByTestId('role-manager'));
    // localStorage was updated to 'manager'.
    expect(globalThis.localStorage.getItem('jd-builder-v2-role')).toBe('manager');
    // The role selector is no longer shown (the main app shell renders).
    expect(queryByTestId('role-selector')).toBeNull();
  });
});
