/* ============================================================
   JD Builder — shared components & input controls
   ============================================================ */
(function () {
  const { useState, useRef, useEffect } = React;
  const D = window.JD_DATA;

  /* ---- icon helper --------------------------------------------- */
  function Icon({ path, size, cls }) {
    return React.createElement('svg', {
      viewBox: '0 0 20 20', width: size || 18, height: size || 18,
      className: cls, 'aria-hidden': true,
      dangerouslySetInnerHTML: { __html: path }
    });
  }
  const Check = () => React.createElement(Icon, { path: D.I.check, size: 12 });

  /* ---- TEXT / TEXTAREA ----------------------------------------- */
  function TextInput({ value, onChange, onSubmit, cfg }) {
    const ref = useRef(null);
    useEffect(() => { if (ref.current) ref.current.focus(); }, []);
    const multi = cfg.type === 'textarea';
    const Tag = multi ? 'textarea' : 'input';
    return React.createElement(Tag, {
      ref, className: 'tf', value: value || '',
      placeholder: cfg.placeholder, rows: multi ? 3 : undefined,
      onChange: e => onChange(e.target.value),
      onKeyDown: e => {
        if (e.key === 'Enter' && (!multi || (e.metaKey || e.ctrlKey))) {
          e.preventDefault();
          if ((value || '').trim()) onSubmit();
        }
      }
    });
  }

  /* ---- CHOICES (single select) --------------------------------- */
  function ChoiceList({ value, onChange, cfg }) {
    const opts = cfg.source === 'workTypes' ? D.WORK_TYPES : cfg.options;
    const grid = cfg.source === 'workTypes';
    return React.createElement('div', { className: 'choices' + (grid ? ' choices--grid' : '') },
      opts.map(o => {
        const sel = value && value.id === o.id;
        return React.createElement('button', {
          key: o.id, type: 'button',
          className: 'choice' + (sel ? ' is-sel' : ''),
          onClick: () => onChange(o)
        },
          o.icon
            ? React.createElement('span', { className: 'choice__icon' }, React.createElement(Icon, { path: o.icon }))
            : React.createElement('span', { className: 'choice__tick' }, React.createElement(Check)),
          React.createElement('span', { className: 'choice__main' },
            React.createElement('span', { className: 'choice__title' },
              o.title,
              o.recommended && React.createElement('span', { className: 'rec-pill' }, ' \u00b7 suggested')
            ),
            o.desc && React.createElement('span', { className: 'choice__desc' }, o.desc)
          )
        );
      })
    );
  }

  /* ---- SCALE (segmented) --------------------------------------- */
  function ScaleInput({ value, onChange, cfg }) {
    return React.createElement('div', { className: 'scale' },
      React.createElement('div', { className: 'scale__ends' },
        React.createElement('span', null, cfg.ends[0]),
        React.createElement('span', null, cfg.ends[1])
      ),
      React.createElement('div', { className: 'scale__track' },
        cfg.options.map(o => {
          const sel = value && value.v === o.v;
          return React.createElement('button', {
            key: o.v, type: 'button',
            className: 'scale__opt' + (sel ? ' is-sel' : ''),
            onClick: () => onChange(o)
          },
            React.createElement('span', { className: 'scale__dot' }),
            React.createElement('span', { className: 'scale__lbl' }, o.lbl)
          );
        })
      )
    );
  }

  /* ---- DUTY BUILDER -------------------------------------------- */
  function DutyBuilder({ value, onChange }) {
    const list = value || [];
    const [text, setText] = useState('');
    const [preview, setPreview] = useState('');
    const inputRef = useRef(null);

    function isOn(plain) { return list.some(d => d.plain === plain); }
    function toggle(s) {
      if (isOn(s.plain)) onChange(list.filter(d => d.plain !== s.plain));
      else onChange([...list, { id: 'sug-' + s.plain, plain: s.plain, polished: s.polished, advisor: false }]);
    }
    function add() {
      const raw = text.trim();
      if (!raw) return;
      const polished = D.refineDuty(raw);
      onChange([...list, { id: 'adv-' + Date.now(), plain: raw, polished, advisor: true }]);
      setText(''); setPreview('');
      if (inputRef.current) inputRef.current.focus();
    }

    return React.createElement('div', { className: 'duties' },
      D.DUTY_SUGGESTIONS.map(s => {
        const on = isOn(s.plain);
        return React.createElement('button', {
          key: s.plain, type: 'button',
          className: 'duty-sug' + (on ? ' is-sel' : ''),
          onClick: () => toggle(s)
        },
          React.createElement('span', { className: 'duty-sug__check' }, React.createElement(Check)),
          React.createElement('span', { className: 'duty-sug__main' },
            React.createElement('span', { className: 'duty-sug__plain' }, s.plain),
            on && React.createElement('span', { className: 'duty-sug__polished' }, s.polished),
            on && React.createElement('span', { className: 'duty-sug__tag' },
              React.createElement(Icon, { path: D.I.spark, size: 11 }), 'refined for the description')
          )
        );
      }),
      // advisor-added duties already in the list
      list.filter(d => d.advisor).map(d =>
        React.createElement('div', { key: d.id, className: 'duty-sug is-sel' },
          React.createElement('span', { className: 'duty-sug__check' }, React.createElement(Check)),
          React.createElement('span', { className: 'duty-sug__main' },
            React.createElement('span', { className: 'duty-sug__plain' }, '\u201c' + d.plain + '\u201d'),
            React.createElement('span', { className: 'duty-sug__polished' }, d.polished),
            React.createElement('span', { className: 'duty-sug__tag' },
              React.createElement(Icon, { path: D.I.spark, size: 11 }), 'refined from your words')
          ),
          React.createElement('span', {
            className: 'duty-sug__x', onClick: (e) => { e.stopPropagation(); onChange(list.filter(x => x.id !== d.id)); }
          }, '\u00d7')
        )
      ),
      React.createElement('div', { className: 'duty-add' },
        React.createElement('input', {
          ref: inputRef, className: 'tf', value: text,
          placeholder: 'Add one in your own words\u2026 e.g. clean up contaminated sites',
          onChange: e => { setText(e.target.value); setPreview(e.target.value.trim() ? D.refineDuty(e.target.value) : ''); },
          onKeyDown: e => { if (e.key === 'Enter') { e.preventDefault(); add(); } }
        }),
        React.createElement('button', { type: 'button', className: 'btn btn--primary', onClick: add, disabled: !text.trim() }, 'Add')
      ),
      preview && React.createElement('div', { className: 'duty-preview' },
        React.createElement(Icon, { path: D.I.spark, size: 12 }),
        React.createElement('span', null, React.createElement('b', null, 'Will read as: '), preview)
      )
    );
  }

  /* ---- DRF PICKER ---------------------------------------------- */
  function DrfPicker({ value, onChange }) {
    return React.createElement('div', { className: 'choices' },
      D.DRF.map(o => {
        const sel = value && value.id === o.id;
        return React.createElement('button', {
          key: o.id, type: 'button',
          className: 'choice' + (sel ? ' is-sel' : ''),
          onClick: () => onChange(o)
        },
          React.createElement('span', { className: 'choice__icon' }, React.createElement(Icon, { path: o.icon })),
          React.createElement('span', { className: 'choice__main' },
            React.createElement('span', { className: 'choice__title' },
              o.cr, o.recommended && React.createElement('span', { className: 'rec-pill' }, ' \u00b7 suggested')),
            React.createElement('span', { className: 'choice__desc' }, o.result)
          )
        );
      })
    );
  }

  /* ---- QUALIFICATION EDITOR ------------------------------------ */
  function QualEditor({ value, onChange }) {
    const v = value || D.QUAL_DEFAULT;
    return React.createElement('div', { className: 'quals' },
      React.createElement('label', { className: 'qual-field' },
        React.createElement('span', { className: 'qual-k' }, 'Education'),
        React.createElement('textarea', { className: 'tf', rows: 3, value: v.education,
          onChange: e => onChange({ ...v, education: e.target.value }) })
      ),
      React.createElement('label', { className: 'qual-field' },
        React.createElement('span', { className: 'qual-k' }, 'Experience'),
        React.createElement('textarea', { className: 'tf', rows: 3, value: v.experience,
          onChange: e => onChange({ ...v, experience: e.target.value }) })
      )
    );
  }

  /* ---- input dispatcher ---------------------------------------- */
  function StepInput(props) {
    const t = props.cfg.type;
    if (t === 'text' || t === 'textarea') return React.createElement(TextInput, props);
    if (t === 'choices') return React.createElement(ChoiceList, props);
    if (t === 'scale') return React.createElement(ScaleInput, props);
    if (t === 'duties') return React.createElement(DutyBuilder, props);
    if (t === 'drf') return React.createElement(DrfPicker, props);
    if (t === 'quals') return React.createElement(QualEditor, props);
    return null;
  }

  // default-answer initialiser per step (for presets / quick demo)
  function initialAnswer(step, record) {
    const c = step.input;
    if (c.type === 'text' || c.type === 'textarea') return c.preset || '';
    if (c.type === 'duties') return [];
    if (c.type === 'quals') return D.QUAL_DEFAULT;
    return null;
  }
  function answerValid(step, a) {
    const t = step.input.type;
    if (t === 'text' || t === 'textarea') return !!(a && a.trim());
    if (t === 'duties') return Array.isArray(a) && a.length > 0;
    if (t === 'quals') return !!(a && a.education && a.experience);
    return !!a;
  }

  window.JD_COMP = { Icon, Check, StepInput, initialAnswer, answerValid };
})();
