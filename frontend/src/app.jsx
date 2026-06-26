/* ============================================================
   JD Builder — main application
   ============================================================ */
import { useState, useRef, useEffect, useMemo } from 'react';
import { STEPS, PHASES, I, OG_LEVELS, OG_DUTY_TIPS, computeClassification, accumulateSignals, getVisibleSteps, isStepVisible, MANAGER_SKIP_STEPS, fetchSjds } from './data.jsx';
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
  qb_sector_gate: 'level', qb_health_social_cluster: 'level',
  qb_legal_cluster: 'level', qb_technical_cluster: 'level',
  qb_education_cluster: 'level', qb_programme_admin_cluster: 'level',
  noc_confirm: 'level',
  og_confirm: 'level',
  og_level_questions: 'level',
  og_level: 'level',
  // Phase 26 (ORG-02): flash keys for the new document-preview Secs.
  // 'org_ctx' and 'csr' map to the new SECTION_NAMES entries below.
  org_context: 'org_ctx',
  client_service_results: 'csr',
  // Phase 27 (RESP-02): flash key for the new Responsibilities Sec
  // (rendered above Key Responsibilities in document.jsx).
  responsibilities_narrative: 'resp_narrative',
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

// Phase 28 (MGR-01): RoleSelector — first-load screen that lets the user
// declare their role. The selection persists to localStorage under
// 'jd-builder-v2-role' and launches the matching track. user_role is NEVER
// sent to the backend (D-28-01 / D-28-03 — it lives in localStorage only).
function RoleSelector({ onSelect }) {
  return (
    <div className="land" data-testid="role-selector">
      {/* top bar */}
      <div className="land__top">
        <div className="brand">
          <div className="brand__mark">
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M12 3l1.9 4.6L18.5 9.5 13.9 11.4 12 16l-1.9-4.6L5.5 9.5l4.6-1.9z" fill="currentColor"/></svg>
          </div>
          <div>
            <div className="brand__name">JD Builder</div>
            <div className="brand__sub">Guided work-description assistant</div>
          </div>
        </div>
        <div className="brand__dept">National Defence · Défense nationale</div>
      </div>

      {/* hero */}
      <div className="hero">
        <span className="hero__eyebrow">Standardized Work Descriptions</span>
        <h1 className="hero__title">Build a classification-ready job description, <em>one question at a time.</em></h1>
        <p className="hero__sub">JD Builder turns plain answers into a well-structured, standardized work description — mapped to the right occupational group and level, linked to Defence results, and traceable to source. No HR jargon required.</p>

        {/* gate */}
        <div className="gate__q">First, which best describes you?</div>
        <div className="paths">

          {/* Manager path */}
          <button className="path path--manager" data-testid="role-manager" onClick={() => onSelect('manager')}>
            <span className="path__tag">Most guidance</span>
            <div className="path__head">
              <div className="path__icon">
                <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="6.5" r="3.2" fill="none" stroke="currentColor" strokeWidth="1.7"/><path d="M3.5 17c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>
              </div>
              <div>
                <div className="path__kicker">For the hiring side</div>
                <div className="path__title">I'm a hiring manager</div>
              </div>
            </div>
            <p className="path__desc">You know the role you need to fill. We'll handle the classification, wording, and standards behind the scenes — you just answer in plain language.</p>
            <ul className="path__feats">
              <li>
                <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10l4 4 8-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                <span>Plain-language questions, no classification expertise needed</span>
              </li>
              <li>
                <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10l4 4 8-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                <span>Your words refined into formal duty statements</span>
              </li>
              <li>
                <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10l4 4 8-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                <span>Group &amp; level suggested for you as you go</span>
              </li>
            </ul>
            <div className="path__cta">
              <span>Start guided build</span>
              <span className="arrow">
                <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11M11 5l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </span>
            </div>
          </button>

          {/* Advisor path */}
          <button className="path path--advisor" data-testid="role-advisor" onClick={() => onSelect('advisor')}>
            <span className="path__tag">Full control</span>
            <div className="path__head">
              <div className="path__icon">
                <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="2.6" fill="none" stroke="currentColor" strokeWidth="1.6"/><path d="M10 2v2.5M10 15.5V18M18 10h-2.5M4.5 10H2M15.7 4.3l-1.8 1.8M6.1 13.9l-1.8 1.8M15.7 15.7l-1.8-1.8M6.1 6.1L4.3 4.3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
              </div>
              <div>
                <div className="path__kicker">For HR classification</div>
                <div className="path__title">I'm a classification advisor</div>
              </div>
            </div>
            <p className="path__desc">You own the standards. Move faster with editable rationale, visible factor-by-factor evaluation, and override control at every step.</p>
            <ul className="path__feats">
              <li>
                <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10l4 4 8-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                <span>Adjust degrees and override the suggested level</span>
              </li>
              <li>
                <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10l4 4 8-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                <span>Full JES factor breakdown &amp; point rationale</span>
              </li>
              <li>
                <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10l4 4 8-9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                <span>Source citations on by default for defensible files</span>
              </li>
            </ul>
            <div className="path__cta">
              <span>Open advisor workspace</span>
              <span className="arrow">
                <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11M11 5l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </span>
            </div>
          </button>

        </div>
      </div>

      {/* footer */}
      <div className="land__foot">
        <div className="land__foot-item">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3l6 2v5c0 4-2.6 6.4-6 7.5C6.6 16.4 4 14 4 10V5z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/></svg>
          <span>Aligned to the <b>TBS Job Evaluation Standards</b></span>
        </div>
        <div className="land__foot-item">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M16 4C9 4 4 8 4 15c5 1 12-2 12-11z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/><path d="M7 13c3-3 6-4 8-4.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>
          <span>Linked to the <b>DND Departmental Results Framework</b></span>
        </div>
        <div className="land__foot-spacer" />
        <button className="land__resume" onClick={() => onSelect('advisor')}>
          Continue without selecting
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11M11 5l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </button>
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
  // Phase 26 (ORG-01): resume-by-last-answered. The STEPS array grows over
  // time (Phases 15..26 each appended steps); an integer stepIndex persisted
  // in localStorage would land the advisor on the WRONG step after a STEPS
  // insertion. Instead, derive the resume position from which record keys
  // are populated — the advisor lands on the step AFTER the last answered
  // one. STEP_RECORD_KEY maps each step id to the record key its `apply`
  // writes (e.g. noc_confirm writes to confirmed_noc; og_confirm writes to
  // confirmed_og). duties is a list, so we treat length > 0 as answered.
  // Worst case on attacker-controlled localStorage: advisor lands on the
  // wrong step (T-26-04 mitigation — non-destructive).
  //
  // Phase 28 (MGR-01): userRole MUST be declared BEFORE stepIndex so its
  // lazy initializer can read userRole without a Temporal Dead Zone error.
  // The reduce below skips MANAGER_SKIP_STEPS in manager mode to keep the
  // resume position on a visible step.
  const [userRole, setUserRole] = useState(() => {
    try { return localStorage.getItem('jd-builder-v2-role') || null; } catch { return null; }
  });
  const [stepIndex, setStepIndex] = useState(() => {
    try {
      const raw = localStorage.getItem('jd-builder-v2-record');
      if (!raw) return 0;
      const rec = JSON.parse(raw);
      const STEP_RECORD_KEY = {
        title: 'title', branch: 'branch', reports: 'reports',
        reports_to_military: 'reports_to_military', supervises: 'supervises',
        summary: 'summary', qb_work_output_type: 'qb_work_output_type',
        qb_work_audience: 'qb_work_audience',
        qb_knowledge_specialization: 'qb_knowledge_specialization',
        qb_policy_interpretation: 'qb_policy_interpretation',
        qb_sector_gate: 'qb_sector_gate',
        qb_health_social_cluster: 'qb_health_social_cluster',
        qb_legal_cluster: 'qb_legal_cluster',
        qb_technical_cluster: 'qb_technical_cluster',
        qb_education_cluster: 'qb_education_cluster',
        qb_programme_admin_cluster: 'qb_programme_admin_cluster',
        noc_confirm: 'confirmed_noc',
        og_confirm: 'confirmed_og',
        og_level_questions: 'og_level_questions',
        og_level: 'og_level',
        org_context: 'org_context',
        client_service_results: 'client_service_results',
        // Phase 27 (RESP-01): responsibilities_narrative is a typed root
        // field on WorkDescription; its record key is the same as its
        // step id (apply writes to record.responsibilities_narrative).
        // stepIndex resume-by-last-answered inherits this entry for free
        // — STEPS.reduce walks STEP_RECORD_KEY[s.id] to find last answered.
        responsibilities_narrative: 'responsibilities_narrative',
        duties: 'duties',
        quals: 'quals',
      };
      const lastAnswered = STEPS.reduce((best, s, i) => {
        // Phase 28 (MGR-03): in manager mode, skip classification-internal
        // steps so the resume-by-last-answered reduce never lands the user
        // on a hidden step (noc_confirm / og_confirm / og_level_questions /
        // og_level are filtered from getVisibleSteps in manager mode).
        if (userRole === 'manager' && MANAGER_SKIP_STEPS.has(s.id)) return best;
        const key = STEP_RECORD_KEY[s.id];
        if (key === 'duties') {
          return (rec[key] && rec[key].length > 0) ? i : best;
        }
        const answered = key && rec[key] !== undefined && rec[key] !== null;
        return answered ? i : best;
      }, -1);
      return lastAnswered < 0 ? 0 : Math.min(lastAnswered + 1, STEPS.length - 1);
    } catch { return 0; }
  });
  const [draft, setDraft] = useState(() => initialAnswer(STEPS[0], {}));
  const [reviewing, setReviewing] = useState(() => {
    // Phase 26 resume: if the persisted record has qualsVisited:true the user
    // completed the full flow before this reload — re-enter ReviewState instead
    // of landing them on the quals question (step 24).
    try {
      const raw = localStorage.getItem('jd-builder-v2-record');
      if (!raw) return false;
      return !!JSON.parse(raw).qualsVisited;
    } catch { return false; }
  });
  const [editingReturn, setEditingReturn] = useState(false);
  const [flashes, setFlashes] = useState(new Set());
  const [toast, setToast] = useState(null);
  // True while the org-context synthesis call is in flight. Disables the
  // org_context Continue button (shows "Generating…") and the step
  // auto-advances when the call resolves — no second click required.
  const [orgGenerating, setOrgGenerating] = useState(false);
  const [wd_id, setWdId] = useState(() => {
    try { return localStorage.getItem('jd-builder-v2-wd-id') || null; } catch { return null; }
  });
  const [nocCandidates, setNocCandidates] = useState([]);
  const [nocLoading, setNocLoading] = useState(false);
  const [ogCandidates, setOgCandidates] = useState([]);
  const [ogLoading, setOgLoading] = useState(false);
  const [ogAlert, setOgAlert] = useState(null);
  const [orphanFlags, setOrphanFlags] = useState([]);
  // Phase 23 (WG-02): structural duty validation findings, populated after duties commit
  const [dutyHints, setDutyHints] = useState([]);
  const [amendmentNotes, setAmendmentNotes] = useState({});    // { [sectionKey]: string } — saved notes from API
  const [amendmentPanels, setAmendmentPanels] = useState({});  // { [sectionKey]: { open, text, saved } } — UI panel state
  // Phase 22 SJD-02: non-blocking "Browse SJDs" action surfaced after Role phase
  const [sjdPanelOpen, setSjdPanelOpen] = useState(false);
  const [sjdAllEntries, setSjdAllEntries] = useState([]);
  const [sjdOgFilter, setSjdOgFilter] = useState('');
  const [sjdLoading, setSjdLoading] = useState(false);
  // Phase 24 (AUDIT-01): compliance audit findings — populated only by button click, never automatically
  const [auditFindings, setAuditFindings] = useState([]);
  const [auditRunning, setAuditRunning] = useState(false);
  // True once the audit has returned at least one response — distinguishes
  // "not run yet" from "ran clean, zero findings" so a clean run isn't
  // silently indistinguishable from a broken button (no panel either way).
  const [auditRan, setAuditRan] = useState(false);
  // Phase 27 Plan 02 (ELEM-02): seven-elements completeness — hydrated from
  // POST /api/wd/{id}/validate-elements when reviewing becomes true. Drives
  // the soft-gate badge in ReviewState (export buttons stay enabled).
  const [completeness, setCompleteness] = useState(null);
  const threadRef = useRef(null);
  const docRef = useRef(null);

  // Phase 21 OGX-04 (continuation fix): the active step is derived from
  // stepIndex + answers so the user never lands on an invisible cluster
  // step. If the persisted stepIndex points to a step that's no longer
  // visible (e.g., the user changed the sector in a revisit), we snap
  // forward to the first visible step from that position. When no
  // forward step is visible (all remaining steps filtered out), the
  // user is sent to review.
  const activeStepIndex = useMemo(() => {
    if (isStepVisible(STEPS[stepIndex], answers, userRole)) return stepIndex;
    let i = stepIndex;
    while (i < STEPS.length && !isStepVisible(STEPS[i], answers, userRole)) i++;
    return i;
  }, [stepIndex, answers, userRole]);
  const step = STEPS[activeStepIndex];

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

  // Phase 27 Plan 02 (ELEM-02): Seven-elements completeness audit — fetch
  // POST /api/wd/{wd_id}/validate-elements once the user enters Review.
  // Drives the soft-gate N/7 badge in ReviewState. Silent on failure
  // (the badge simply doesn't appear). Mirrors the orphan_check /
  // amendment_notes useEffect pattern.
  useEffect(() => {
    if (!reviewing || !wd_id) return;
    let cancelled = false;
    fetch(`/api/wd/${wd_id}/validate-elements`, { method: 'POST' })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!cancelled && data) setCompleteness(data);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [reviewing, wd_id]);

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

    // SJD-03: warn if confirmed_og changes after an SJD pre-fill. Advisory only —
    // non-blocking per T-22-06; the user can keep working with the new OG. We
    // intentionally do NOT fire when only og_level changes (sjdOgCode comparison
    // is on og_code, so a same-OG level change leaves it inert).
    if (step.id === 'og_confirm' && record.sjd_source) {
      const newOgCode = typeof patch.confirmed_og === 'object'
        ? patch.confirmed_og?.og_code
        : patch.confirmed_og;
      const sjdOgCode = record.sjd_source?.og_code;
      if (newOgCode && sjdOgCode && newOgCode !== sjdOgCode) {
        setToast('Departing from the SJD classification turns this into a new evaluation — the SJD decision no longer applies');
        setTimeout(() => setToast(null), 7000);
      }
    }

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
    // Phase 28 (MGR-03): wd_type travels with every POST/PATCH so the backend
    // can route manager-track WDs through the require_og_confirmed bypass
    // and the DRAFT watermark. user_role is intentionally NOT sent (D-28-01
    // / D-28-03) — it lives in localStorage only.
    wdPayload.wd_type = userRole === 'manager' ? 'manager' : 'advisor';
    ['confirmed_noc', 'confirmed_og', 'og_level', 'reports_to_military',
     'jes_scores', 'jes_total_points', 'org_context',
     'responsibilities_narrative'].forEach(k => {
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

      // Phase 23 (WG-02): non-blocking duty validation — chains off wdPromise so
      // duties are persisted before the POST fires. setDutyHints on success, silent on failure.
      // Fires on EVERY duties commit regardless of OG/level state — advisors can
      // enter and commit duties before confirming classification.
      wdPromise
        .then(id => fetch(`/api/wd/${id}/validate-duties`, { method: 'POST' }))
        .then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(data => setDutyHints(data.findings || []))
        .catch(() => {}); // non-blocking; silent on failure
    }

    // Org-context synthesis — fires when the org_context step is committed.
    // step.apply already wrote a joined-plain-text fallback to org_context; this
    // upgrades it to fluid LLM prose built from branch + reports + the two fields.
    // Chains off wdPromise so the WD row exists before we PATCH the prose back.
    // Non-blocking: on any failure the fallback string stays and no error shows.
    if (step.id === 'org_context') {
      // In the forward flow we gate: show "Generating…", then auto-advance
      // when the call resolves. In edit-return mode we still regenerate the
      // prose but let the editingReturn block below send the user to review.
      const gated = !editingReturn;
      const parts = newRecord.org_context_parts || {};
      setToast('Generating organizational context…');
      if (gated) setOrgGenerating(true);
      // Hard client-side bound so the call can never hang on a slow upstream
      // (or a misbehaving proxy/connection beyond the server's 30s timeout).
      // The plain-text fallback is already in record.org_context, so aborting
      // simply keeps it — no error surfaces to the advisor.
      const orgCtl = new AbortController();
      const orgTimer = setTimeout(() => orgCtl.abort(), 30000);

      // Advance to the next visible step. Deferred until the synthesis
      // resolves so the step "just moves forward" once the prose is ready,
      // rather than gating behind a second Continue click.
      const advance = () => {
        let i = stepIndex + 1;
        while (i < STEPS.length && !isStepVisible(STEPS[i], newAnswers)) i++;
        if (i >= STEPS.length) {
          setReviewing(true);
        } else {
          setStepIndex(i);
          const ns = STEPS[i];
          setDraft(newAnswers[ns.id] !== undefined ? newAnswers[ns.id] : initialAnswer(ns, newRecord));
        }
      };

      wdPromise
        .then(id => fetch('/api/org-context/synthesize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            branch: newRecord.branch || '',
            reports: newRecord.reports || '',
            work_stream: parts.work_stream || '',
            additional: parts.additional || '',
          }),
          signal: orgCtl.signal,
        })
          .then(r => r.ok ? r.json() : Promise.reject(r.status))
          .then(data => ({ id, data })))
        .then(({ id, data }) => {
          if (data && data.prose) {
            setRecord(prev => ({ ...prev, org_context: data.prose }));
            setToast('Organizational context generated');
            if (id) {
              return fetch(`/api/wd/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ org_context: data.prose }),
              }).catch(() => {});
            }
          } else {
            // No prose came back — keep the joined-text fallback, but tell
            // the advisor so the step never looks like it silently stalled.
            setToast('Using the text you entered for organizational context');
          }
        })
        .catch(() => { setToast('Using the text you entered for organizational context'); })
        .finally(() => {
          clearTimeout(orgTimer);
          if (gated) {
            setOrgGenerating(false);
            advance();                            // ← auto-advance once complete
          }
          setTimeout(() => setToast(null), 2600);
        });
      // Forward flow: the promise handles advancement, so skip the synchronous
      // advance below. Edit-return flow falls through to the editingReturn
      // block, which routes the user back to review.
      if (gated) return;
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
      // Phase 23 (WG-02): clear stale duty hints when advisor re-enters duties step in editing mode
      if (step.id === 'duties') {
        setDutyHints([]);
      }
      setEditingReturn(false);
      setReviewing(true);
      return;
    }
    // Phase 21 OGX-04 (continuation fix): skip cluster questions whose sector
    // was not selected. computeNextVisible walks forward from `start` to the
    // first visible step, falling through to STEPS.length if all remaining
    // steps are invisible (drives the user to review).
    const computeNextVisible = (start) => {
      let i = start;
      while (i < STEPS.length && !isStepVisible(STEPS[i], newAnswers)) i++;
      return i;
    };
    const next = computeNextVisible(stepIndex + 1);
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
    // Phase 21 OGX-04: skip invisible cluster questions when going back too.
    let prev = stepIndex - 1;
    while (prev > 0 && !isStepVisible(STEPS[prev], answers)) prev--;
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
    if (userRole !== 'manager' && kind !== 'json' && kind !== 'csv'
        && (!record.confirmed_og || !record.og_level)) {
      setToast('Complete the OG group and level steps before exporting.');
      setTimeout(() => setToast(null), 5000);
      return;
    }
    let endpoint, ext;
    if (kind === 'PDF') {
      endpoint = `/api/wd/${wd_id}/export/pdf`; ext = 'pdf';
    } else if (kind === 'json') {
      endpoint = `/api/wd/${wd_id}/export/json`; ext = 'json';
    } else if (kind === 'csv') {
      endpoint = `/api/wd/${wd_id}/export/csv`; ext = 'csv';
    } else {
      endpoint = `/api/wd/${wd_id}/export/docx`; ext = 'docx';
    }
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
        const kindLabel = kind === 'json' ? 'JSON' : kind === 'csv' ? 'CSV' : 'Export';
        setToast(`${kindLabel} export failed — ${detail}. Try again or contact support.`);
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
      setTimeout(() => URL.revokeObjectURL(href), 0);
      const successMsg = kind === 'json'
        ? 'Structured data downloaded (JSON)'
        : kind === 'csv'
          ? 'Structured data downloaded (CSV)'
          : `${ext.toUpperCase()} exported`;
      setToast(successMsg);
      setTimeout(() => setToast(null), 2600);
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
    // Clear the role too so the gate at userRole===null re-renders the
    // RoleSelector landing page, and purge the persisted session so a reload
    // does not resume the work description we just discarded.
    setUserRole(null);
    try {
      localStorage.removeItem('jd-builder-v2-wd-id');
      localStorage.removeItem('jd-builder-v2-record');
      localStorage.removeItem('jd-builder-v2-role');
    } catch {}
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
    // Phase 26 (ORG-02): new section keys surfaced in the document preview
    // Secs (org_context + client_service_results). Used by the amendment
    // toast ("Note saved for Organizational Context.") — same pattern as
    // the existing id/ov/du/cls/q/drf entries.
    org_ctx: 'Organizational Context',
    csr: 'Client Service Results',
    // Phase 27 (RESP-02): 'Responsibilities' title for the new Sec — same
    // title string used by the document.jsx Responsibilities Sec and by
    // the amendment toast ("Note saved for Responsibilities.").
    resp_narrative: 'Responsibilities',
    du: 'Key Responsibilities',
    cls: 'Classification & Evaluation',
    q: 'Essential Qualification',
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

  // Phase 24 (AUDIT-01): Manually-triggered compliance audit — button click only.
  // T-24-09 mitigation: never invoked from a useEffect; fires only on Run-audit click.
  function handleRunAudit() {
    if (!wd_id) return;
    setAuditRunning(true);
    fetch(`/api/wd/${wd_id}/audit`, { method: 'POST' })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        setAuditFindings(data.findings || []);
        setAuditRan(true);
        setAuditRunning(false);
      })
      .catch(() => { setAuditRunning(false); });
  }

  // Phase 24 (AUDIT-04): Log advisor Accept / Manual Edit / Skip decision.
  // Fire-and-forget POST; failure is silent. Manual Edit additionally opens the
  // existing Phase 19 amendment panel for the flagged section (AUDIT-05).
  // Accept / Skip (not-applicable) dismiss the finding from the panel so the
  // advisor sees a clear visual confirmation that the decision was recorded.
  function handleAuditDecide(ruleId, section, decision) {
    if (!wd_id) return;
    fetch(`/api/wd/${wd_id}/audit/decide`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rule_id: ruleId, section, decision }),
    }).catch(() => {}); // fire-and-forget; non-blocking
    if (decision === 'manual_edit') {
      handleAmendToggle(section);
    } else if (decision === 'accept' || decision === 'skip') {
      // Remove the addressed finding so the panel reflects the decision.
      setAuditFindings((prev) =>
        prev.filter((f) => !(f.rule_id === ruleId && f.section === section))
      );
    }
  }

  // Phase 22 SJD-02: non-blocking "Browse SJDs" handler. Opens the SJD panel
  // and fetches the list (optionally pre-filtered by current OG group). The
  // action is gated to post-Role phase (step.phase >= 1) at the render site.
  function handleBrowseSjds() {
    if (!wd_id) {
      setToast('Complete at least the first Role step before browsing SJDs.');
      setTimeout(() => setToast(null), 3500);
      return;
    }
    setSjdPanelOpen(true);
    setSjdLoading(true);
    setSjdAllEntries([]);
    fetchSjds(null)
      .then(entries => { setSjdAllEntries(entries); setSjdLoading(false); })
      .catch(() => {
        setToast('Could not load SJDs — try again.');
        setTimeout(() => setToast(null), 3500);
        setSjdLoading(false);
      });
  }

  // Filter change handler — client-side filter (no refetch). The full SJD
  // list is small (10 entries); filtering from sjdAllEntries is instant.
  function handleSjdFilterChange(ogCode) {
    setSjdOgFilter(ogCode);
  }

  // SJD selection handler — POST /api/wd/{id}/sjd-start mirrors the updated
  // WorkDescription (sjd_source, confirmed_og, og_level, duties) into SPA
  // record. Toast is advisory only (4s timeout). On error, an SJD-specific
  // toast tells the user the apply step failed and the panel stays open
  // so they can retry.
  function handleSjdSelect(entry) {
    if (!wd_id) return;
    fetch(`/api/wd/${wd_id}/sjd-start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sjd_number: entry.sjd_number }),
    })
      .then(r => r.ok ? r.json() : Promise.reject(r))
      .then(updatedWd => {
        setRecord(prev => ({
          ...prev,
          sjd_source: updatedWd.sjd_source,
          confirmed_og: updatedWd.confirmed_og,
          og_level: updatedWd.og_level,
          duties: updatedWd.duties,
        }));
        setSjdPanelOpen(false);
        setToast('SJD applied — OG, level, and seed duties pre-filled.');
        setTimeout(() => setToast(null), 4000);
      })
      .catch(() => {
        setToast('Could not apply SJD — try again.');
        setTimeout(() => setToast(null), 3500);
      });
  }

  const phaseIdx = reviewing ? PHASES.length - 1 : step.phase;
  // Phase 21 OGX-04 (bugfix round 3): answeredSteps is filtered to only
  // include steps that were actually answered. Without this filter, the
  // slice includes the 3 invisible cluster questions (legal/technical/
  // education) that the visibility gate in commit() skipped. Their
  // transcripts are `a => a.title`, which throws TypeError when called
  // on `undefined` — React unmounts the tree and the screen goes blank.
  // We preserve the original STEPS index in `originalIndex` so that
  // jumpToExchange(originalIndex) still navigates to the right step.
  const answeredSteps = useMemo(() => {
    const out = [];
    for (let i = 0; i < stepIndex; i++) {
      if (answers[STEPS[i].id] !== undefined) out.push({ s: STEPS[i], originalIndex: i });
    }
    return out;
  }, [stepIndex, answers]);

  // cfgOverride injects live NOC candidates into the noc_confirm step input,
  // OG candidates + AS/EC disambiguation alert into og_confirm, OG_LEVELS
  // range into og_level, and confirmed NOC code into the duties step so
  // DutyBuilder can fetch verbatim duties from /api/noc/{noc_code}/duties.
  //
  // Phase 21 OGX-07 (continuation fix): OgConfirmList now fetches its own
  // subgroup_alert when the user selects NU/SW/ED in the draft (see the
  // useEffect inside that component). This is necessary because the picker
  // must appear DURING the og_confirm step — after the user picks NU in the
  // draft but before they click Continue. The previous app-level useEffect
  // only fired on record.confirmed_og changes, which is too late.
  //
  // The remaining cfg fields we still need to inject are: candidates,
  // loading, asec_alert (from the initial /api/og/classify call), work
  // description (for the re-fetch payload), confirmed_noc (for the re-fetch
  // payload), and wd_id (so the picker can persist selections).
  const stepCfgOverride = !reviewing && step
    ? (step.input.type === 'noc_confirm'
        ? { ...step.input, candidates: nocCandidates, loading: nocLoading }
        : step.input.type === 'og_confirm'
          ? {
              ...step.input,
              candidates: ogCandidates,
              loading: ogLoading,
              asec_alert: ogAlert,
              work_description: record.summary || '',
              confirmed_noc_code: record.confirmed_noc
                ? (typeof record.confirmed_noc === 'string'
                    ? record.confirmed_noc
                    : record.confirmed_noc.noc_code || '')
                : '',
              wd_id: wd_id,
            }
          : step.input.type === 'og_level_questions'
            ? {
                ...step.input,
                og_code: answers.og_confirm?.og_code || record.confirmed_og?.og_code || '',
                sub_group: answers.og_confirm?.sub_group || record.confirmed_og?.sub_group || null,
              }
            : step.input.type === 'og_level'
              ? {
                  ...step.input,
                  levels: record.confirmed_og
                    ? OG_LEVELS[record.confirmed_og.og_code] || []
                    : [],
                  preselect: answers.og_level_questions?.suggested_level ?? null,
                }
              : step.id === 'duties'
                ? {
                    ...step.input,
                    noc_code: record.confirmed_noc
                      ? (typeof record.confirmed_noc === 'string'
                          ? record.confirmed_noc
                          : record.confirmed_noc?.noc_code || null)
                      : null,
                    // Phase 23 (WG-04): per-OG duty tip drawn from OG_DUTY_TIPS.
                    // Suppressed (null) when tip text is under 80 chars or no confirmed_og.
                    og_tip: (() => {
                      const ogCode = typeof record.confirmed_og === 'object'
                        ? (record.confirmed_og?.og_code || '')
                        : (record.confirmed_og || '');
                      const tip = OG_DUTY_TIPS[ogCode] || '';
                      return tip.length >= 80 ? tip : null;
                    })(),
                    // Phase 23 (WG-02): structural duty validation findings.
                    duty_hints: dutyHints,
                  }
                : undefined)
    : undefined;

  // Phase 28 (MGR-01): role gate. When userRole is null (jd-builder-v2-role
// absent from localStorage), the RoleSelector renders in place of the main
// app shell. The selector persists the choice via setUserRole + a localStorage
// setItem; once userRole is non-null, the standard app shell renders.
if (userRole === null) {
  return (
    <RoleSelector
      onSelect={(role) => {
        try { localStorage.setItem('jd-builder-v2-role', role); } catch {}
        setUserRole(role);
      }}
    />
  );
}

return (
    <div className="app">
      {/* ---------- LEFT ---------- */}
      <div className="convo">
        <Header
          phaseIdx={phaseIdx}
          onHome={() => {
            // Guard the destructive reset — a misclick should not wipe an
            // in-progress work description. Skip the prompt on an empty record.
            const hasWork = Object.keys(record).length > 0;
            if (!hasWork || window.confirm('Discard this work description and return to the start page?')) {
              restart();
            }
          }}
        />
        {reviewing
          ? <ReviewState
              record={record}
              cls={cls}
              onExport={exportAs}
              onRestart={restart}
              amendmentNotes={amendmentNotes}
              auditFindings={auditFindings}
              auditRunning={auditRunning}
              auditRan={auditRan}
              onRunAudit={handleRunAudit}
              onAuditDecide={handleAuditDecide}
              completeness={completeness}
              // Phase 28 (MGR-02): thread userRole so ReviewState can hide
              // the "Classified as" checklist line + the entire compliance
              // audit panel in manager mode. Default 'advisor' is enforced
              // by ReviewState's signature — the prop is additive.
              userRole={userRole}
            />
          : (
            <div className="thread" ref={threadRef}>
              {answeredSteps.map(({ s, originalIndex: i }) => (
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
                busy={orgGenerating && step.id === 'org_context'}
                busyLabel="Generating…"
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
              {/* Phase 22 SJD-02: non-blocking "Browse SJDs" action. Surfaced
                  after Role phase (step.phase >= 1) and only when a WD row
                  exists, so we have a target for /api/wd/{id}/sjd-start. */}
              {!reviewing && step.phase >= 1 && wd_id && (
                <div className="sjd-browse-action">
                  <button
                    className="btn-secondary"
                    onClick={handleBrowseSjds}
                    title="Browse DND Standard Job Descriptions"
                  >
                    Browse SJDs
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
          {/* Phase 28 (MGR-02): ClassifyBadge is HIDDEN in manager mode.
              The badge exposes the OG group code (e.g. "EC") and confidence
              ring — classification internals the manager must never see. */}
          {userRole !== 'manager' && <ClassifyBadge cls={cls} />}
        </div>
        <div className="doc-scroll" ref={docRef}>
          <DocumentPane
            record={reviewing ? record : liveRecord} cls={cls} flashes={flashes}
            reviewing={reviewing} onEditStep={editStep}
            onJesOverride={handleJesOverride}
            amendmentNotes={amendmentNotes} amendmentPanels={amendmentPanels}
            onAmendToggle={handleAmendToggle} onAmendSave={handleAmendSave}
            // Phase 28 (MGR-02): thread userRole so DocumentPane can show
            // the classification-team placeholder in the Classification Sec
            // (instead of the OG code / JES scorecard) and suppress the
            // CAF rank advisory in the Position Identification Sec.
            userRole={userRole}
          />
        </div>
      </div>
      {/* ---------- toast ---------- */}
      <div className={`toast${toast ? ' is-show' : ''}`}>
        <Icon path={I.check} size={17} />
        <span>{toast || ''}</span>
      </div>
      {/* ---------- SJD browser panel (Phase 22 SJD-02) ---------- */}
      {sjdPanelOpen && (
        <div className="sjd-panel-overlay" onClick={() => setSjdPanelOpen(false)}>
          <div className="sjd-panel" onClick={e => e.stopPropagation()}>
            <div className="sjd-panel__header">
              <h2>Standard Job Descriptions</h2>
              <button onClick={() => setSjdPanelOpen(false)} aria-label="Close SJD browser">✕</button>
            </div>
            <div className="sjd-panel__filter">
              <label htmlFor="sjd-og-filter">Filter by OG group:</label>
              <select
                id="sjd-og-filter"
                value={sjdOgFilter}
                onChange={e => handleSjdFilterChange(e.target.value)}
              >
                <option value="">All groups</option>
                {[...new Set(sjdAllEntries.map(e => e.og_code))].sort().map(code => (
                  <option key={code} value={code}>{code}</option>
                ))}
              </select>
            </div>
            <div className="sjd-panel__list">
              {sjdLoading && <p>Loading…</p>}
              {!sjdLoading && (() => {
                const visible = sjdOgFilter
                  ? sjdAllEntries.filter(e => e.og_code === sjdOgFilter)
                  : sjdAllEntries;
                if (visible.length === 0) return <p>No SJDs found for this group.</p>;
                return visible.map(entry => (
                <div key={entry.sjd_number} className="sjd-entry">
                  <div className="sjd-entry__title">{entry.title}</div>
                  <div className="sjd-entry__meta">
                    {entry.group_level_str} · {entry.noc_code} · {entry.salary_range}
                  </div>
                  {/* T-22-05: organizational_context truncated at 200 chars (UX choice only) */}
                  <div className="sjd-entry__context">
                    {entry.organizational_context.slice(0, 200)}{entry.organizational_context.length > 200 ? '…' : ''}
                  </div>
                  <button
                    className="btn-primary btn-sm"
                    onClick={() => handleSjdSelect(entry)}
                  >
                    Use this SJD
                  </button>
                </div>
                ));
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
