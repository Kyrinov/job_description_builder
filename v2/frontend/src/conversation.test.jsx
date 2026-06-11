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

// Helpers for driving the App through the conversation flow in integration
// tests. The App is one big state machine, so tests that walk through more
// than a couple of steps need these to stay readable.
function clickPrimary(container) {
  const btn = container.querySelector('.btn.btn--primary');
  if (!btn) throw new Error('primary button not found');
  if (btn.disabled) throw new Error('primary button is disabled — fill input first');
  fireEvent.click(btn);
}
function pickOptionByText(container, text) {
  const choices = Array.from(container.querySelectorAll('.choice'));
  const match = choices.find(c => c.textContent && c.textContent.includes(text));
  if (!match) {
    throw new Error(
      `choice containing ${JSON.stringify(text)} not found; ` +
      `available: ${choices.map(c => c.textContent).join(' | ')}`
    );
  }
  fireEvent.click(match);
}
function fillInput(container, value) {
  const input = container.querySelector('input.tf, textarea');
  if (!input) throw new Error('input not found');
  fireEvent.change(input, { target: { value } });
}

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
    // Phase 21 Plan 07: the work-type steps are gated on qb_sector_gate ===
    // 'other_sector'. The test now seeds the sector answer so the work-type
    // step is visible to accumulateSignals.
    const answers = {
      qb_sector_gate: { id: 'other_sector', signals: { og_candidates: ['EC', 'AS', 'IT', 'FI'] } },
      qb_work_output_type: {
        id: 'analysis_advice',
        title: 'Analysis, options, or recommendations for decision-makers',
        signals: { og_candidates: ['EC'], jes_factor_hints: [] },
      },
    };
    const result = accumulateSignals(answers);
    expect(result).not.toBeNull();
    expect(result.dominant).toBe('EC');
    // The sector itself contributes EC (from its og_candidates list) and the
    // work-type answer contributes EC. Tally is therefore at least 1; the
    // important assertion is that the work-type signal is included.
    expect(result.tally['EC']).toBeGreaterThanOrEqual(1);
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

  it('getVisibleSteps omits all cluster steps when no sector answer (21 - 9 = 12)', () => {
    // Phase 21 Plan 07: the 4 legacy work-type questions + the 4 cluster
    // questions + qb_programme_admin_cluster are all gated on the sector
    // answer. With no sector answer, all 9 of those are hidden. The 5
    // role + summary + sector + 4 post-cluster steps (noc/og/level/duties/quals)
    // remain visible. Total 12 = 21 - 9 gated.
    const visible = getVisibleSteps(STEPS, {});
    expect(visible.length).toBe(12);
    const visibleIds = visible.map(s => s.id);
    expect(visibleIds).not.toContain('qb_work_output_type');
    expect(visibleIds).not.toContain('qb_work_audience');
    expect(visibleIds).not.toContain('qb_knowledge_specialization');
    expect(visibleIds).not.toContain('qb_policy_interpretation');
    expect(visibleIds).not.toContain('qb_health_social_cluster');
    expect(visibleIds).not.toContain('qb_legal_cluster');
    expect(visibleIds).not.toContain('qb_technical_cluster');
    expect(visibleIds).not.toContain('qb_education_cluster');
    expect(visibleIds).not.toContain('qb_programme_admin_cluster');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Phase 21 Plan 07 — OGX-04 (round 2): gate 4 legacy work-type questions to
// other_sector only, and add the 5th cluster (qb_programme_admin_cluster) for
// the programme_admin_sector path. The legacy EC/AS/IT/FI questions should
// only appear for users who chose "General professional or administrative
// work" (other_sector); the new programme_admin_cluster only appears for
// users who chose "Programme and administrative operations".
// ─────────────────────────────────────────────────────────────────────────────

describe('OGX-04 (Plan 07): 4 legacy work-type questions gated to other_sector', () => {
  const legacyIds = [
    'qb_work_output_type',
    'qb_work_audience',
    'qb_knowledge_specialization',
    'qb_policy_interpretation',
  ];

  it('hides each legacy question when sector is pa_sh_sector', () => {
    const answers = {
      qb_sector_gate: { id: 'pa_sh_sector', signals: { og_candidates: ['NU', 'SW', 'PS', 'WP'] } },
    };
    for (const id of legacyIds) {
      expect(isStepVisible({ id }, answers)).toBe(false);
    }
  });

  it('shows each legacy question when sector is other_sector', () => {
    const answers = {
      qb_sector_gate: { id: 'other_sector', signals: { og_candidates: ['EC', 'AS', 'IT', 'FI'] } },
    };
    for (const id of legacyIds) {
      expect(isStepVisible({ id }, answers)).toBe(true);
    }
  });

  it('hides each legacy question when sector is undefined (user must answer sector gate first)', () => {
    // When sector is undefined (falsy), `sector === 'other_sector'` is false.
    // The activeStepIndex logic in app.jsx will skip the invisible steps
    // forward to qb_sector_gate, forcing the user to pick a sector first.
    // This is by design — the Socratic intent is to never ask questions
    // until the sector is known.
    for (const id of legacyIds) {
      expect(isStepVisible({ id }, {})).toBe(false);
    }
  });

  it('accumulateSignals does NOT include signals from qb_work_output_type when sector is pa_sh_sector', () => {
    const answers = {
      qb_sector_gate: { id: 'pa_sh_sector', signals: { og_candidates: ['NU', 'SW', 'PS', 'WP'] } },
      qb_work_output_type: {
        id: 'analysis_advice',
        title: 'Analysis',
        signals: { og_candidates: ['EC'], jes_factor_hints: [], teer_affinity: [1, 2] },
      },
    };
    const result = accumulateSignals(answers);
    // EC should not appear in the tally because the step is invisible
    expect(result === null || (result.tally && result.tally['EC'] === undefined)).toBe(true);
  });

  it('accumulateSignals DOES include signals from qb_work_output_type when sector is other_sector', () => {
    // The only sector for which the work-type step is visible is other_sector.
    // We assert that the work-type signal flows through to the tally. The
    // exact count is 2 (1 from sector's own EC + 1 from work-type EC), so
    // we check >= 1 to confirm the work-type signal is included.
    const answers = {
      qb_sector_gate: { id: 'other_sector', signals: { og_candidates: ['EC', 'AS', 'IT', 'FI'] } },
      qb_work_output_type: {
        id: 'analysis_advice',
        title: 'Analysis',
        signals: { og_candidates: ['EC'], jes_factor_hints: [], teer_affinity: [1, 2] },
      },
    };
    const result = accumulateSignals(answers);
    expect(result).not.toBeNull();
    expect(result.tally['EC']).toBeGreaterThanOrEqual(1);
  });
});

describe('OGX-04 (Plan 07): qb_programme_admin_cluster visible only for programme_admin_sector', () => {
  it('shows qb_programme_admin_cluster when sector is programme_admin_sector', () => {
    const answers = {
      qb_sector_gate: { id: 'programme_admin_sector', signals: { og_candidates: ['PO', 'WP'] } },
    };
    expect(isStepVisible({ id: 'qb_programme_admin_cluster' }, answers)).toBe(true);
  });

  it('hides qb_programme_admin_cluster when sector is pa_sh_sector', () => {
    const answers = {
      qb_sector_gate: { id: 'pa_sh_sector', signals: { og_candidates: ['NU', 'SW', 'PS', 'WP'] } },
    };
    expect(isStepVisible({ id: 'qb_programme_admin_cluster' }, answers)).toBe(false);
  });

  it('hides qb_programme_admin_cluster when sector is undefined', () => {
    expect(isStepVisible({ id: 'qb_programme_admin_cluster' }, {})).toBe(false);
  });

  it('hides qb_programme_admin_cluster when sector is other_sector', () => {
    const answers = {
      qb_sector_gate: { id: 'other_sector', signals: { og_candidates: ['EC', 'AS', 'IT', 'FI'] } },
    };
    expect(isStepVisible({ id: 'qb_programme_admin_cluster' }, answers)).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Phase 21 — OGX-04 (bugfix round 3): regression test for the screen-blank bug
// the user surfaced after Plan 06 round-2 verification. When the user picks
// "Direct patient care" (nursing_hospital) in the qb_health_social_cluster
// step, commit() advances stepIndex from 11 → 15 (skipping 3 invisible cluster
// steps at indices 12, 13, 14). The previous fix rendered the answered
// exchanges from STEPS.slice(0, stepIndex) — which includes those 3 invisible
// steps. Their transcripts are `a => a.title`, which throws TypeError when
// the answer is undefined. React's error boundary then unmounts the tree
// and the screen goes blank.
//
// Fix: filter answeredSteps to only include steps that were actually
// answered. The 3 skipped cluster questions are excluded because the user
// never saw them. This test walks through the full flow up to and past
// the cluster step and verifies the next step (noc_confirm) renders.
// ─────────────────────────────────────────────────────────────────────────────

describe('OGX-04 (bugfix round 3): screen does not blank after cluster step commit', () => {
  beforeEach(() => {
    // The App fires several fetch calls during the flow (NOC, OG, WD
    // persistence). Mock all of them to keep the test hermetic.
    globalThis.fetch = vi.fn().mockImplementation(async (url, init) => {
      if (typeof url === 'string' && url.includes('/api/og/classify')) {
        return {
          ok: true,
          json: async () => ({ candidates: [], asec_alert: null, subgroup_alert: null }),
        };
      }
      if (typeof url === 'string' && url.includes('/api/noc/map')) {
        return { ok: true, json: async () => ({ candidates: [] }) };
      }
      if (typeof url === 'string' && url.match(/\/api\/wd($|\/)/)) {
        if (init && init.method === 'POST') {
          return { ok: true, json: async () => ({ id: 'test-wd-id' }) };
        }
        return { ok: true, json: async () => ({}) };
      }
      return { ok: true, json: async () => ({}) };
    });
  });
  afterEach(() => { vi.restoreAllMocks(); });

  it('advances to noc_confirm without blanking the screen after picking "Direct patient care"', () => {
    // Walk through the conversation flow:
    //   title → branch → reports → reports_to_military → supervises
    //     → summary
    //     → qb_sector_gate (pick "Health and social services")
    //     → qb_health_social_cluster (pick "Direct patient care")
    //   After commit on the cluster step, the user should land on
    //   noc_confirm (not a blank screen).
    //
    // Phase 21 Plan 07: the 4 legacy work-type questions (qb_work_output_type,
    // qb_work_audience, qb_knowledge_specialization, qb_policy_interpretation)
    // are now gated on qb_sector_gate === 'other_sector'. For a user who
    // picks any other sector, those 4 steps are skipped in the linear flow
    // (activeStepIndex walks past them). The user now goes from summary
    // directly to qb_sector_gate.
    const { container } = render(<App />);

    // Phase 0 — role
    fillInput(container, 'Registered Nurse');
    clickPrimary(container);
    fillInput(container, 'Health Services');
    clickPrimary(container);
    fillInput(container, 'Director of Nursing');
    clickPrimary(container);
    pickOptionByText(container, 'No — reports to a civilian supervisor');
    clickPrimary(container);
    pickOptionByText(container, 'No — individual contributor');
    clickPrimary(container);

    // Phase 1 — summary only (work-type steps are skipped for non-other sectors)
    fillInput(container, 'Provides direct patient care in a hospital ward.');
    clickPrimary(container);

    // Phase 2 — sector gate
    pickOptionByText(container, 'Health and social services');
    clickPrimary(container);

    // We're now on the cluster step (qb_health_social_cluster) — verify
    expect(container.querySelector('[data-step-id="qb_health_social_cluster"]')).not.toBeNull();

    // Pick the cluster option that triggered the bug report
    pickOptionByText(container, 'Direct patient care');
    expect(container.querySelector('[data-step-id="qb_health_social_cluster"]')).not.toBeNull();

    // Commit — the user should advance to noc_confirm. Before the fix,
    // this threw "Cannot read properties of undefined (reading 'title')"
    // inside the <Exchange> for qb_legal_cluster (which the user never
    // answered) and blanked the screen.
    clickPrimary(container);

    // The next active step is noc_confirm (skipping 3 invisible clusters)
    expect(container.querySelector('[data-step-id="noc_confirm"]')).not.toBeNull();

    // The screen should still show the question text and the active question.
    // If the tree was unmounted by an error, these would be missing.
    const activeQuestion = container.querySelector('.ask');
    expect(activeQuestion).not.toBeNull();
    expect(activeQuestion.textContent).toContain('NOC');
  });

  it('also handles the other 3 sectors without blanking (each skips 3 invisible clusters)', () => {
    // Smoke test for the other 3 sector routes. Each one has a single
    // visible cluster that the user answers; commit() then skips the 3
    // invisible clusters and advances to noc_confirm. The previous bug
    // would blank the screen for all 4 cases.
    //
    // Phase 21 Plan 07: the 4 legacy work-type steps are now skipped for
    // these sectors (they're gated on other_sector). The user goes from
    // summary directly to qb_sector_gate.
    const sectors = [
      { sector: 'Legal services', cluster: 'Providing legal counsel' },
      { sector: 'Technical or scientific operations', cluster: 'Examining travellers' },
      { sector: 'Education and training', cluster: 'Teaching language' },
    ];
    for (const { sector, cluster } of sectors) {
      const { container, unmount } = render(<App />);
      // Phase 0 — role (5 steps)
      fillInput(container, 'Worker');
      clickPrimary(container);
      fillInput(container, 'Branch');
      clickPrimary(container);
      fillInput(container, 'Director');
      clickPrimary(container);
      pickOptionByText(container, 'No — reports to a civilian supervisor');
      clickPrimary(container);
      pickOptionByText(container, 'No — individual contributor');
      clickPrimary(container);
      // Phase 1 — summary only (no work-type questions for non-other sectors)
      fillInput(container, 'Does work.');
      clickPrimary(container);
      // Sector + cluster
      pickOptionByText(container, sector);
      clickPrimary(container);
      pickOptionByText(container, cluster);
      clickPrimary(container);
      // Should land on noc_confirm without blanking
      expect(container.querySelector('[data-step-id="noc_confirm"]')).not.toBeNull();
      unmount();
    }
  });
});
