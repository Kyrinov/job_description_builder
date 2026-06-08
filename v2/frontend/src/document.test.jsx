/**
 * document.test.jsx — Phase 17 JES-04: ClassBlock scorecard render tests.
 *
 * Tests that ClassBlock renders per-factor rows for EC groups and a single
 * totals line for non-EC groups. Plan 17-03 exports ClassBlock from
 * document.jsx and wires the JES scorecard into Section 4.
 *
 * JES-04-regression: DocumentPane render gate uses jes_total_points (not
 * jes_scores.length) so non-EC groups (factors:[]) also render the scorecard.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ClassBlock, DocumentPane } from './document.jsx';

describe('ClassBlock — JES-04', () => {
  it('renders per-factor rows for EC group (cls.factors truthy)', () => {
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

describe('DocumentPane — JES-04 regression: scorecard gate', () => {
  const baseCls = { status: 'resolved', group: 'IT', groupName: 'Information Technology', code: 'IT-04', points: 480 };

  it('renders scorecard for non-EC group when jes_total_points is set (factors is empty array)', () => {
    // Backend returns factors:[] for non-EC; render must fire on jes_total_points, not jes_scores.length
    const record = {
      confirmed_og: { og_code: 'IT', og_name: 'Information Technology' },
      og_level: 4,
      jes_scores: [],
      jes_total_points: 480,
      jes_standard_name: 'IT Job Evaluation Standard',
      jes_is_ec: false,
    };
    render(<DocumentPane record={record} cls={baseCls} flashes={new Set()} reviewing={false} onEditStep={() => {}} onJesOverride={() => {}} />);
    expect(screen.getByText(/IT Job Evaluation Standard/)).toBeTruthy();
  });

  it('does not render scorecard before jes_total_points is set', () => {
    // Scorecard must not appear while JES fetch is still in flight
    const record = {
      confirmed_og: { og_code: 'IT', og_name: 'Information Technology' },
      og_level: 4,
    };
    render(<DocumentPane record={record} cls={baseCls} flashes={new Set()} reviewing={false} onEditStep={() => {}} onJesOverride={() => {}} />);
    expect(screen.queryByText(/IT Job Evaluation Standard/)).toBeFalsy();
  });
});
