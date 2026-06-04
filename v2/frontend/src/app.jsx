/* ============================================================
   JD Builder — main application
   ============================================================ */
import { useState, useRef, useEffect, useMemo } from 'react';
import { STEPS, PHASES, I, computeClassification } from './data.jsx';
import { Icon, initialAnswer, answerValid } from './components.jsx';
import { Header, Exchange, ActiveQuestion, ReviewState } from './conversation.jsx';
import { DocumentPane } from './document.jsx';

const FLASH = {
  title: 'title', branch: 'title', reports: 'title', supervises: 'summary',
  summary: 'summary', workType: 'level', scopeDirection: 'level', scopeAdvises: 'level', scopeImpact: 'level',
  duties: 'duties', drf: 'drf', quals: 'quals'
};

/* live classification badge in the preview header */
function ClassifyBadge({ cls }) {
  const c = 2 * Math.PI * 16;
  if (cls.status === 'analyzing') {
    return (
      <div className="classify">
        <div className="classify__txt">
          <div className="classify__state">Classification</div>
          <div className="classify__analyzing">
            <i /><i /><i />
            <span style={{ fontSize: 12, color: 'var(--ink-faint)', marginLeft: 6 }}>listening…</span>
          </div>
        </div>
      </div>
    );
  }
  const resolved = cls.status === 'resolved';
  const pct = Math.round((cls.confidence || 0.6) * 100);
  return (
    <div className={`classify${resolved ? ' is-resolved' : ''}`}>
      <div className="classify__txt">
        <div className="classify__state">{resolved ? 'Recommended classification' : 'Narrowing\u2026'}</div>
        <div className="classify__code">
          {resolved ? cls.code : cls.group + ' group'}
          <span className="muted">{resolved ? cls.points + ' pts' : cls.groupName.split(' ')[0]}</span>
        </div>
      </div>
      <div className="classify__ring">
        <svg width="38" height="38" viewBox="0 0 38 38">
          <circle className="track" cx="19" cy="19" r="16" fill="none" strokeWidth="3" />
          <circle
            className="fill" cx="19" cy="19" r="16" fill="none" strokeWidth="3"
            strokeDasharray={c} strokeDashoffset={c * (1 - (cls.confidence || 0.6))}
          />
        </svg>
        <div className="classify__pct">{pct}%</div>
      </div>
    </div>
  );
}

function App() {
  // record initialises lazily from localStorage so a refresh restores the WD in progress (FE-05)
  const [record, setRecord] = useState(() => {
    try {
      const raw = localStorage.getItem('jd-builder-v2-record');
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  });
  const [answers, setAnswers] = useState({});
  const [stepIndex, setStepIndex] = useState(0);
  const [draft, setDraft] = useState(() => initialAnswer(STEPS[0], {}));
  const [reviewing, setReviewing] = useState(false);
  const [editingReturn, setEditingReturn] = useState(false);
  const [flashes, setFlashes] = useState(new Set());
  const [toast, setToast] = useState(null);
  const threadRef = useRef(null);
  const docRef = useRef(null);

  const step = STEPS[stepIndex];

  // Persist record to localStorage on every change (FE-05).
  // flashes is a Set — not JSON-serializable, deliberately excluded.
  // Quota errors are swallowed; app keeps working without persistence.
  useEffect(() => {
    try {
      localStorage.setItem('jd-builder-v2-record', JSON.stringify(record));
    } catch {
      // storage quota exceeded — degrade gracefully, do not throw
    }
  }, [record]);

  // committed record
  const baseRecord = record;
  // live record reflects the in-progress draft so the doc fills as you answer
  const liveRecord = useMemo(() => {
    let patch = {};
    try { if (step) patch = step.apply(record, draft) || {}; } catch (e) { patch = {}; }
    const merged = { ...record, ...patch };
    if (step && step.id === 'quals') merged.qualsVisited = true;
    return merged;
  }, [record, draft, step]);

  const cls = useMemo(() => computeClassification(reviewing ? record : liveRecord), [liveRecord, record, reviewing]);

  // auto-scroll the transcript so the active question is in view
  useEffect(() => {
    if (threadRef.current && !reviewing) {
      threadRef.current.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [stepIndex, reviewing]);

  function flash(key) {
    if (!key) return;
    setFlashes(prev => { const n = new Set(prev); n.add(key); return n; });
    setTimeout(() => setFlashes(prev => { const n = new Set(prev); n.delete(key); return n; }), 1700);
  }

  function commit() {
    if (!answerValid(step, draft)) return;
    const patch = step.apply(record, draft) || {};
    const newRecord = { ...record, ...patch };
    if (step.id === 'quals') newRecord.qualsVisited = true;
    setRecord(newRecord);
    setAnswers(prev => ({ ...prev, [step.id]: draft }));
    flash(FLASH[step.id]);

    if (editingReturn) {
      setEditingReturn(false);
      setReviewing(true);
      return;
    }
    const next = stepIndex + 1;
    if (next >= STEPS.length) {
      setReviewing(true);
    } else {
      setStepIndex(next);
      const ns = STEPS[next];
      setDraft(answers[ns.id] !== undefined ? answers[ns.id] : initialAnswer(ns, newRecord));
    }
  }

  function goBack() {
    if (stepIndex === 0) return;
    const prev = stepIndex - 1;
    setStepIndex(prev);
    const ps = STEPS[prev];
    setDraft(answers[ps.id] !== undefined ? answers[ps.id] : initialAnswer(ps, record));
  }

  function editStep(stepId) {
    const idx = STEPS.findIndex(s => s.id === stepId);
    if (idx < 0) return;
    setReviewing(false);
    setEditingReturn(true);
    setStepIndex(idx);
    setDraft(answers[stepId] !== undefined ? answers[stepId] : initialAnswer(STEPS[idx], record));
  }

  function jumpToExchange(idx) {
    setReviewing(false);
    setEditingReturn(false);
    setStepIndex(idx);
    const s = STEPS[idx];
    setDraft(answers[s.id] !== undefined ? answers[s.id] : initialAnswer(s, record));
  }

  function exportAs(kind) {
    const msg = kind === 'clipboard' ? 'Job description copied to clipboard'
      : `${record.title || 'Work description'} exported as ${kind}`;
    setToast(msg);
    setTimeout(() => setToast(null), 2600);
  }

  function restart() {
    setRecord({}); setAnswers({}); setStepIndex(0);
    setDraft(initialAnswer(STEPS[0], {})); setReviewing(false); setEditingReturn(false);
  }

  const phaseIdx = reviewing ? PHASES.length - 1 : step.phase;
  const answeredSteps = STEPS.slice(0, stepIndex);

  return (
    <div className="app">
      {/* ---------- LEFT ---------- */}
      <div className="convo">
        <Header phaseIdx={phaseIdx} />
        {reviewing
          ? <ReviewState record={record} cls={cls} onExport={exportAs} onRestart={restart} />
          : (
            <div className="thread" ref={threadRef}>
              {answeredSteps.map((s, i) => (
                <Exchange
                  key={s.id} step={s} record={record} answer={answers[s.id]}
                  onEdit={() => jumpToExchange(i)}
                />
              ))}
              <ActiveQuestion
                step={step} record={record} draft={draft} setDraft={setDraft}
                onCommit={commit} onBack={goBack}
                canBack={stepIndex > 0 && !editingReturn}
                isLast={stepIndex === STEPS.length - 1}
              />
              {editingReturn && (
                <div style={{ marginLeft: 43, marginTop: 14 }}>
                  <button
                    className="btn btn--ghost" style={{ paddingLeft: 0 }}
                    onClick={() => { setEditingReturn(false); setReviewing(true); }}
                  >
                    ← Back to review without changes
                  </button>
                </div>
              )}
            </div>
          )}
      </div>
      {/* ---------- RIGHT ---------- */}
      <div className="preview">
        <div className="preview__head">
          <div className="preview__label">
            <span className="live-dot" />
            {reviewing ? 'Final document' : 'Building live'}
          </div>
          <div className="preview__spacer" />
          <ClassifyBadge cls={cls} />
        </div>
        <div className="doc-scroll" ref={docRef}>
          <DocumentPane
            record={reviewing ? record : liveRecord} cls={cls} flashes={flashes}
            reviewing={reviewing} onEditStep={editStep}
          />
        </div>
      </div>
      {/* ---------- toast ---------- */}
      <div className={`toast${toast ? ' is-show' : ''}`}>
        <Icon path={I.check} size={17} />
        <span>{toast || ''}</span>
      </div>
    </div>
  );
}

export default App;
