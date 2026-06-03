/* ============================================================
   JD Builder — conversation pane (left)
   ============================================================ */
(function () {
  const D = window.JD_DATA;
  const { Icon, Check, StepInput, answerValid } = window.JD_COMP;

  /* brand + phase progress header */
  function Header({ phaseIdx }) {
    return React.createElement('div', { className: 'convo__head' },
      React.createElement('div', { className: 'brand' },
        React.createElement('div', { className: 'brand__mark' }, React.createElement(Icon, { path: D.I.spark, size: 19 })),
        React.createElement('div', null,
          React.createElement('div', { className: 'brand__name' }, 'JD Builder'),
          React.createElement('div', { className: 'brand__sub' }, 'Guided work-description assistant')
        ),
        React.createElement('div', { className: 'brand__spacer' }),
        React.createElement('div', { className: 'brand__dept' }, 'National Defence')
      ),
      React.createElement('div', { className: 'phases' },
        D.PHASES.map((p, i) =>
          React.createElement('div', {
            key: p, className: 'phase' + (i === phaseIdx ? ' is-active' : '') + (i < phaseIdx ? ' is-done' : '')
          },
            React.createElement('div', { className: 'phase__bar' }, React.createElement('i')),
            React.createElement('div', { className: 'phase__label' }, p)
          )
        )
      )
    );
  }

  /* answered exchange (compact, clickable to edit) */
  function Exchange({ step, record, answer, onEdit }) {
    const label = step.transcript ? step.transcript(answer, record) : String(answer);
    const qText = typeof step.q === 'function' ? step.q(record) : step.q;
    return React.createElement('div', { className: 'xchg' },
      React.createElement('div', { className: 'xchg__q' }, qText),
      React.createElement('div', { className: 'xchg__a', onClick: onEdit, title: 'Click to revisit' }, label)
    );
  }

  /* active question + input */
  function ActiveQuestion({ step, record, draft, setDraft, onCommit, onBack, canBack, isLast }) {
    const qText = typeof step.q === 'function' ? step.q(record) : step.q;
    const valid = answerValid(step, draft);
    const showEnter = step.input.type === 'text';
    return React.createElement('div', { className: 'ask', key: step.id },
      React.createElement('div', { className: 'ask__row' },
        React.createElement('div', { className: 'ask__avatar' }, React.createElement(Icon, { path: step.icon || D.I.spark, size: 16 })),
        React.createElement('div', { className: 'ask__body' },
          React.createElement('div', { className: 'ask__q' }, qText),
          step.helper && React.createElement('div', { className: 'ask__helper', dangerouslySetInnerHTML: { __html: helperHtml(step, record) } })
        )
      ),
      React.createElement('div', { className: 'input-zone' },
        React.createElement(StepInput, { cfg: step.input, value: draft, onChange: setDraft, onSubmit: () => { if (valid) onCommit(); }, record })
      ),
      React.createElement('div', { className: 'actions' },
        React.createElement('button', {
          className: 'btn btn--primary', disabled: !valid, onClick: onCommit
        },
          isLast ? 'Finish & review' : 'Continue',
          React.createElement(Icon, { path: '<path d="M4 10h11M11 5l5 5-5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>', size: 16 })
        ),
        canBack && React.createElement('button', { className: 'btn btn--ghost', onClick: onBack }, 'Back'),
        showEnter && React.createElement('span', { className: 'skip-hint' }, 'Press ', React.createElement('kbd', null, 'Enter'))
      )
    );
  }

  function helperHtml(step, record) {
    let h = typeof step.helper === 'function' ? step.helper(record) : step.helper;
    return h;
  }

  /* completion / review state */
  function ReviewState({ record, cls, onExport, onRestart }) {
    const dutyCount = (record.duties || []).length;
    const checks = [
      ['Position identified', record.title],
      [cls.code ? `Classified as ${cls.code} \u00b7 ${cls.points} pts` : 'Classified', cls.status === 'resolved'],
      [`${dutyCount} key ${dutyCount === 1 ? 'responsibility' : 'responsibilities'}, formally worded`, dutyCount > 0],
      [record.drf ? `Linked to: ${record.drf.cr}` : 'Defence result linked', !!record.drf],
      ['Essential qualifications set', !!record.qualsVisited]
    ];
    return React.createElement('div', { className: 'thread' },
      React.createElement('div', { className: 'done-card' },
        React.createElement('div', { className: 'done-card__icon' }, React.createElement(Icon, { path: D.I.check, size: 27 })),
        React.createElement('div', { className: 'done-card__title' }, 'Your job description is ready.'),
        React.createElement('div', { className: 'done-card__sub' },
          'It reads as one cohesive document \u2014 not stitched-together fragments \u2014 and every element traces back to an authoritative source. Review it on the right; ',
          React.createElement('b', null, 'click any section to revisit your answer.')),
        React.createElement('div', { className: 'checklist' },
          checks.map(([label, ok], i) =>
            React.createElement('div', { className: 'check-row', key: i },
              React.createElement('div', { className: 'check-row__dot' }, React.createElement(Check)),
              React.createElement('span', null, label)))
        ),
        React.createElement('div', { className: 'export-row' },
          React.createElement('button', { className: 'btn--export', onClick: () => onExport('Word document (.docx)') },
            React.createElement(Icon, { path: '<rect x="3" y="2.5" width="14" height="15" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M6 7h8M6 10h8M6 13h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>' }),
            'Export DOCX'),
          React.createElement('button', { className: 'btn--export', onClick: () => onExport('PDF') },
            React.createElement(Icon, { path: '<rect x="3" y="2.5" width="14" height="15" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M6.5 13v-3.5h1.2a1.1 1.1 0 010 2.2H6.5M11 9.5V13M11 9.5h1.8M11 11.4h1.4" stroke="currentColor" stroke-width="1.3" fill="none" stroke-linecap="round"/>' }),
            'Export PDF'),
          React.createElement('button', { className: 'btn--export', onClick: () => onExport('clipboard') },
            React.createElement(Icon, { path: '<rect x="6" y="3" width="11" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M3.5 6v9.5A1.5 1.5 0 005 17h8" fill="none" stroke="currentColor" stroke-width="1.6"/>' }),
            'Copy')
        ),
        React.createElement('button', { className: 'btn btn--ghost restart', onClick: onRestart, style: { paddingLeft: 0 } }, '\u2190 Start a new description')
      )
    );
  }

  window.JD_CONVO = { Header, Exchange, ActiveQuestion, ReviewState };
})();
