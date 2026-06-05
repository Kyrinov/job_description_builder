/* ============================================================
   JD Builder — shared components & input controls
   ============================================================ */
import React, { useState, useRef, useEffect } from 'react';
import { I, WORK_TYPES, DUTY_SUGGESTIONS, DRF, QUAL_DEFAULT, refineDuty } from './data.jsx';

const DUTY_PLACEHOLDER = 'Add one in your own words… e.g. clean up contaminated sites';

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
function DutyBuilder({ value, onChange, cfg }) {
  const list = value || [];
  const [text, setText] = useState('');
  const [preview, setPreview] = useState('');
  const inputRef = useRef(null);
  // cfg.suggestions is injected by app.jsx (keyed to OG group via getDutySuggestions).
  // Falls back to the 'default' set when the group is unmapped or no overrides.
  const suggestions = (cfg && cfg.suggestions) || DUTY_SUGGESTIONS.default;

  function isOn(plain) { return list.some(d => d.plain === plain); }
  function toggle(s) {
    if (isOn(s.plain)) onChange(list.filter(d => d.plain !== s.plain));
    else onChange([...list, { id: 'sug-' + s.plain, plain: s.plain, polished: s.polished, advisor: false }]);
  }
  function add() {
    const raw = text.trim();
    if (!raw) return;
    const polished = refineDuty(raw);
    onChange([...list, { id: 'adv-' + Date.now(), plain: raw, polished, advisor: true }]);
    setText(''); setPreview('');
    if (inputRef.current) inputRef.current.focus();
  }

  return (
    <div className="duties">
      {suggestions.map(s => {
        const on = isOn(s.plain);
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
            <span className="duty-sug__polished">{d.polished}</span>
            <span className="duty-sug__tag">
              <Icon path={I.spark} size={11} />refined from your words
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
  if (t === 'og_confirm') return <NocConfirmList {...props} />; // stub — Phase 16 replaces with OgConfirmList
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
  return !!value;
}

export { Icon, Check, StepInput, initialAnswer, answerValid };
