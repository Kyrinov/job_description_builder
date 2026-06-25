/* ============================================================
   JD Builder — live document preview (right pane)
   ============================================================ */
(function () {
  const { useState, useEffect, useRef } = React;
  const D = window.JD_DATA;
  const { Icon } = window.JD_COMP;

  /* compose a cohesive overview paragraph from the answers */
  function buildOverview(r) {
    if (!r.summary) return null;
    let lead = '';
    if (r.branch) lead += `Located within ${r.branch}, `;
    if (r.reports) lead += (lead ? 'and ' : '') + `reporting to the ${r.reports}, `;
    lead += `the ${r.title || 'position'} `;
    let s = r.summary.trim();
    s = s.charAt(0).toLowerCase() + s.slice(1);
    let para = lead + s;
    if (!/[.!?]$/.test(para)) para += '.';
    const supMap = {
      'No \u2014 individual contributor': ' The incumbent works as an individual contributor and subject-matter resource.',
      'Leads 1\u20133 people or a small team': ' The incumbent provides functional leadership to a small team.',
      'Manages a team of 4\u201310': ' The incumbent manages a team and is accountable for its collective results.',
      'Leads multiple teams': ' The incumbent leads multiple teams and integrates their work toward common objectives.'
    };
    if (r.supervises && supMap[r.supervises]) para += supMap[r.supervises];
    return para;
  }

  /* ghost shimmer lines */
  function Ghost({ lines }) {
    const w = ['w90', 'w70', 'w50', 'w90', 'w70'];
    return React.createElement('div', { className: 'prose' },
      Array.from({ length: lines }).map((_, i) =>
        React.createElement('div', { key: i, className: 'ph-line ' + w[i % w.length] })));
  }

  /* a document section wrapper with section number + source tag */
  function Sec({ n, title, src, ghost, fresh, editable, onEdit, children }) {
    return React.createElement('section', {
      className: 'sec' + (ghost ? ' is-ghost' : '') + (editable ? ' sec--editable' : ''),
      onClick: editable ? onEdit : undefined
    },
      React.createElement('div', { className: 'sec__h' },
        n && React.createElement('span', { className: 'n' }, n),
        React.createElement('span', null, title),
        src && React.createElement('span', { className: 'src' },
          React.createElement('i', { style: { width: 5, height: 5, borderRadius: '50%', background: 'var(--accent)', display: 'inline-block' } }),
          src)
      ),
      React.createElement('div', { className: fresh ? 'fresh' : '' }, children)
    );
  }

  /* the classification + JES block */
  function ClassBlock({ cls }) {
    return React.createElement('div', null,
      React.createElement('div', { className: 'cls-block' },
        React.createElement('div', { className: 'cls-block__badge' },
          React.createElement('div', { className: 'cls-block__code' }, cls.code),
          React.createElement('div', { className: 'cls-block__pts' }, cls.points + ' pts')
        ),
        React.createElement('div', { className: 'cls-block__body' },
          React.createElement('div', { className: 'cls-block__name' }, cls.group + ' \u2014 ' + cls.groupName),
          React.createElement('div', { className: 'cls-block__why' }, cls.rationale)
        )
      ),
      cls.factors
        ? React.createElement('div', { className: 'jes' },
            cls.factors.map(f =>
              React.createElement('div', { key: f.name, className: 'jes__row' },
                React.createElement('span', { className: 'jes__name' }, f.name),
                React.createElement('span', { className: 'jes__deg' }, 'D' + f.degree),
                React.createElement('span', { className: 'jes__pts' }, f.points)
              )
            ),
            React.createElement('div', { className: 'jes__total' },
              React.createElement('span', null, 'Total \u2014 ' + cls.standard),
              React.createElement('b', null, cls.points)
            )
          )
        : React.createElement('div', { className: 'jes' },
            React.createElement('div', { className: 'jes__total' },
              React.createElement('span', null, 'Evaluated under the ' + cls.standard),
              React.createElement('b', null, cls.points)
            )
          )
    );
  }

  function DocumentPane({ record: r, cls, flashes, reviewing, onEditStep }) {
    const overview = buildOverview(r);
    const hasDuties = r.duties && r.duties.length;
    const isFresh = (k) => flashes && flashes.has(k);

    let n = 0;
    const sections = [];

    // 1 — Position identification (always, fills as we go)
    n++;
    sections.push(React.createElement(Sec, {
      key: 'id', n: '\u2014', title: 'Position Identification',
      src: 'TBS Directive on Classification',
      editable: reviewing, onEdit: () => onEditStep('title')
    },
      React.createElement('div', { className: 'doc__meta', style: { marginTop: 0, paddingTop: 0, borderTop: 'none' } },
        metaItem('Position title', r.title),
        metaItem('Classification', cls.code || (cls.group ? cls.group + ' group' : null), cls.status === 'resolved'),
        metaItem('Branch / directorate', r.branch),
        metaItem('Reports to', r.reports)
      )
    ));

    // 2 — Position overview
    n++;
    sections.push(React.createElement(Sec, {
      key: 'ov', n: String(n), title: 'Position Overview',
      src: 'Drafted from your answers', ghost: !overview, fresh: isFresh('summary'),
      editable: reviewing, onEdit: () => onEditStep('summary')
    },
      overview
        ? React.createElement('p', { className: 'prose' }, overview)
        : React.createElement(Ghost, { lines: 3 })
    ));

    // 3 — Key responsibilities
    n++;
    sections.push(React.createElement(Sec, {
      key: 'du', n: String(n), title: 'Key Responsibilities',
      src: hasDuties ? 'NOC 2021 \u00b7 refined' : null, ghost: !hasDuties, fresh: isFresh('duties'),
      editable: reviewing, onEdit: () => onEditStep('duties')
    },
      hasDuties
        ? React.createElement('ul', { className: 'doc-duties' },
            r.duties.map(d =>
              React.createElement('li', { key: d.id, className: 'doc-duty' + (d.advisor ? ' is-advisor' : '') }, d.polished)))
        : React.createElement('div', null,
            React.createElement(Ghost, { lines: 2 }),
            React.createElement('p', { className: 'ghost-note' }, 'Your responsibilities will appear here, formally worded.'))
    ));

    // 4 — Classification & evaluation (only once resolved)
    if (cls.status === 'resolved') {
      n++;
      sections.push(React.createElement(Sec, {
        key: 'cls', n: String(n), title: 'Classification & Evaluation',
        src: cls.factors ? cls.standard : 'Job Evaluation Standard', fresh: isFresh('level'),
        editable: reviewing, onEdit: () => onEditStep('scopeDirection')
      }, React.createElement(ClassBlock, { cls })));
    }

    // 5 — DND results linkage
    if (r.drf) {
      n++;
      sections.push(React.createElement(Sec, {
        key: 'drf', n: String(n), title: 'Defence Results Linkage',
        src: 'DND Departmental Results Framework', fresh: isFresh('drf'),
        editable: reviewing, onEdit: () => onEditStep('drf')
      },
        React.createElement('div', { className: 'drf' },
          React.createElement('div', { className: 'drf__cr' }, r.drf.cr),
          React.createElement('div', { className: 'drf__result' }, r.drf.result),
          React.createElement('ul', { className: 'drf__ind' },
            r.drf.indicators.map((ind, i) => React.createElement('li', { key: i }, ind)))
        )
      ));
    }

    // 6 — Qualifications
    if (r.quals && r.quals !== D.QUAL_DEFAULT || (reviewing && r.quals)) {
      // show once visited
    }
    if (r.qualsVisited) {
      n++;
      sections.push(React.createElement(Sec, {
        key: 'q', n: String(n), title: 'Essential Qualifications',
        src: 'TBS Qualification Standard', fresh: isFresh('quals'),
        editable: reviewing, onEdit: () => onEditStep('quals')
      },
        React.createElement('div', null,
          React.createElement('p', { className: 'prose', style: { marginBottom: 12 } },
            React.createElement('b', { style: { fontFamily: 'var(--mono)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--ink-faint)', display: 'block', marginBottom: 4 } }, 'Education'),
            (r.quals || D.QUAL_DEFAULT).education),
          React.createElement('p', { className: 'prose' },
            React.createElement('b', { style: { fontFamily: 'var(--mono)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--ink-faint)', display: 'block', marginBottom: 4 } }, 'Experience'),
            (r.quals || D.QUAL_DEFAULT).experience)
        )
      ));
    }

    // provenance footer
    const provTags = [];
    if (hasDuties) provTags.push('NOC 2021');
    if (cls.status === 'resolved') provTags.push(cls.factors ? 'EC JES 2017' : cls.standard);
    if (cls.group) provTags.push('TBS OG Definitions');
    if (r.drf) provTags.push('DND DRF');
    if (r.qualsVisited) provTags.push('TBS Qualification Standard');
    if (r.duties && r.duties.some(d => d.advisor)) provTags.push('Advisor-added');

    return React.createElement('div', { className: 'doc' },
      // eyebrow + title
      React.createElement('div', { className: 'doc__eyebrow' },
        'Work Description', React.createElement('span', { style: { fontWeight: 400 } }, 'Department of National Defence')),
      React.createElement('h1', { className: 'doc__title' + (isFresh('title') ? ' fresh' : '') },
        r.title || React.createElement('span', { className: 'ph' }, 'Your position title\u2026')),

      sections,

      provTags.length > 0 && React.createElement('div', { className: 'prov' },
        React.createElement('span', { style: { fontFamily: 'var(--mono)', fontSize: 9.5, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--ink-faint)', width: '100%', marginBottom: 4 } }, 'Every element is traceable to its source'),
        provTags.map(t => React.createElement('span', { key: t, className: 'prov__tag' },
          React.createElement('i'), t)))
    );

    function metaItem(k, v, strong) {
      return React.createElement('div', { className: 'doc__meta-item' },
        React.createElement('div', { className: 'doc__meta-k' }, k),
        React.createElement('div', { className: 'doc__meta-v' + (v ? '' : ' is-empty') + (strong ? ' is-strong' : '') }, v || 'Pending'));
    }
  }

  window.JD_DOC = { DocumentPane };
})();
