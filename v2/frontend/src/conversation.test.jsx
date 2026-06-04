/**
 * conversation.test.jsx — Phase 15 CONVO-01..05 contract tests.
 *
 * Wave 0 stubs: most tests will fail RED until Plan 03 (data.jsx rewrite)
 * and Plan 04 (app.jsx + components.jsx wiring) complete.
 */
import { describe, it, expect } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { STEPS, PHASES, accumulateSignals } from './data.jsx';
import { StepInput, answerValid } from './components.jsx';
import App from './app.jsx';

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

describe('CONVO-04: StepInput dispatches og_confirm type', () => {
  it('StepInput with type og_confirm renders something (not null)', () => {
    // og_confirm stub uses NocConfirmList — must render without crashing
    // and return a non-null element
    const cfg = { type: 'og_confirm', candidates: [] };
    const { container } = render(
      <StepInput cfg={cfg} value={null} onChange={() => {}} onSubmit={() => {}} record={{}} />
    );
    expect(container.firstChild).not.toBeNull();
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
