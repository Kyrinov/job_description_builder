/* ============================================================
   JD Builder — main application
   ============================================================ */
import { useState, useRef, useEffect, useMemo } from 'react';
import { STEPS, PHASES, I, OG_LEVELS, computeClassification, accumulateSignals } from './data.jsx';
import { Icon, initialAnswer, answerValid } from './components.jsx';
import { Header, Exchange, ActiveQuestion, ReviewState } from './conversation.jsx';
import { DocumentPane } from './document.jsx';

const FLASH = {
  title: 'title', branch: 'title', reports: 'title',
  reports_to_military: 'title',
  supervises: 'summary',
  summary: 'summary',
  qb_work_output_type: 'level', qb_work_audience: 'level',
  qb_knowledge_specialization: 'level', qb_policy_interpretation: 'level',
  noc_confirm: 'level',
  og_confirm: 'level',
  og_level: 'level',
  duties: 'duties', quals: 'quals',
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
  const [wd_id, setWdId] = useState(() => {
    try { return localStorage.getItem('jd-builder-v2-wd-id') || null; } catch { return null; }
  });
  const [nocCandidates, setNocCandidates] = useState([]);
  const [nocLoading, setNocLoading] = useState(false);
  const [ogCandidates, setOgCandidates] = useState([]);
  const [ogLoading, setOgLoading] = useState(false);
  const [ogAlert, setOgAlert] = useState(null);
  const [orphanFlags, setOrphanFlags] = useState([]);
  const [amendmentNotes, setAmendmentNotes] = useState({});    // { [sectionKey]: string } — saved notes from API
  const [amendmentPanels, setAmendmentPanels] = useState({});  // { [sectionKey]: { open, text, saved } } — UI panel state
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

  // Persist wd_id on change so a page refresh can resume the same WD row
  useEffect(() => {
    try {
      if (wd_id) localStorage.setItem('jd-builder-v2-wd-id', wd_id);
    } catch {}
  }, [wd_id]);

  // Orphan check: fire automatically when reviewing becomes true and duties + OG are present (JD-04)
  // Silent advisory check — non-blocking; EC positions always return 0 flags (no exclusions defined)
  useEffect(() => {
    if (!reviewing || !wd_id || !record.duties?.length || !record.confirmed_og) return;
    fetch(`/api/wd/${wd_id}/orphan_check`, { method: 'POST' })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        if (data.flagged && data.flagged.length > 0) {
          setRecord(prev => ({
            ...prev,
            duties: (prev.duties || []).map(d => {
              const flag = data.flagged.find(f => f.duty_id === d.id);
              return flag
                ? { ...d, orphan: true, orphan_rationale: flag.orphan_rationale }
                : d;
            }),
          }));
        }
        setOrphanFlags(data.flagged || []);
      })
      .catch(() => {}); // silent on failure — orphan check is advisory only
  }, [reviewing, wd_id]);

  // Amendment notes hydration: load saved notes from audit_log when review state begins
  // (AMEND-01). Mirrors the orphan_check useEffect pattern above.
  useEffect(() => {
    if (!wd_id || !reviewing) return;
    fetch(`/api/wd/${wd_id}/amendments`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.notes) setAmendmentNotes(data.notes);
      })
      .catch(() => {});
  }, [wd_id, reviewing]);

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
    const newAnswers = { ...answers, [step.id]: draft };
    setAnswers(newAnswers);
    flash(FLASH[step.id]);

    // WD persistence — first commit creates row; subsequent commits patch.
    // The backend WorkDescription model has classification-level fields
    // (confirmed_noc, confirmed_og, og_level, reports_to_military, jes_scores,
    // jes_total_points) at the root — NOT nested in `record`. Mirror them up
    // here so the stored WD has the data the JES endpoint reads via
    // require_og_confirmed (otherwise /api/jes/score 409s even after og_level
    // is committed in the local record).
    //
    // Return a promise that resolves with the persisted wd_id so downstream
    // triggers (NOC / OG / JES) can chain off the persistence and avoid the
    // 409 race where the read races the write.
    const wdPayload = {
      record: newRecord,
      answers: newAnswers,
      step_index: stepIndex,
    };
    ['confirmed_noc', 'confirmed_og', 'og_level', 'reports_to_military',
     'jes_scores', 'jes_total_points'].forEach(k => {
      if (k in newRecord) wdPayload[k] = newRecord[k];
    });
    // Persist duties with provenance when committing the duties step (JD-02)
    if (step.id === 'duties' && newRecord.duties) {
      wdPayload.duties = newRecord.duties;
    }
    // Persist qualification when committing the quals step (QUAL-01/02)
    if (step.id === 'quals' && newRecord.quals) {
      wdPayload.qualification = {
        ...newRecord.quals,
        source: 'advisor-edited',
        last_modified: new Date().toISOString(),
      };
    }
    let wdPromise;
    if (!wd_id) {
      wdPromise = fetch('/api/wd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(wdPayload),
      })
        .then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(data => {
          setWdId(data.id);
          try { localStorage.setItem('jd-builder-v2-wd-id', data.id); } catch {}
          return data.id;
        });
    } else {
      wdPromise = fetch(`/api/wd/${wd_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(wdPayload),
      })
        .then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(() => wd_id);
    }
    wdPromise.catch(() => {});

    // NOC pipeline trigger — fires once when the work summary step is committed
    if (step.id === 'summary') {
      setNocLoading(true);
      setNocCandidates([]);
      fetch('/api/noc/map', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ work_description: newRecord.summary }),
      })
        .then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(data => {
          setNocCandidates(data.candidates || []);
          setNocLoading(false);
        })
        .catch(() => { setNocLoading(false); });
    }

    // OG pipeline trigger — fires once when noc_confirm step is committed
    if (step.id === 'noc_confirm') {
      setOgLoading(true);
      setOgCandidates([]);
      setOgAlert(null);
      const signalTally = accumulateSignals(answers);
      const confirmedNoc = newRecord.confirmed_noc || {};
      fetch('/api/og/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          confirmed_noc_code: typeof confirmedNoc === 'string' ? confirmedNoc : (confirmedNoc.noc_code || ''),
          work_description: newRecord.summary || '',
          signal_tally: (signalTally && signalTally.tally) || {},
        }),
      })
        .then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(data => {
          setOgCandidates(data.candidates || []);
          setOgAlert(data.asec_alert || null);
          setOgLoading(false);
        })
        .catch(() => { setOgLoading(false); });
    }

    // JES pipeline trigger — fires after duties are committed so EC scoring
    // has actual duty content. Chains off wdPromise so og_level + confirmed_og
    // are already persisted before /api/jes/score reads them.
    if (step.id === 'duties') {
      const confirmedOg = newRecord.confirmed_og || {};
      const ogCode = typeof confirmedOg === 'string' ? confirmedOg : (confirmedOg.og_code || '');
      const ogLevel = newRecord.og_level || 0;
      const duties = (newRecord.duties || []).map(d => d.polished || d.text || '');

      if (ogCode && ogLevel) {
        wdPromise
          .then((id) => fetch('/api/jes/score', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ wd_id: id, og_code: ogCode, og_level: ogLevel, duties }),
          }))
          .then(r => r.ok ? r.json() : Promise.reject(r.status))
          .then(data => {
            setRecord(prev => ({
              ...prev,
              jes_scores: data.factors || [],
              jes_total_points: data.total_points ?? null,
              jes_standard_name: data.standard_name || '',
              jes_is_ec: data.is_ec ?? false,
            }));
            // Persist jes_scores on the WD record so a refresh restores them
            const persistId = wd_id || data.wd_id;
            if (persistId) {
              return fetch('/api/wd/' + persistId, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  jes_scores: data.factors || [],
                  jes_total_points: data.total_points ?? null,
                }),
              });
            }
          })
          .catch(() => {
            setToast('JES scoring could not complete — export may be unavailable. Try re-selecting the OG level.');
            setTimeout(() => setToast(null), 7000);
          });
      }
    }

    if (editingReturn) {
      // Invalidate NOC + OG state when re-answering any Work Type phase step
      if (step.phase === 1) {
        setNocCandidates([]);
        setNocLoading(false);
        setOgCandidates([]);
        setOgLoading(false);
        setOgAlert(null);
        setAnswers(prev => {
          const updated = { ...prev };
          delete updated['noc_confirm'];
          delete updated['og_confirm'];
          delete updated['og_level'];
          return updated;
        });
      }
      // Invalidate OG state when re-answering noc_confirm (NOC changed)
      if (step.id === 'noc_confirm') {
        setOgCandidates([]);
        setOgLoading(false);
        setOgAlert(null);
        setAnswers(prev => {
          const updated = { ...prev };
          delete updated['og_confirm'];
          delete updated['og_level'];
          return updated;
        });
      }
      // Invalidate JES state when re-answering og_confirm or og_level
      // (the new og_level commit will trigger a fresh /api/jes/score fetch
      //  which will replace these fields, so we clear them to avoid stale
      //  scorecards in the preview while the re-fetch is in flight).
      if (step.id === 'og_confirm' || step.id === 'og_level') {
        setRecord(prev => {
          const updated = { ...prev };
          delete updated.jes_scores;
          delete updated.jes_total_points;
          delete updated.jes_standard_name;
          delete updated.jes_is_ec;
          return updated;
        });
      }
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

  async function exportAs(kind) {
    if (kind === 'clipboard') {
      setToast('Job description copied to clipboard');
      setTimeout(() => setToast(null), 2600);
      return;
    }
    if (!wd_id) {
      setToast('Save your work description first before exporting.');
      setTimeout(() => setToast(null), 2600);
      return;
    }
    if (!record.confirmed_og || !record.og_level) {
      setToast('Complete the OG group and level steps before exporting.');
      setTimeout(() => setToast(null), 5000);
      return;
    }
    const isPdf = kind === 'PDF';
    const endpoint = isPdf
      ? `/api/wd/${wd_id}/export/pdf`
      : `/api/wd/${wd_id}/export/docx`;
    const ext = isPdf ? 'pdf' : 'docx';
    const filename = `${(record.title || 'work-description').toLowerCase().replace(/\s+/g, '-')}.${ext}`;
    try {
      const resp = await fetch(endpoint, { method: 'POST' });
      if (resp.status === 501) {
        const data = await resp.json();
        setToast(data.detail || 'PDF export unavailable. Download DOCX instead.');
        setTimeout(() => setToast(null), 5000);
        return;
      }
      if (!resp.ok) {
        let detail = `HTTP ${resp.status}`;
        try {
          const data = await resp.json();
          if (data && data.detail != null) {
            const d = data.detail;
            if (typeof d === 'string') {
              detail = `${resp.status}: ${d}`;
            } else if (typeof d === 'object') {
              const msg = d.message || d.error || JSON.stringify(d);
              detail = `${resp.status}: ${msg}`;
            } else {
              detail = `${resp.status}: ${String(d)}`;
            }
          }
        } catch (_e) { /* non-JSON body — keep status code only */ }
        setToast(`Export failed — ${detail}`);
        setTimeout(() => setToast(null), 5000);
        return;
      }
      const blob = await resp.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = href;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(href);
    } catch (_err) {
      setToast('Export failed. Please try again.');
      setTimeout(() => setToast(null), 2600);
    }
  }

  function restart() {
    setRecord({}); setAnswers({}); setStepIndex(0);
    setDraft(initialAnswer(STEPS[0], {})); setReviewing(false); setEditingReturn(false);
    setWdId(null); setNocCandidates([]); setNocLoading(false);
    setOgCandidates([]); setOgLoading(false); setOgAlert(null);
    try { localStorage.removeItem('jd-builder-v2-wd-id'); } catch {}
  }

  // JES override handler — fires POST /api/jes/override/{wd_id}/{factor_name}
  // when an advisor enters a manual degree for a failed factor (degree === -1).
  // Updates record.jes_scores and record.jes_total_points in place from response.
  function handleJesOverride(factorName, degree) {
    if (!wd_id) return;
    fetch(`/api/jes/override/${wd_id}/${encodeURIComponent(factorName)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ degree, rationale: 'Advisor override via UI' }),
    })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        setRecord(prev => ({
          ...prev,
          jes_scores: (prev.jes_scores || []).map(f =>
            f.factor_name === factorName
              ? { ...f, degree: data.degree, points: data.points, advisor_adjusted: true }
              : f
          ),
          jes_total_points: data.jes_total_points ?? prev.jes_total_points,
        }));
      })
      .catch(() => {});
  }

  // Amendment panel open/close/text toggle. Three call modes:
  //   onAmendToggle(key)               — toggle panel open/close
  //   onAmendToggle(key, null)         — discard (close + reset to saved)
  //   onAmendToggle(key, "new text")   — text update while panel is open
  // The Sec component in document.jsx calls onAmendToggle(key) when the amend
  // button is clicked and onAmendToggle(key, e.target.value) on textarea change.
  function handleAmendToggle(sectionKey, textOrNull) {
    setAmendmentPanels(prev => {
      const cur = prev[sectionKey] || { open: false, text: '', saved: null };
      if (textOrNull === null) {
        // Discard — close and reset to saved value (or empty if no saved note)
        return { ...prev, [sectionKey]: { ...cur, open: false, text: cur.saved || '' } };
      }
      if (typeof textOrNull === 'string' && cur.open) {
        // Text update while panel is open
        return { ...prev, [sectionKey]: { ...cur, text: textOrNull } };
      }
      // Toggle open/close; prefill textarea with the saved value (if any)
      return { ...prev, [sectionKey]: { ...cur, open: !cur.open, text: cur.saved || '' } };
    });
  }

  // Save amendment note via POST /api/wd/{id}/amendments.
  // On success: set the saved note in amendmentNotes, close the panel, fire toast.
  // On failure: fire an error toast; panel state preserved so user can retry.
  const SECTION_NAMES = {
    id: 'Position Identification',
    ov: 'Position Overview',
    du: 'Key Responsibilities',
    cls: 'Classification & Evaluation',
    q: 'Essential Qualifications',
    drf: 'Defence Results Linkage',
  };
  function handleAmendSave(sectionKey, text) {
    if (!wd_id || !text.trim()) return;
    fetch(`/api/wd/${wd_id}/amendments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ section: sectionKey, comment: text }),
    })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(() => {
        setAmendmentNotes(prev => ({ ...prev, [sectionKey]: text }));
        setAmendmentPanels(prev => ({
          ...prev,
          [sectionKey]: { open: false, text, saved: text },
        }));
        setToast(`Note saved for ${SECTION_NAMES[sectionKey] || sectionKey}.`);
        setTimeout(() => setToast(null), 3500);
      })
      .catch(() => {
        setToast('Could not save note. Try again.');
        setTimeout(() => setToast(null), 3500);
      });
  }

  const phaseIdx = reviewing ? PHASES.length - 1 : step.phase;
  const answeredSteps = STEPS.slice(0, stepIndex);

  // cfgOverride injects live NOC candidates into the noc_confirm step input,
  // OG candidates + AS/EC disambiguation alert into og_confirm, OG_LEVELS
  // range into og_level, and confirmed NOC code into the duties step so
  // DutyBuilder can fetch verbatim duties from /api/noc/{noc_code}/duties.
  const stepCfgOverride = !reviewing && step
    ? (step.input.type === 'noc_confirm'
        ? { ...step.input, candidates: nocCandidates, loading: nocLoading }
        : step.input.type === 'og_confirm'
          ? { ...step.input, candidates: ogCandidates, loading: ogLoading, asec_alert: ogAlert }
          : step.input.type === 'og_level'
            ? { ...step.input, levels: record.confirmed_og
                  ? OG_LEVELS[record.confirmed_og.og_code] || []
                  : [] }
            : step.id === 'duties'
              ? { ...step.input, noc_code: record.confirmed_noc
                    ? (typeof record.confirmed_noc === 'string'
                        ? record.confirmed_noc
                        : record.confirmed_noc?.noc_code || null)
                    : null }
              : undefined)
    : undefined;

  return (
    <div className="app">
      {/* ---------- LEFT ---------- */}
      <div className="convo">
        <Header phaseIdx={phaseIdx} />
        {reviewing
          ? <ReviewState record={record} cls={cls} onExport={exportAs} onRestart={restart} amendmentNotes={amendmentNotes} />
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
                cfgOverride={stepCfgOverride}
                dataTestid={`jump-${stepIndex}`}
                dataStepId={step.id}
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
            onJesOverride={handleJesOverride}
            amendmentNotes={amendmentNotes} amendmentPanels={amendmentPanels}
            onAmendToggle={handleAmendToggle} onAmendSave={handleAmendSave}
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
