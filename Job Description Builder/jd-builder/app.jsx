/* ============================================================
   JD Builder — main application
   ============================================================ */
(function () {
  const { useState, useRef, useEffect, useMemo } = React;
  const D = window.JD_DATA;
  const { Icon, initialAnswer, answerValid } = window.JD_COMP;
  const { Header, Exchange, ActiveQuestion, ReviewState } = window.JD_CONVO;
  const { DocumentPane } = window.JD_DOC;

  const FLASH = {
    title: 'title', branch: 'title', reports: 'title', supervises: 'summary',
    summary: 'summary', workType: 'level', scopeDirection: 'level', scopeAdvises: 'level', scopeImpact: 'level',
    duties: 'duties', drf: 'drf', quals: 'quals'
  };

  /* live classification badge in the preview header */
  function ClassifyBadge({ cls }) {
    const c = 2 * Math.PI * 16;
    if (cls.status === 'analyzing') {
      return React.createElement('div', { className: 'classify' },
        React.createElement('div', { className: 'classify__txt' },
          React.createElement('div', { className: 'classify__state' }, 'Classification'),
          React.createElement('div', { className: 'classify__analyzing' },
            React.createElement('i'), React.createElement('i'), React.createElement('i'),
            React.createElement('span', { style: { fontSize: 12, color: 'var(--ink-faint)', marginLeft: 6 } }, 'listening\u2026'))
        )
      );
    }
    const resolved = cls.status === 'resolved';
    const pct = Math.round((cls.confidence || 0.6) * 100);
    return React.createElement('div', { className: 'classify' + (resolved ? ' is-resolved' : '') },
      React.createElement('div', { className: 'classify__txt' },
        React.createElement('div', { className: 'classify__state' }, resolved ? 'Recommended classification' : 'Narrowing\u2026'),
        React.createElement('div', { className: 'classify__code' },
          resolved ? cls.code : cls.group + ' group',
          React.createElement('span', { className: 'muted' }, resolved ? cls.points + ' pts' : cls.groupName.split(' ')[0])
        )
      ),
      React.createElement('div', { className: 'classify__ring' },
        React.createElement('svg', { width: 38, height: 38, viewBox: '0 0 38 38' },
          React.createElement('circle', { className: 'track', cx: 19, cy: 19, r: 16, fill: 'none', strokeWidth: 3 }),
          React.createElement('circle', { className: 'fill', cx: 19, cy: 19, r: 16, fill: 'none', strokeWidth: 3,
            strokeDasharray: c, strokeDashoffset: c * (1 - (cls.confidence || 0.6)) })
        ),
        React.createElement('div', { className: 'classify__pct' }, pct + '%')
      )
    );
  }

  function App() {
    const [record, setRecord] = useState({});
    const [answers, setAnswers] = useState({});
    const [stepIndex, setStepIndex] = useState(0);
    const [draft, setDraft] = useState(() => initialAnswer(D.STEPS[0], {}));
    const [reviewing, setReviewing] = useState(false);
    const [editingReturn, setEditingReturn] = useState(false);
    const [flashes, setFlashes] = useState(new Set());
    const [toast, setToast] = useState(null);
    const threadRef = useRef(null);
    const docRef = useRef(null);

    const step = D.STEPS[stepIndex];

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

    const cls = useMemo(() => D.computeClassification(reviewing ? record : liveRecord), [liveRecord, record, reviewing]);

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
      if (next >= D.STEPS.length) {
        setReviewing(true);
      } else {
        setStepIndex(next);
        const ns = D.STEPS[next];
        setDraft(answers[ns.id] !== undefined ? answers[ns.id] : initialAnswer(ns, newRecord));
      }
    }

    function goBack() {
      if (stepIndex === 0) return;
      const prev = stepIndex - 1;
      setStepIndex(prev);
      const ps = D.STEPS[prev];
      setDraft(answers[ps.id] !== undefined ? answers[ps.id] : initialAnswer(ps, record));
    }

    function editStep(stepId) {
      const idx = D.STEPS.findIndex(s => s.id === stepId);
      if (idx < 0) return;
      setReviewing(false);
      setEditingReturn(true);
      setStepIndex(idx);
      setDraft(answers[stepId] !== undefined ? answers[stepId] : initialAnswer(D.STEPS[idx], record));
    }

    function jumpToExchange(idx) {
      setReviewing(false);
      setEditingReturn(false);
      setStepIndex(idx);
      const s = D.STEPS[idx];
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
      setDraft(initialAnswer(D.STEPS[0], {})); setReviewing(false); setEditingReturn(false);
    }

    const phaseIdx = reviewing ? D.PHASES.length - 1 : step.phase;
    const answeredSteps = D.STEPS.slice(0, stepIndex);

    return React.createElement('div', { className: 'app' },
      // ---------- LEFT ----------
      React.createElement('div', { className: 'convo' },
        React.createElement(Header, { phaseIdx }),
        reviewing
          ? React.createElement(ReviewState, { record, cls, onExport: exportAs, onRestart: restart })
          : React.createElement('div', { className: 'thread', ref: threadRef },
              answeredSteps.map((s, i) =>
                React.createElement(Exchange, {
                  key: s.id, step: s, record, answer: answers[s.id],
                  onEdit: () => jumpToExchange(i)
                })),
              React.createElement(ActiveQuestion, {
                step, record, draft, setDraft, onCommit: commit, onBack: goBack,
                canBack: stepIndex > 0 && !editingReturn, isLast: stepIndex === D.STEPS.length - 1
              }),
              editingReturn && React.createElement('div', { style: { marginLeft: 43, marginTop: 14 } },
                React.createElement('button', { className: 'btn btn--ghost', style: { paddingLeft: 0 }, onClick: () => { setEditingReturn(false); setReviewing(true); } },
                  '\u2190 Back to review without changes'))
            )
      ),
      // ---------- RIGHT ----------
      React.createElement('div', { className: 'preview' },
        React.createElement('div', { className: 'preview__head' },
          React.createElement('div', { className: 'preview__label' },
            React.createElement('span', { className: 'live-dot' }),
            reviewing ? 'Final document' : 'Building live'),
          React.createElement('div', { className: 'preview__spacer' }),
          React.createElement(ClassifyBadge, { cls })
        ),
        React.createElement('div', { className: 'doc-scroll', ref: docRef },
          React.createElement(DocumentPane, {
            record: reviewing ? record : liveRecord, cls, flashes, reviewing, onEditStep: editStep
          })
        )
      ),
      // ---------- toast ----------
      React.createElement('div', { className: 'toast' + (toast ? ' is-show' : '') },
        React.createElement(Icon, { path: D.I.check, size: 17 }),
        React.createElement('span', null, toast || ''))
    );
  }

  ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));
})();
