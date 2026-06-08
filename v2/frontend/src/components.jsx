/* ============================================================
   JD Builder — shared components & input controls
   ============================================================ */
import React, { useState, useRef, useEffect } from 'react';
import { I, WORK_TYPES, DUTY_SUGGESTIONS, DRF, QUAL_DEFAULT, refineDuty } from './data.jsx';

const DUTY_PLACEHOLDER = 'Describe a duty not listed above…';

/* ---- icon helper --------------------------------------------- */
function Icon({ path, size, cls }) {
  return (
    <svg
      viewBox="0 0 20 20"
      width={size || 18}
      height={size || 18}
      className={cls}
      aria-hidden="true"
      // Icon paths are string literals from data.jsx — not user input; XSS-safe
      dangerouslySetInnerHTML={{ __html: path }}
    />
  );
}
const Check = () => <Icon path={I.check} size={12} />;

/* ---- TEXT / TEXTAREA ----------------------------------------- */
function TextInput({ value, onChange, onSubmit, cfg }) {
  const ref = useRef(null);
  useEffect(() => { if (ref.current) ref.current.focus(); }, []);
  const multi = cfg.type === 'textarea';
  const props = {
    ref,
    className: 'tf',
    value: value || '',
    placeholder: cfg.placeholder,
    onChange: e => onChange(e.target.value),
    onKeyDown: e => {
      if (e.key === 'Enter' && (!multi || (e.metaKey || e.ctrlKey))) {
        e.preventDefault();
        if ((value || '').trim()) onSubmit();
      }
    }
  };
  if (multi) return <textarea {...props} rows={3} />;
  return <input {...props} />;
}

/* ---- CHOICES (single select) --------------------------------- */
function ChoiceList({ value, onChange, cfg }) {
  const opts = cfg.source === 'workTypes' ? WORK_TYPES : cfg.options;
  const grid = cfg.source === 'workTypes';
  return (
    <div className={'choices' + (grid ? ' choices--grid' : '')}>
      {opts.map(o => {
        const sel = value && value.id === o.id;
        return (
          <button
            key={o.id}
            type="button"
            className={'choice' + (sel ? ' is-sel' : '')}
            onClick={() => onChange(o)}
          >
            {o.icon
              ? <span className="choice__icon"><Icon path={o.icon} /></span>
              : <span className="choice__tick"><Check /></span>}
            <span className="choice__main">
              <span className="choice__title">
                {o.title}
                {o.recommended && <span className="rec-pill"> {'\u00b7 suggested'}</span>}
              </span>
              {o.desc && <span className="choice__desc">{o.desc}</span>}
            </span>
          </button>
        );
      })}
    </div>
  );
}

/* ---- SCALE (segmented) --------------------------------------- */
function ScaleInput({ value, onChange, cfg }) {
  return (
    <div className="scale">
      <div className="scale__ends">
        <span>{cfg.ends[0]}</span>
        <span>{cfg.ends[1]}</span>
      </div>
      <div className="scale__track">
        {cfg.options.map(o => {
          const sel = value && value.v === o.v;
          return (
            <button
              key={o.v}
              type="button"
              className={'scale__opt' + (sel ? ' is-sel' : '')}
              onClick={() => onChange(o)}
            >
              <span className="scale__dot" />
              <span className="scale__lbl">{o.lbl}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ---- DUTY BUILDER -------------------------------------------- */
// Local shimmer for DutyBuilder loading state. Ghost is defined in document.jsx;
// importing it would create a circular import (document.jsx imports Icon from
// components.jsx). Inline a minimal version here.
const _shimmerWidths = ['w90', 'w70', 'w50', 'w90', 'w70'];
function LocalShimmer({ lines }) {
  return (
    <div className="prose">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={'ph-line ' + _shimmerWidths[i % _shimmerWidths.length]} />
      ))}
    </div>
  );
}

function DutyBuilder({ value, onChange, cfg }) {
  const list = value || [];
  const [text, setText] = useState('');
  const [preview, setPreview] = useState('');
  const [nocDuties, setNocDuties] = useState(null); // null=loading, []=empty/error, [...]=fetched
  const inputRef = useRef(null);
  // Phase 18: prefer cfg.noc_code (verbatim NOC duties from /api/noc/{noc_code}/duties)
  // over the legacy cfg.suggestions static array.
  const noc_code = cfg && cfg.noc_code;
  useEffect(() => {
    if (!noc_code) return;
    setNocDuties(null); // trigger shimmer
    fetch(`/api/noc/${encodeURIComponent(noc_code)}/duties`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => setNocDuties(data.duties || []))
      .catch(() => setNocDuties([]));
  }, [noc_code]);
  // Legacy fallback: cfg.suggestions keyed to OG group via getDutySuggestions.
  // Used only when noc_code is not present (e.g. pre-NOC-confirm flow / tests).
  const suggestions = (cfg && cfg.suggestions) || DUTY_SUGGESTIONS.default;

  function isOn(dutyId) { return list.some(d => d.id === dutyId); }
  function toggleNoc(d) {
    const dutyId = `noc-${d.id}`;
    if (isOn(dutyId)) onChange(list.filter(x => x.id !== dutyId));
    else onChange([...list, {
      id: dutyId,
      plain: d.text,
      text: d.text,
      source: 'noc',
      advisor: false,
      provenance_noc_code: noc_code,
      provenance_section: 'Main duties',
      provenance_hash: d.source_hash || null,
    }]);
  }
  function toggle(s) {
    const dutyId = 'sug-' + s.plain;
    if (isOn(dutyId)) onChange(list.filter(d => d.id !== dutyId));
    else onChange([...list, { id: dutyId, plain: s.plain, polished: s.polished, advisor: false }]);
  }
  function add() {
    const raw = text.trim();
    if (!raw) return;
    const polished = refineDuty(raw);
    onChange([...list, {
      id: `adv-${Date.now()}`,
      plain: raw,
      text: polished,
      source: 'advisor',
      advisor: true,
      provenance_noc_code: null,
      provenance_section: null,
      provenance_hash: null,
    }]);
    setText(''); setPreview('');
    if (inputRef.current) inputRef.current.focus();
  }

  return (
    <div className="duties">
      {/* NOC duties fetched from backend (Phase 18) */}
      {noc_code && (
        nocDuties === null
          ? <LocalShimmer lines={3} />
          : nocDuties.length === 0
            ? <p className="step-loading">No duties found for NOC {noc_code}.</p>
            : nocDuties.map(d => {
                const on = isOn(`noc-${d.id}`);
                return (
                  <button
                    key={d.id}
                    type="button"
                    className={'duty-sug' + (on ? ' is-sel' : '')}
                    onClick={() => toggleNoc(d)}
                  >
                    <span className="duty-sug__check"><Check /></span>
                    <span className="duty-sug__main">
                      <span className="duty-sug__plain">{d.text}</span>
                      {on && (
                        <span className="duty-sug__tag">
                          NOC 2021 · {noc_code}
                        </span>
                      )}
                    </span>
                  </button>
                );
              })
      )}
      {/* Legacy static suggestions fallback (no noc_code) */}
      {!noc_code && suggestions.map(s => {
        const on = isOn('sug-' + s.plain);
        return (
          <button
            key={s.plain}
            type="button"
            className={'duty-sug' + (on ? ' is-sel' : '')}
            onClick={() => toggle(s)}
          >
            <span className="duty-sug__check"><Check /></span>
            <span className="duty-sug__main">
              <span className="duty-sug__plain">{s.plain}</span>
              {on && <span className="duty-sug__polished">{s.polished}</span>}
              {on && (
                <span className="duty-sug__tag">
                  <Icon path={I.spark} size={11} />refined for the description
                </span>
              )}
            </span>
          </button>
        );
      })}
      {/* advisor-added duties already in the list */}
      {list.filter(d => d.advisor).map(d => (
        <div key={d.id} className="duty-sug is-sel">
          <span className="duty-sug__check"><Check /></span>
          <span className="duty-sug__main">
            <span className="duty-sug__plain">{'\u201c' + d.plain + '\u201d'}</span>
            <span className="duty-sug__polished">{d.text || d.polished}</span>
            <span className="duty-sug__tag">
              <Icon path={I.spark} size={11} />advisor-added
            </span>
          </span>
          <span
            className="duty-sug__x"
            onClick={(e) => { e.stopPropagation(); onChange(list.filter(x => x.id !== d.id)); }}
          >
            {'\u00d7'}
          </span>
        </div>
      ))}
      <div className="duty-add">
        <input
          ref={inputRef}
          className="tf"
          value={text}
          placeholder={DUTY_PLACEHOLDER}
          onChange={e => { setText(e.target.value); setPreview(e.target.value.trim() ? refineDuty(e.target.value) : ''); }}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add(); } }}
        />
        <button type="button" className="btn btn--primary" onClick={add} disabled={!text.trim()}>Add</button>
      </div>
      {preview && (
        <div className="duty-preview">
          <Icon path={I.spark} size={12} />
          <span><b>Will read as: </b>{preview}</span>
        </div>
      )}
      <span aria-live="polite" className="visually-hidden">
        {list.length} {list.length === 1 ? 'duty' : 'duties'} selected.
      </span>
    </div>
  );
}

/* ---- NOC CONFIRM LIST ---------------------------------------- */
// cfg.type === 'noc_confirm'
// cfg.candidates: array of { noc_code, noc_title (or title), teer, matched_duties }
// value: selected noc_code string or null
// onChange(noc_code): called on card click
function NocConfirmList({ value, onChange, cfg }) {
  const candidates = cfg.candidates || [];
  return (
    <div className="choices">
      {candidates.map(c => {
        const sel = value === c.noc_code;
        const duties = c.matched_duties || [];
        return (
          <button
            key={c.noc_code}
            type="button"
            className={'choice choice--noc' + (sel ? ' is-sel' : '')}
            onClick={() => onChange(c.noc_code)}
          >
            <span className="choice__main">
              <span className="choice__title">
                {c.noc_code} — {c.noc_title || c.title}
              </span>
              <span className="choice__desc">TEER {c.teer}</span>
            </span>
            {duties.length > 0 && (
              <ul className="noc-duties">
                {duties.slice(0, 2).map((d, i) => <li key={i}>{d}</li>)}
              </ul>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ---- OG CONFIRM LIST ----------------------------------------- */
// cfg.type === 'og_confirm'
// cfg.candidates: array from POST /api/og/classify response
// cfg.asec_alert: { disambiguation_text, citation } or null — from API response via ogAlert state in app.jsx
// cfg.loading: boolean — true while /api/og/classify is in flight
// value: selected candidate object or null (stores full candidate, not just og_code)
// onChange(candidate): stores full OGCandidate object — og_level step reads .og_code from it
function OgConfirmList({ value, onChange, cfg }) {
  const candidates = cfg.candidates || [];
  const alert = cfg.asec_alert || null;
  if (cfg.loading) {
    return <p className="step-loading">Finding occupational group matches...</p>;
  }
  return (
    <div>
      {alert && (
        <div className="asec-alert">
          <p className="asec-alert__title">
            Both Administrative Services (AS) and Economics and Social Science
            Services (EC) appear in the top candidates.
          </p>
          <p className="asec-alert__body">{alert.disambiguation_text}</p>
          <span className="asec-alert__cite">{alert.citation}</span>
        </div>
      )}
      <div className="choices">
        {candidates.map(c => {
          const sel = value && value.og_code === c.og_code;
          return (
            <button
              key={c.og_code}
              type="button"
              className={'choice choice--og' + (sel ? ' is-sel' : '')}
              onClick={() => onChange(c)}
            >
              <span className="choice__main">
                <span className="choice__title">{c.og_code} — {c.og_name}</span>
                <span className="choice__desc">{Math.round(c.confidence * 100)}% match</span>
                {c.definition_excerpt && (
                  <span className="choice__excerpt">{c.definition_excerpt}</span>
                )}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ---- OG LEVEL PICKER ----------------------------------------- */
// cfg.type === 'og_level'
// cfg.levels: array of integers from OG_LEVELS[og_code] — populated by cfgOverride in app.jsx
// value: selected level integer or null
// onChange(level): stores selected integer — PATCH /api/wd/{id} persists og_level
function OgLevelPicker({ value, onChange, cfg }) {
  const levels = cfg.levels || [];
  if (levels.length === 0) {
    return <p className="step-loading">Confirm occupational group first to see level options.</p>;
  }
  return (
    <div className="choices">
      {levels.map(lv => {
        const sel = value === lv;
        return (
          <button
            key={lv}
            type="button"
            className={'choice' + (sel ? ' is-sel' : '')}
            onClick={() => onChange(lv)}
          >
            <span className="choice__main">
              <span className="choice__title">Level {lv < 10 ? '0' + lv : lv}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

/* ---- DRF PICKER ---------------------------------------------- */
function DrfPicker({ value, onChange }) {
  return (
    <div className="choices">
      {DRF.map(o => {
        const sel = value && value.id === o.id;
        return (
          <button
            key={o.id}
            type="button"
            className={'choice' + (sel ? ' is-sel' : '')}
            onClick={() => onChange(o)}
          >
            <span className="choice__icon"><Icon path={o.icon} /></span>
            <span className="choice__main">
              <span className="choice__title">
                {o.cr}
                {o.recommended && <span className="rec-pill"> {'\u00b7 suggested'}</span>}
              </span>
              <span className="choice__desc">{o.result}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

/* ---- QUALIFICATION EDITOR ------------------------------------ */
function QualEditor({ value, onChange }) {
  const v = value || QUAL_DEFAULT;
  return (
    <div className="quals">
      <label className="qual-field">
        <span className="qual-k">Education</span>
        <textarea
          className="tf"
          rows={3}
          value={v.education}
          onChange={e => onChange({ ...v, education: e.target.value })}
        />
      </label>
      <label className="qual-field">
        <span className="qual-k">Experience</span>
        <textarea
          className="tf"
          rows={3}
          value={v.experience}
          onChange={e => onChange({ ...v, experience: e.target.value })}
        />
      </label>
    </div>
  );
}

/* ---- input dispatcher ---------------------------------------- */
function StepInput(props) {
  const t = props.cfg.type;
  if (t === 'text' || t === 'textarea') return <TextInput {...props} />;
  if (t === 'choices') return <ChoiceList {...props} />;
  if (t === 'scale') return <ScaleInput {...props} />;
  if (t === 'duties') return <DutyBuilder {...props} />;
  if (t === 'drf') return <DrfPicker {...props} />;
  if (t === 'quals') return <QualEditor {...props} />;
  if (t === 'noc_confirm') return <NocConfirmList {...props} />;
  if (t === 'og_confirm') return <OgConfirmList {...props} />;
  if (t === 'og_level') return <OgLevelPicker {...props} />;
  return null;
}

// default-answer initialiser per step (for presets / quick demo)
function initialAnswer(step, record) {
  const c = step.input;
  if (c.type === 'text' || c.type === 'textarea') return c.preset || '';
  if (c.type === 'duties') return [];
  if (c.type === 'quals') return QUAL_DEFAULT;
  return null;
}
function answerValid(step, value) {
  const t = step.input.type;
  if (t === 'text' || t === 'textarea') return !!(value && value.trim());
  if (t === 'duties') return Array.isArray(value) && value.length > 0;
  if (t === 'quals') return !!(value && value.education && value.experience);
  if (t === 'noc_confirm') return typeof value === 'string' && value.length > 0;
  if (t === 'og_confirm') return value !== null && value !== undefined && !!value.og_code;
  if (t === 'og_level') return typeof value === 'number' && value >= 1;
  return !!value;
}

export { Icon, Check, StepInput, initialAnswer, answerValid };
