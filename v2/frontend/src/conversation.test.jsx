/**
 * conversation.test.jsx — Phase 15 CONVO-01..05 contract tests.
 *
 * Wave 0 stubs: most tests will fail RED until Plan 03 (data.jsx rewrite)
 * and Plan 04 (app.jsx + components.jsx wiring) complete.
 */
import { describe, it, expect, beforeAll, vi, afterEach, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/react';
import { STEPS, PHASES, accumulateSignals, isStepVisible, getVisibleSteps } from './data.jsx';
import { StepInput, answerValid } from './components.jsx';
import App from './app.jsx';

// jsdom does not implement Element.prototype.scrollTo; App calls it inside a
// useEffect on the thread ref. Polyfill with a no-op so render paths don't throw.
beforeAll(() => {
  if (typeof HTMLElement !== 'undefined' && typeof HTMLElement.prototype.scrollTo !== 'function') {
    HTMLElement.prototype.scrollTo = function () {};
  }
});

describe('CONVO-01: QUESTION_BANK steps in Phase 1', () => {
  it('STEPS contains qb_work_output_type with phase 1', () => {
    const step = STEPS.find(s => s.id === 'qb_work_output_type');
    expect(step).toBeDefined();
    expect(step.phase).toBe(1);
  });

  it('STEPS does not contain the old workType step', () => {
    const step = STEPS.find(s => s.id === 'workType');
    expect(step).toBeUndefined();
  });
});

describe('CONVO-03: Phase chips use new phase names', () => {
  it('PHASES equals the 6 v2.0 phase names', () => {
    expect(PHASES).toEqual([
      'Role', 'Work Type', 'Classification', 'Duties', 'Qualifications', 'Review'
    ]);
  });
});

describe('CONVO-04: OgConfirmList renders candidates from cfg', () => {
  it('renders candidate button when candidates array is non-empty', () => {
    const cfg = {
      type: 'og_confirm',
      candidates: [
        {
          og_code: 'EC',
          og_name: 'Economics and Social Science Services',
          confidence: 0.85,
          rank: 1,
          rationale: 'Signal profile matches EC group',
          evidence_quotes: [],
          definition_excerpt: 'The EC Group comprises positions primarily involved...',
          relevant_inclusions: '',
          relevant_exclusions: '',
          available_levels: [1, 2, 3, 4, 5, 6, 7, 8],
        },
      ],
    };
    const { getByRole, queryAllByText } = render(
      <StepInput cfg={cfg} value={null} onChange={() => {}} onSubmit={() => {}} record={{}} />
    );
    // The component renders a <button> per candidate; EC appears in both the
    // title (og_code) and the definition_excerpt — use getAllByText via queryAllByText
    expect(getByRole('button')).toBeTruthy();
    expect(queryAllByText(/EC/).length).toBeGreaterThan(0);
  });
});

describe('CLASS-03: OgLevelPicker renders level range', () => {
  it('renders 8 level buttons for EC range 1-8', () => {
    const cfg = { type: 'og_level', levels: [1, 2, 3, 4, 5, 6, 7, 8] };
    const { getAllByRole } = render(
      <StepInput cfg={cfg} value={null} onChange={() => {}} onSubmit={() => {}} record={{}} />
    );
    const buttons = getAllByRole('button');
    expect(buttons.length).toBe(8);
  });
});

describe('CONVO-05: answerValid returns true for valid choices answer', () => {
  it('choices step with non-null option is valid', () => {
    const step = { input: { type: 'choices', options: [] } };
    expect(answerValid(step, { id: 'analysis_advice', title: 'Some title' })).toBe(true);
  });
});

describe('CONVO-02: accumulateSignals pure function', () => {
  it('returns null for empty answers', () => {
    expect(accumulateSignals({})).toBeNull();
  });

  it('accumulates EC signal from qb_work_output_type answer', () => {
    const answers = {
      qb_work_output_type: {
        id: 'analysis_advice',
        title: 'Analysis, options, or recommendations for decision-makers',
        signals: { og_candidates: ['EC'], jes_factor_hints: [] },
      },
    };
    const result = accumulateSignals(answers);
    expect(result).not.toBeNull();
    expect(result.dominant).toBe('EC');
    expect(result.tally['EC']).toBe(1);
  });
});

describe('CONVO-02: jumpToExchange resets stepIndex', () => {
  it('clicking a prior exchange resets stepIndex to that exchange index', () => {
    // Renders App, advances past two steps via jumpToExchange(0), confirms stepIndex resets.
    // Wave 0 stub: fails RED until Plan 04 wires jumpToExchange in app.jsx.
    const { getByTestId } = render(<App />);
    // jumpToExchange is exposed via data-testid="jump-0" on committed exchange bubbles
    const jumpTarget = getByTestId('jump-0');
    fireEvent.click(jumpTarget);
    // After click, the active step input should correspond to step index 0 (title step)
    expect(document.querySelector('[data-step-id="title"]')).not.toBeNull();
  });
});

describe('CONVO-05: Enter key submits text input', () => {
  it('pressing Enter on a text input calls onSubmit', () => {
    // Wave 0 stub: fails RED until Plan 04 wires keyboard handler in components.jsx.
    const cfg = { type: 'text', placeholder: 'test', preset: '' };
    let submitted = false;
    const { container } = render(
      <StepInput cfg={cfg} value="hello" onChange={() => {}} onSubmit={() => { submitted = true; }} record={{}} />
    );
    const input = container.querySelector('input');
    expect(input).not.toBeNull();
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
    expect(submitted).toBe(true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Phase 21 — OGX-04 / OGX-07: regression tests for the two continuation bugs
// the user surfaced after Plan 06 verification:
//   1. Sub-group picker never rendered (cfg.subgroup_alert not wired in app.jsx)
//   2. Sector-gate + cluster questions asked on every pass (no gating)
// ─────────────────────────────────────────────────────────────────────────────

describe('OGX-07: OgConfirmList renders sub-group picker when value is NU + API returns alert', () => {
  let fetchMock;
  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        subgroup_alert: {
          subgroups: ['HOS', 'CHN', 'EMA'],
          descriptions: {
            HOS: 'Hospital Nursing — inpatient acute care',
            CHN: 'Community Health Nursing — public health and home care',
            EMA: 'Emergency Medical Attendant — pre-hospital emergency response',
          },
          disambiguation_text: 'Three sub-groups with different evaluation methods.',
          citation: 'TBS OCHRO — Nursing (NU) JES',
        },
      }),
    });
    globalThis.fetch = fetchMock;
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the sub-group picker buttons when value is NU and the API returns a subgroup_alert', async () => {
    // Regression: with the previous app.jsx implementation, cfgOverride did
    // NOT pass subgroup_alert to OgConfirmList, so the picker never rendered
    // at runtime. The new implementation fetches the alert locally when the
    // user picks NU/SW/ED in the draft, so the picker appears DURING the
    // og_confirm step (not after commit).
    const cfg = {
      type: 'og_confirm',
      candidates: [
        {
          og_code: 'NU',
          og_name: 'Nursing',
          confidence: 0.85,
          rank: 1,
          rationale: '',
          evidence_quotes: [],
          definition_excerpt: '',
          relevant_inclusions: '',
          relevant_exclusions: '',
          available_levels: [1, 2, 3, 4, 5, 6, 7, 8],
        },
      ],
      asec_alert: null,
      work_description: 'Provides nursing care in a hospital setting',
      confirmed_noc_code: '31301',
    };
    const value = { og_code: 'NU', og_name: 'Nursing' };
    const { container, queryByTestId } = render(
      <StepInput cfg={cfg} value={value} onChange={() => {}} onSubmit={() => {}} record={{}} />
    );
    // Wait for the fetch + render to complete
    await waitFor(() => {
      expect(queryByTestId('subgroup-picker')).not.toBeNull();
    });
    // And the three sub-group buttons render with the expected codes
    expect(container.textContent).toContain('HOS');
    expect(container.textContent).toContain('CHN');
    expect(container.textContent).toContain('EMA');
    // The fetch was called with confirmed_og: 'NU' in the body
    expect(fetchMock).toHaveBeenCalled();
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.confirmed_og).toBe('NU');
    expect(body.confirmed_noc_code).toBe('31301');
  });

  it('does NOT render the sub-group picker when value is EC (no subgroups)', async () => {
    // Regression guard: the picker must not appear for non-sub-group OGs.
    const cfg = {
      type: 'og_confirm',
      candidates: [
        { og_code: 'EC', og_name: 'EC', confidence: 0.85, rank: 1, rationale: '', evidence_quotes: [], definition_excerpt: '', relevant_inclusions: '', relevant_exclusions: '', available_levels: [1, 2, 3, 4, 5, 6, 7, 8] },
      ],
      asec_alert: null,
      work_description: 'Develops policy',
      confirmed_noc_code: '41402',
    };
    const value = { og_code: 'EC', og_name: 'Economics and Social Science Services' };
    const { queryByTestId } = render(
      <StepInput cfg={cfg} value={value} onChange={() => {}} onSubmit={() => {}} record={{}} />
    );
    // Picker is hidden for EC
    expect(queryByTestId('subgroup-picker')).toBeNull();
    // And the fetch was NOT called (no point fetching for a non-sub-group OG)
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('OGX-04: sector-gate + cluster questions gated by sector answer', () => {
  it('isStepVisible gates qb_health_social_cluster on qb_sector_gate === pa_sh_sector', () => {
    // Regression: cluster questions were asked on every pass. They must only
    // be visible when the corresponding sector was selected. This test asserts
    // the gating predicate.
    const answers = {
      qb_sector_gate: {
        id: 'pa_sh_sector',
        signals: { og_candidates: ['NU', 'SW', 'PS', 'WP'] },
      },
    };
    expect(isStepVisible({ id: 'qb_health_social_cluster' }, answers)).toBe(true);
    expect(isStepVisible({ id: 'qb_legal_cluster' }, answers)).toBe(false);
    expect(isStepVisible({ id: 'qb_technical_cluster' }, answers)).toBe(false);
    expect(isStepVisible({ id: 'qb_education_cluster' }, answers)).toBe(false);
  });

  it('isStepVisible gates qb_legal_cluster on qb_sector_gate === legal_sector', () => {
    const answers = {
      qb_sector_gate: {
        id: 'legal_sector',
        signals: { og_candidates: ['LC', 'LP'] },
      },
    };
    expect(isStepVisible({ id: 'qb_legal_cluster' }, answers)).toBe(true);
    expect(isStepVisible({ id: 'qb_health_social_cluster' }, answers)).toBe(false);
    expect(isStepVisible({ id: 'qb_technical_cluster' }, answers)).toBe(false);
    expect(isStepVisible({ id: 'qb_education_cluster' }, answers)).toBe(false);
  });

  it('isStepVisible gates qb_technical_cluster on qb_sector_gate === technical_scientific_sector', () => {
    const answers = {
      qb_sector_gate: {
        id: 'technical_scientific_sector',
        signals: { og_candidates: ['FB', 'FS', 'MT'] },
      },
    };
    expect(isStepVisible({ id: 'qb_technical_cluster' }, answers)).toBe(true);
    expect(isStepVisible({ id: 'qb_health_social_cluster' }, answers)).toBe(false);
    expect(isStepVisible({ id: 'qb_legal_cluster' }, answers)).toBe(false);
    expect(isStepVisible({ id: 'qb_education_cluster' }, answers)).toBe(false);
  });

  it('isStepVisible gates qb_education_cluster on qb_sector_gate === education_sector', () => {
    const answers = {
      qb_sector_gate: {
        id: 'education_sector',
        signals: { og_candidates: ['ED', 'NT'] },
      },
    };
    expect(isStepVisible({ id: 'qb_education_cluster' }, answers)).toBe(true);
    expect(isStepVisible({ id: 'qb_health_social_cluster' }, answers)).toBe(false);
    expect(isStepVisible({ id: 'qb_legal_cluster' }, answers)).toBe(false);
    expect(isStepVisible({ id: 'qb_technical_cluster' }, answers)).toBe(false);
  });

  it('isStepVisible hides cluster questions when no sector answer is set', () => {
    // Defensive: until the sector question is answered, cluster questions
    // are hidden. The linear flow guarantees the user encounters the
    // sector question first (answerValid blocks Continue without an
    // answer), so cluster questions are never shown in the linear path
    // until the sector matches. This is the gating that prevents the
    // "questions fire on every pass" bug.
    expect(isStepVisible({ id: 'qb_health_social_cluster' }, {})).toBe(false);
    expect(isStepVisible({ id: 'qb_legal_cluster' }, {})).toBe(false);
    expect(isStepVisible({ id: 'qb_technical_cluster' }, {})).toBe(false);
    expect(isStepVisible({ id: 'qb_education_cluster' }, {})).toBe(false);
  });

  it('isStepVisible treats non-cluster steps as unconditionally visible', () => {
    // Regression guard: only the 4 cluster questions are gated. Title,
    // sector-gate, NOC/OG/level, duties, quals must always be visible.
    expect(isStepVisible({ id: 'title' }, {})).toBe(true);
    expect(isStepVisible({ id: 'qb_sector_gate' }, {})).toBe(true);
    expect(isStepVisible({ id: 'noc_confirm' }, {})).toBe(true);
    expect(isStepVisible({ id: 'duties' }, {})).toBe(true);
    expect(isStepVisible({ id: 'quals' }, {})).toBe(true);
  });

  it('getVisibleSteps omits non-matching cluster steps for legal_sector', () => {
    const answers = {
      qb_sector_gate: {
        id: 'legal_sector',
        signals: { og_candidates: ['LC', 'LP'] },
      },
    };
    const visible = getVisibleSteps(STEPS, answers);
    const visibleIds = visible.map(s => s.id);
    // Legal cluster is shown
    expect(visibleIds).toContain('qb_legal_cluster');
    // Other clusters are hidden
    expect(visibleIds).not.toContain('qb_health_social_cluster');
    expect(visibleIds).not.toContain('qb_technical_cluster');
    expect(visibleIds).not.toContain('qb_education_cluster');
  });

  it('getVisibleSteps omits all cluster steps when no sector answer (20 - 4 = 16)', () => {
    const visible = getVisibleSteps(STEPS, {});
    // With no sector answer, all 4 cluster questions are hidden.
    // The 4 work-type questions + 5 role + summary + sector + noc/og/level + duties + quals
    // are all visible. Total 16 = 20 - 4 cluster.
    expect(visible.length).toBe(16);
    const visibleIds = visible.map(s => s.id);
    expect(visibleIds).not.toContain('qb_health_social_cluster');
    expect(visibleIds).not.toContain('qb_legal_cluster');
    expect(visibleIds).not.toContain('qb_technical_cluster');
    expect(visibleIds).not.toContain('qb_education_cluster');
  });
});
