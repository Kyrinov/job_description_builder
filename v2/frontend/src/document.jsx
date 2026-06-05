/* ============================================================
   JD Builder — live document preview (right pane)
   ============================================================ */
import React from 'react';
import { QUAL_DEFAULT } from './data.jsx';
import { Icon } from './components.jsx';

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
  return (
    <div className="prose">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={'ph-line ' + w[i % w.length]} />
      ))}
    </div>
  );
}

/* Compact JS copy of CAF rank equivalence lookup.
   Returns matching rank entries for a given og_code + og_level combination.
   Source: CAF_RANK_OG_EQUIVALENCE constant in v2/backend/app/data/constants.py.
   Advisory only — not authoritative. */
function getCafEquivalence(ogCode, ogLevel) {
  if (!ogCode || !ogLevel) return null;
  const target = `${ogCode}-${ogLevel < 10 ? '0' + ogLevel : ogLevel}`;
  const CAF_EQUIV = {
    'CR-02': ['Private / Able Seaman', 'Corporal / Master Seaman'],
    'CR-03': ['Private / Able Seaman', 'Corporal / Master Seaman'],
    'CR-04': ['Corporal / Master Seaman', 'Master Corporal / Leading Seaman'],
    'CR-05': ['Master Corporal / Leading Seaman', 'Sergeant / Petty Officer 2nd Class'],
    'CR-06': ['Sergeant / Petty Officer 2nd Class', 'Warrant Officer / Petty Officer 1st Class'],
    'CR-07': ['Warrant Officer / Petty Officer 1st Class'],
    'AS-01': ['Corporal / Master Seaman'],
    'AS-02': ['Master Corporal / Leading Seaman'],
    'AS-03': ['Sergeant / Petty Officer 2nd Class'],
    'AS-04': ['Warrant Officer / Petty Officer 1st Class', 'Master Warrant Officer / Chief Petty Officer 2nd Class'],
    'AS-05': ['Master Warrant Officer / Chief Petty Officer 2nd Class', 'Chief Warrant Officer / Chief Petty Officer 1st Class'],
    'AS-06': ['Lieutenant / Lieutenant (N)', 'Captain / Lieutenant (N)'],
    'AS-07': ['Major / Lieutenant-Commander'],
    'AS-08': ['Lieutenant-Colonel / Commander'],
    'EC-04': ['Captain / Lieutenant (N)', 'Major / Lieutenant-Commander'],
    'EC-05': ['Major / Lieutenant-Commander'],
    'EC-06': ['Major / Lieutenant-Commander', 'Lieutenant-Colonel / Commander'],
    'EC-07': ['Lieutenant-Colonel / Commander', 'Colonel / Captain (N)'],
    'EC-08': ['Colonel / Captain (N)', 'Brigadier-General / Commodore'],
    'IT-01': ['Corporal / Master Seaman'],
    'IT-02': ['Sergeant / Petty Officer 2nd Class'],
    'IT-03': ['Warrant Officer / Petty Officer 1st Class'],
    'IT-04': ['Master Warrant Officer / Chief Petty Officer 2nd Class'],
    'IT-05': ['Chief Warrant Officer / Chief Petty Officer 1st Class', 'Lieutenant / Lieutenant (N)'],
    'FI-01': ['Corporal / Master Seaman'],
    'FI-02': ['Sergeant / Petty Officer 2nd Class'],
    'FI-03': ['Warrant Officer / Petty Officer 1st Class'],
    'FI-04': ['Master Warrant Officer / Chief Petty Officer 2nd Class'],
  };
  const ranks = CAF_EQUIV[target];
  return ranks ? ranks.join(', ') : null;
}

/* a document section wrapper with section number + source tag */
function Sec({ n, title, src, ghost, fresh, editable, onEdit, children }) {
  return (
    <section
      className={`sec${ghost ? ' is-ghost' : ''}${editable ? ' sec--editable' : ''}`}
      onClick={editable ? onEdit : undefined}
    >
      <div className="sec__h">
        {n && <span className="n">{n}</span>}
        <span>{title}</span>
        {src && (
          <span className="src">
            <i style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--accent)', display: 'inline-block' }} />
            {src}
          </span>
        )}
      </div>
      <div className={fresh ? 'fresh' : ''}>{children}</div>
    </section>
  );
}

/* the classification + JES block */
export function ClassBlock({ cls, onOverride }) {
  if (cls.factors) {
    return (
      <div>
        <div className="cls-block">
          <div className="cls-block__badge">
            <div className="cls-block__code">{cls.code}</div>
            <div className="cls-block__pts">{cls.points} pts</div>
          </div>
          <div className="cls-block__body">
            <div className="cls-block__name">{cls.group} — {cls.groupName}</div>
            <div className="cls-block__why">{cls.rationale}</div>
          </div>
        </div>
        <div className="jes">
          {cls.factors.map(f => (
            <div key={f.name} className="jes__row">
              <span className="jes__name">{f.name}</span>
              {f.degree === -1
                ? <input
                    type="number" min="1" max="8" className="jes__override-input"
                    placeholder="Enter degree"
                    onChange={e => onOverride && onOverride(f.name, parseInt(e.target.value, 10))}
                  />
                : <span className="jes__deg">D{f.degree}</span>
              }
              <span className="jes__pts">{f.points}</span>
            </div>
          ))}
          <div className="jes__total">
            <span>Total — {cls.standard}</span>
            <b>{cls.points}</b>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div>
      <div className="cls-block">
        <div className="cls-block__badge">
          <div className="cls-block__code">{cls.code}</div>
          <div className="cls-block__pts">{cls.points} pts</div>
        </div>
        <div className="cls-block__body">
          <div className="cls-block__name">{cls.group} — {cls.groupName}</div>
          <div className="cls-block__why">{cls.rationale}</div>
        </div>
      </div>
      <div className="jes">
        <div className="jes__total">
          <span>Evaluated under the {cls.standard}</span>
          <b>{cls.points}</b>
        </div>
      </div>
    </div>
  );
}

function metaItem(k, v, strong) {
  return (
    <div className="doc__meta-item">
      <div className="doc__meta-k">{k}</div>
      <div className={`doc__meta-v${v ? '' : ' is-empty'}${strong ? ' is-strong' : ''}`}>
        {v || 'Pending'}
      </div>
    </div>
  );
}

function DocumentPane({ record: r, cls, flashes, reviewing, onEditStep, onJesOverride }) {
  const overview = buildOverview(r);
  const hasDuties = r.duties && r.duties.length;
  const isFresh = (k) => flashes && flashes.has(k);

  let n = 0;
  const sections = [];

  // 1 — Position identification (always, fills as we go)
  n++;
  // Classification value (for the metaItem): prefer the v2.0 evidence-based
  // confirmed_og + og_level over the legacy workType-based cls object.
  const classificationValue = r.confirmed_og && r.og_level
    ? `${r.confirmed_og.og_code}-${r.og_level < 10 ? '0' + r.og_level : r.og_level}`
    : (cls.code || (cls.group ? cls.group + ' group' : null));
  sections.push(
    <Sec
      key="id" n={'\u2014'} title="Position Identification"
      src="TBS Directive on Classification"
      editable={reviewing} onEdit={() => onEditStep('title')}
    >
      <div className="doc__meta" style={{ marginTop: 0, paddingTop: 0, borderTop: 'none' }}>
        {metaItem('Position title', r.title)}
        {metaItem('Classification', classificationValue, !!(r.confirmed_og && r.og_level))}
        {metaItem('Branch / directorate', r.branch)}
        {metaItem('Reports to', r.reports)}
      </div>
      {/* CLASS-05: CAF rank advisory — only when reports_to_military = true and OG confirmed */}
      {r.reports_to_military && r.confirmed_og && r.og_level && (
        <div className="caf-advisory">
          <span className="caf-advisory__label">
            CAF Rank Equivalent (advisory — not authoritative):
          </span>
          <span className="caf-advisory__value">
            {getCafEquivalence(r.confirmed_og.og_code, r.og_level) || 'See TBS advisory tables'}
          </span>
        </div>
      )}
    </Sec>
  );

  // 2 — Position overview
  n++;
  sections.push(
    <Sec
      key="ov" n={String(n)} title="Position Overview"
      src="Drafted from your answers" ghost={!overview} fresh={isFresh('summary')}
      editable={reviewing} onEdit={() => onEditStep('summary')}
    >
      {overview
        ? <p className="prose">{overview}</p>
        : <Ghost lines={3} />}
    </Sec>
  );

  // 3 — Key responsibilities
  n++;
  sections.push(
    <Sec
      key="du" n={String(n)} title="Key Responsibilities"
      src={hasDuties ? 'NOC 2021 \u00b7 refined' : null} ghost={!hasDuties} fresh={isFresh('duties')}
      editable={reviewing} onEdit={() => onEditStep('duties')}
    >
      {hasDuties
        ? (
          <ul className="doc-duties">
            {r.duties.map(d => (
              <li key={d.id} className={`doc-duty${d.advisor ? ' is-advisor' : ''}`}>
                {d.polished}
              </li>
            ))}
          </ul>
        )
        : (
          <div>
            <Ghost lines={2} />
            <p className="ghost-note">Your responsibilities will appear here, formally worded.</p>
          </div>
        )}
    </Sec>
  );

  // 4 — Classification & evaluation (CLASS-04 frontend gate)
  // Always render this section. "Classification pending" when confirmed_og or
  // og_level is null; resolved content when both are set.
  n++;
  if (!r.confirmed_og || !r.og_level) {
    sections.push(
      <Sec
        key="cls" n={String(n)} title="Classification & Evaluation"
        src="TBS Directive on Classification"
        editable={reviewing} onEdit={() => onEditStep('og_confirm')}
      >
        <p className="sec__pending">
          Classification pending — confirm occupational group and level to proceed.
        </p>
      </Sec>
    );
  } else {
    const resolvedCode = `${r.confirmed_og.og_code}-${r.og_level < 10 ? '0' + r.og_level : r.og_level}`;
    sections.push(
      <Sec
        key="cls" n={String(n)} title="Classification & Evaluation"
        src="TBS Directive on Classification" fresh={isFresh('og_level')}
        editable={reviewing} onEdit={() => onEditStep('og_level')}
      >
        <div className="cls-block">
          <div className="cls-block__badge">
            <div className="cls-block__code">{resolvedCode}</div>
          </div>
          <div className="cls-block__body">
            <div className="cls-block__name">{r.confirmed_og.og_name}</div>
            <div className="cls-block__why">
              Occupational group <b>{r.confirmed_og.og_code}</b> at level <b>{r.og_level < 10 ? '0' + r.og_level : r.og_level}</b>, confirmed by the Socratic question bank signals and the confirmed NOC code.
            </div>
          </div>
        </div>
        {/* JES scorecard — renders once record.jes_scores is populated (JES-04) */}
        {r.jes_scores && r.jes_scores.length > 0 && (
          <ClassBlock
            cls={{
              code: resolvedCode,
              group: r.confirmed_og.og_code,
              groupName: r.confirmed_og.og_name,
              standard: r.jes_standard_name || (r.jes_is_ec ? 'EC JES 2017' : ''),
              points: r.jes_total_points,
              factors: r.jes_is_ec ? r.jes_scores.map(f => ({
                name: f.factor_name,
                degree: f.degree,
                points: f.points,
              })) : null,
            }}
            onOverride={onJesOverride}
          />
        )}
      </Sec>
    );
  }

  // 5 — DND results linkage
  if (r.drf) {
    n++;
    sections.push(
      <Sec
        key="drf" n={String(n)} title="Defence Results Linkage"
        src="DND Departmental Results Framework" fresh={isFresh('drf')}
        editable={reviewing} onEdit={() => onEditStep('drf')}
      >
        <div className="drf">
          <div className="drf__cr">{r.drf.cr}</div>
          <div className="drf__result">{r.drf.result}</div>
          <ul className="drf__ind">
            {r.drf.indicators.map((ind, i) => <li key={i}>{ind}</li>)}
          </ul>
        </div>
      </Sec>
    );
  }

  // 6 — Qualifications
  if (r.qualsVisited) {
    n++;
    const quals = r.quals || QUAL_DEFAULT;
    sections.push(
      <Sec
        key="q" n={String(n)} title="Essential Qualifications"
        src="TBS Qualification Standard" fresh={isFresh('quals')}
        editable={reviewing} onEdit={() => onEditStep('quals')}
      >
        <div>
          <p className="prose" style={{ marginBottom: 12 }}>
            <b style={{ fontFamily: 'var(--mono)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--ink-faint)', display: 'block', marginBottom: 4 }}>
              Education
            </b>
            {quals.education}
          </p>
          <p className="prose">
            <b style={{ fontFamily: 'var(--mono)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--ink-faint)', display: 'block', marginBottom: 4 }}>
              Experience
            </b>
            {quals.experience}
          </p>
        </div>
      </Sec>
    );
  }

  // provenance footer
  const provTags = [];
  if (hasDuties) provTags.push('NOC 2021');
  if (cls.status === 'resolved') provTags.push(cls.factors ? 'EC JES 2017' : cls.standard);
  if (cls.group) provTags.push('TBS OG Definitions');
  if (r.drf) provTags.push('DND DRF');
  if (r.qualsVisited) provTags.push('TBS Qualification Standard');
  if (r.duties && r.duties.some(d => d.advisor)) provTags.push('Advisor-added');

  return (
    <div className="doc">
      <div className="doc__eyebrow">
        Work Description<span style={{ fontWeight: 400 }}>Department of National Defence</span>
      </div>
      <h1 className={`doc__title${isFresh('title') ? ' fresh' : ''}`}>
        {r.title || <span className="ph">Your position title…</span>}
      </h1>

      {sections}

      {provTags.length > 0 && (
        <div className="prov">
          <span style={{ fontFamily: 'var(--mono)', fontSize: 9.5, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--ink-faint)', width: '100%', marginBottom: 4 }}>
            Every element is traceable to its source
          </span>
          {provTags.map(t => (
            <span key={t} className="prov__tag">
              <i />{t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export { DocumentPane };
