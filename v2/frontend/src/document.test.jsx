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

// ─────────────────────────────────────────────────────────────────────────────
// Phase 18: JD Composition & Live Preview stubs (RED — Wave 2 makes them GREEN)
// ─────────────────────────────────────────────────────────────────────────────

describe('DocumentPane — DOC-01: Section 5 ghost renders unconditionally', () => {
  it('renders Essential Qualifications section even when qualsVisited is falsy', () => {
    // RED stub — Wave 2 changes condition in document.jsx
    expect(false, 'RED stub — DOC-01').toBe(true);
  });
});

describe('DocumentPane — DOC-03: Section 3 ghost note copy', () => {
  it('shows "Select duties from the NOC list" when no duties', () => {
    // RED stub — Wave 2 changes ghost-note copy in document.jsx
    expect(false, 'RED stub — DOC-03').toBe(true);
  });
});

describe('DocumentPane — DOC-04: Section 3 header click calls onEditStep duties', () => {
  it('calls onEditStep("duties") when Section 3 header clicked in review state', () => {
    // RED stub — Wave 2 confirms onEditStep wiring in document.jsx
    expect(false, 'RED stub — DOC-04').toBe(true);
  });
});

describe('DocumentPane — DOC-05: Section 3 src pill shows "NOC 2021" not "NOC 2021 · refined"', () => {
  it('src pill text is "NOC 2021" when duties present', () => {
    // RED stub — Wave 2 removes "· refined" suffix from document.jsx
    expect(false, 'RED stub — DOC-05').toBe(true);
  });
});

describe('OrphanBadge — JD-04: badge renders when d.orphan true + reviewing', () => {
  it('renders orphan badge inside duty li when orphan is true and reviewing is true', () => {
    // RED stub — Wave 2 adds OrphanBadge component + export to document.jsx
    expect(false, 'RED stub — JD-04').toBe(true);
  });
});

describe('DutyBuilder — JD-01: fetches from API when noc_code prop present', () => {
  it('calls fetch /api/noc/{noc_code}/duties on mount', () => {
    // RED stub — Wave 2 rewires DutyBuilder in components.jsx
    expect(false, 'RED stub — JD-01 frontend').toBe(true);
  });
});
