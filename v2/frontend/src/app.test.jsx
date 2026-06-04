/**
 * app.test.jsx — FE-04 (state slices) + FE-05 (localStorage crash-recovery)
 * Tests are RED until Plan 03 ports app.jsx.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, act } from '@testing-library/react';

// app.jsx does not exist yet — importing will fail until Plan 03.
// The test file must exist now so Wave 0 gate passes with a skip/todo.
// Replace with real import in Plan 03 once app.jsx is ported.

describe('App state slices (FE-04)', () => {
  it.todo('App renders without crashing');
  it.todo('record initialises to empty object {}');
  it.todo('answers initialises to empty object {}');
  it.todo('stepIndex initialises to 0');
  it.todo('reviewing initialises to false');
  it.todo('editingReturn initialises to false');
  it.todo('flashes initialises to an instance of Set');
  it.todo('toast initialises to null');
});

describe('localStorage crash-recovery (FE-05)', () => {
  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'setItem');
    vi.spyOn(Storage.prototype, 'getItem');
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it.todo('localStorage.setItem called with key jd-builder-v2-record on record change');
  it.todo('on mount with pre-seeded localStorage, record is restored from jd-builder-v2-record');
  it.todo('corrupt localStorage value (non-JSON) falls back to empty record without throwing');
});
