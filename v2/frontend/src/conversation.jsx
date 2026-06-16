/* ============================================================
   JD Builder — conversation pane (left)
   ============================================================ */
import React, { useState } from 'react';
import { PHASES, I } from './data.jsx';
import { Icon, Check, StepInput, answerValid } from './components.jsx';

/* brand + phase progress header */
function Header({ phaseIdx }) {
  return (
    <div className="convo__head">
      <div className="brand">
        <div className="brand__mark">
          <Icon path={I.spark} size={19} />
        </div>
        <div>
          <div className="brand__name">JD Builder</div>
          <div className="brand__sub">Guided work-description assistant</div>
        </div>
        <div className="brand__spacer" />
        <div className="brand__dept">National Defence</div>
      </div>
      <div className="phases">
        {PHASES.map((p, i) => (
          <div
            key={p}
            className={`phase${i === phaseIdx ? ' is-active' : ''}${i < phaseIdx ? ' is-done' : ''}`}
          >
            <div className="phase__bar"><i /></div>
            <div className="phase__label">{p}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* answered exchange (compact, clickable to edit) */
function Exchange({ step, record, answer, onEdit }) {
  const label = step.transcript ? step.transcript(answer, record) : String(answer);
  const qText = typeof step.q === 'function' ? step.q(record) : step.q;
  return (
    <div className="xchg">
      <div className="xchg__q">{qText}</div>
      <div className="xchg__a" onClick={onEdit} title="Click to revisit">{label}</div>
    </div>
  );
}

/* active question + input */
function helperHtml(step, record) {
  let h = typeof step.helper === 'function' ? step.helper(record) : step.helper;
  return h;
}

function ActiveQuestion({ step, record, draft, setDraft, onCommit, onBack, canBack, isLast, cfgOverride, dataTestid, dataStepId }) {
  const qText = typeof step.q === 'function' ? step.q(record) : step.q;
  const valid = answerValid(step, draft);
  const showEnter = step.input.type === 'text';
  return (
    <div
      className="ask"
      key={step.id}
      data-testid={dataTestid}
      data-step-id={dataStepId}
    >
      <div className="ask__row">
        <div className="ask__avatar">
          <Icon path={step.icon || I.spark} size={16} />
        </div>
        <div className="ask__body">
          <div className="ask__q">{qText}</div>
          {step.helper && (
            <div
              className="ask__helper"
              dangerouslySetInnerHTML={{ __html: helperHtml(step, record) }}
            />
          )}
        </div>
      </div>
      <div className="input-zone">
        <StepInput
          cfg={cfgOverride || step.input}
          value={draft}
          onChange={setDraft}
          onSubmit={() => { if (valid) onCommit(); }}
          record={record}
        />
      </div>
      <div className="actions">
        <button
          className="btn btn--primary"
          disabled={!valid}
          onClick={onCommit}
        >
          {isLast ? 'Finish & review' : 'Continue'}
          <Icon path='<path d="M4 10h11M11 5l5 5-5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' size={16} />
        </button>
        {canBack && (
          <button className="btn btn--ghost" onClick={onBack}>Back</button>
        )}
        {showEnter && (
          <span className="skip-hint">Press <kbd>Enter</kbd></span>
        )}
      </div>
    </div>
  );
}

/* Phase 24 (AUDIT-01/04/05): one finding card. Long citations (>240 chars) are
   shown truncated by default with a "Show more" toggle so the full CBA clause
   or court citation is reachable without re-running the audit. */
function FindingCard({ finding, onAuditDecide }) {
  const [expanded, setExpanded] = useState(false);
  const citation = finding.citation || '';
  const long = citation.length > 240;
  const visible = !long || expanded ? citation : citation.slice(0, 240) + '\u2026';
  return (
    <div
      className={`audit-finding audit-finding--${finding.severity}`}
      style={{
        border: '1px solid #ccc',
        borderRadius: '4px',
        padding: '0.75rem',
        marginBottom: '0.5rem',
        overflowWrap: 'anywhere',
      }}
    >
      <div className="finding-meta" style={{ marginBottom: '0.25rem' }}>
        <span className={`finding-severity finding-severity--${finding.severity}`}
              style={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '0.75rem' }}>
          {finding.severity}
        </span>
        {' \u2014 '}
        <span className="finding-section" style={{ fontSize: '0.85rem', color: '#555' }}>
          Section: {finding.section}
        </span>
      </div>
      <blockquote
        className="finding-citation"
        style={{ margin: '0.25rem 0', fontSize: '0.85rem', fontStyle: 'italic', color: '#333' }}
      >
        {visible}
      </blockquote>
      {long && (
        <button
          type="button"
          className="btn btn--ghost finding-toggle"
          style={{ fontSize: '0.8rem', padding: '0.1rem 0.4rem', marginBottom: '0.25rem' }}
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
      <p className="finding-recommendation" style={{ margin: '0.25rem 0', fontSize: '0.9rem' }}>
        {finding.recommendation}
      </p>
      <div className="finding-actions" style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
        <button
          className="btn btn--ghost"
          style={{ fontSize: '0.85rem' }}
          onClick={() => onAuditDecide && onAuditDecide(finding.rule_id, finding.section, 'accept')}
        >
          Accept
        </button>
        <button
          className="btn btn--ghost"
          style={{ fontSize: '0.85rem' }}
          onClick={() => onAuditDecide && onAuditDecide(finding.rule_id, finding.section, 'manual_edit')}
        >
          Manual Edit
        </button>
        <button
          className="btn btn--ghost"
          style={{ fontSize: '0.85rem' }}
          onClick={() => onAuditDecide && onAuditDecide(finding.rule_id, finding.section, 'skip')}
        >
          Not applicable — no conflict found
        </button>
      </div>
    </div>
  );
}

/* completion / review state */
function ReviewState({ record, cls, onExport, onRestart, amendmentNotes = {},
                       auditFindings = [], auditRunning = false, auditRan = false,
                       onRunAudit, onAuditDecide }) {
  const dutyCount = (record.duties || []).length;
  const checks = [
    ['Position identified', record.title],
    [cls.code ? `Classified as ${cls.code} \u00b7 ${cls.points} pts` : 'Classified', cls.status === 'resolved'],
    [`${dutyCount} key ${dutyCount === 1 ? 'responsibility' : 'responsibilities'}, formally worded`, dutyCount > 0],
    [record.drf ? `Linked to: ${record.drf.cr}` : 'Defence result linked', !!record.drf],
    ['Essential qualifications set', !!record.qualsVisited]
  ];
  // AMEND-01: amendment count checklist row (only when at least 1 note saved)
  const amendmentCount = Object.values(amendmentNotes).filter(n => n).length;
  if (amendmentCount > 0) {
    checks.push([
      `${amendmentCount} amendment note${amendmentCount === 1 ? '' : 's'} attached`,
      true,
    ]);
  }
  return (
    <div className="thread">
      <div className="done-card">
        <div className="done-card__icon">
          <Icon path={I.check} size={27} />
        </div>
        <div className="done-card__title">Your job description is ready.</div>
        <div className="done-card__sub">
          It reads as one cohesive document — not stitched-together fragments — and every element traces back to an authoritative source. Review it on the right; <b>click any section to revisit your answer.</b>
        </div>
        <div className="checklist">
          {checks.map(([label, ok], i) => (
            <div className="check-row" key={i}>
              <div className="check-row__dot"><Check /></div>
              <span>{label}</span>
            </div>
          ))}
        </div>
        <div className="export-row">
          <button className="btn--export" onClick={() => onExport('Word document (.docx)')}>
            <Icon path='<rect x="3" y="2.5" width="14" height="15" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M6 7h8M6 10h8M6 13h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>' />
            Export DOCX
          </button>
          <button className="btn--export" onClick={() => onExport('PDF')}>
            <Icon path='<rect x="3" y="2.5" width="14" height="15" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M6.5 13v-3.5h1.2a1.1 1.1 0 010 2.2H6.5M11 9.5V13M11 9.5h1.8M11 11.4h1.4" stroke="currentColor" stroke-width="1.3" fill="none" stroke-linecap="round"/>' />
            Export PDF
          </button>
          <button className="btn--export" onClick={() => onExport('clipboard')}>
            <Icon path='<rect x="6" y="3" width="11" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M3.5 6v9.5A1.5 1.5 0 005 17h8" fill="none" stroke="currentColor" stroke-width="1.6"/>' />
            Copy
          </button>
        </div>
        {/* Phase 24 (AUDIT-01): Compliance audit — manual trigger only. Button
            is disabled and shows "Auditing…" while the request is in flight. */}
        <div className="audit-row" style={{ marginTop: '1rem' }}>
          <button
            className="btn--export"
            onClick={onRunAudit}
            disabled={auditRunning}
            style={{ width: '100%' }}
          >
            {auditRunning ? 'Auditing\u2026' : 'Run compliance audit'}
          </button>
        </div>

        {/* Phase 24 (AUDIT-01/04): Findings panel — hidden until audit runs.
            Each finding shows severity, citation excerpt, recommendation, and
            3 decision buttons. Manual Edit opens the existing Phase 19
            amendment panel (AUDIT-05) via the onAuditDecide callback. */}
        {auditRan && auditFindings.length === 0 && (
          <div className="audit-findings audit-findings--clean" style={{ marginTop: '1rem' }}>
            <h4 style={{ marginBottom: '0.5rem' }}>Compliance Findings</h4>
            <p style={{ fontSize: '0.9rem', color: '#555' }}>
              No outstanding compliance findings.
            </p>
          </div>
        )}
        {auditFindings.length > 0 && (
          <div className="audit-findings" style={{ marginTop: '1rem' }}>
            <h4 style={{ marginBottom: '0.5rem' }}>Compliance Findings</h4>
            {auditFindings.map((finding, idx) => (
              <FindingCard
                key={finding.rule_id || idx}
                finding={finding}
                onAuditDecide={onAuditDecide}
              />
            ))}
          </div>
        )}

        <button className="btn btn--ghost restart" onClick={onRestart} style={{ paddingLeft: 0 }}>← Start a new description</button>
      </div>
    </div>
  );
}

export { Header, Exchange, ActiveQuestion, ReviewState, FindingCard };
