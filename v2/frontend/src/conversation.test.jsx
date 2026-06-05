/**
 * conversation.test.jsx — Phase 15 CONVO-01..05 contract tests.
 *
 * Wave 0 stubs: most tests will fail RED until Plan 03 (data.jsx rewrite)
 * and Plan 04 (app.jsx + components.jsx wiring) complete.
 */
import { describe, it, expect, beforeAll } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { STEPS, PHASES, accumulateSignals } from './data.jsx';
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
