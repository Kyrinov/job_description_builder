/**
 * document.test.jsx — Phase 17 JES-04: ClassBlock scorecard render stubs.
 *
 * Tests that ClassBlock renders per-factor rows for EC groups and a single
 * totals line for non-EC groups. All tests are RED until Plan 17-03 wires
 * record.jes_scores into ClassBlock in document.jsx.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

// ClassBlock is not yet exported by document.jsx — import will fail (RED)
// Plan 17-03 exports it. Until then these tests fail at import.
let ClassBlock;
try {
  ({ ClassBlock } = await import('./document.jsx'));
} catch {
  ClassBlock = null;
}

describe('ClassBlock — JES-04', () => {
  it('renders per-factor rows for EC group (cls.factors truthy)', () => {
    if (!ClassBlock) throw new Error('RED — ClassBlock not exported from document.jsx');
    const cls = {
      code: 'EC-05', group: 'EC', groupName: 'Economics and Social Science Services',
      standard: 'EC JES 2017', points: 720,
      factors: [
        { name: 'Decision making', degree: 5, points: 90 },
        { name: 'Leadership & operational mgmt', degree: 3, points: 50 },
      ],
    };
    render(<ClassBlock cls={cls} />);
    expect(screen.getByText('Decision making')).toBeTruthy();
    expect(screen.getByText('D5')).toBeTruthy();
    expect(screen.getByText('90')).toBeTruthy();
  });

  it('renders single totals line for non-EC group (cls.factors falsy)', () => {
    if (!ClassBlock) throw new Error('RED — ClassBlock not exported from document.jsx');
    const cls = {
      code: 'IT-04', group: 'IT', groupName: 'Information Technology',
      standard: 'IT Job Evaluation Standard', points: 480,
      factors: null,
    };
    render(<ClassBlock cls={cls} />);
    expect(screen.getByText(/IT Job Evaluation Standard/)).toBeTruthy();
    expect(screen.getByText('480')).toBeTruthy();
  });
});
