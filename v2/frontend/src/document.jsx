/* ============================================================
   JD Builder — live document preview (right pane)
   ============================================================ */
import React from 'react';
import { I, QUAL_DEFAULT } from './data.jsx';
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
    'No — individual contributor': ' The incumbent works as an individual contributor and subject-matter resource.',
    'Leads 1–3 people or a small team': ' The incumbent provides functional leadership to a small team.',
    'Manages a team of 4–10': ' The incumbent manages a team and is accountable for its collective results.',
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

/* Phase 18: Orphan warning badge (JD-04) — rendered inside flagged duty li
   when d.orphan && reviewing. Rationale is the OG_DEFINITIONS exclusion text. */
function OrphanBadge({ rationale }) {
  return (
    <div className="orphan-badge">
      <span className="orphan-badge__icon">
        <Icon path={I.warn} size={13} />
      </span>
      <span className="orphan-badge__body">
        <span className="orphan-badge__label">Orphan Warning</span>
        <span className="orphan-badge__cite">{rationale}</span>
      </span>
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
function Sec({ n, title, src, ghost, fresh, editable, onEdit, children,
               sectionKey, amendmentNote, amendmentPanel, onAmendToggle, onAmendSave, reviewing }) {
  const panelOpen = amendmentPanel?.open;
  const panelText = amendmentPanel?.text ?? '';
  const savedNote = amendmentPanel?.saved ?? amendmentNote ?? null;

  return (
    <section
      className={`sec${ghost ? ' is-ghost' : ''}${editable ? ' sec--editable' : ''}`}
      onClick={(!panelOpen && editable) ? onEdit : undefined}
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
        {reviewing && sectionKey && (
          <>
            <button
              className={`amend-btn${panelOpen ? ' is-active' : ''}`}
              aria-label={`Add amendment note for ${title}`}
              aria-expanded={!!panelOpen}
              onClick={e => { e.stopPropagation(); onAmendToggle(sectionKey); }}
            >
              <Icon path='<path d="M14 3l3 3-9 9H5v-3L14 3z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>' size={13} />
            </button>
            {savedNote && (
              <span className="amend-indicator" aria-label="Amendment note exists" />
            )}
          </>
        )}
      </div>
      {panelOpen && (
        <div className="amend-panel" style={{ animation: 'rise 0.3s ease both' }}>
          <span className="amend-panel__label">Note for: {title}</span>
          <textarea
            className="tf"
            value={panelText}
            placeholder="Enter a note for the advisor or reviewing manager…"
            onChange={e => onAmendToggle(sectionKey, e.target.value)}
          />
          <div className="amend-panel__actions">
            <button
              className="btn--primary"
              disabled={!panelText.trim()}
              onClick={() => onAmendSave(sectionKey, panelText)}
            >Save note</button>
            <button
              className="btn--ghost"
              onClick={() => onAmendToggle(sectionKey, null)}
            >Discard note</button>
            <span className="amend-count">{panelText.length} characters</span>
          </div>
        </div>
      )}
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

function DocumentPane({ record: r, cls, flashes, reviewing, onEditStep, onJesOverride,
                        amendmentNotes, amendmentPanels, onAmendToggle, onAmendSave }) {
  const safeCls = cls || {};
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
    : (safeCls.code || (safeCls.group ? safeCls.group + ' group' : null));
  sections.push(
    <Sec
      key="id" n={'—'} title="Position Identification"
      src="TBS Directive on Classification"
      editable={reviewing} onEdit={() => onEditStep('title')}
      sectionKey="id" reviewing={reviewing}
      amendmentNote={amendmentNotes?.id} amendmentPanel={amendmentPanels?.id}
      onAmendToggle={onAmendToggle} onAmendSave={onAmendSave}
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
      sectionKey="ov" reviewing={reviewing}
      amendmentNote={amendmentNotes?.ov} amendmentPanel={amendmentPanels?.ov}
      onAmendToggle={onAmendToggle} onAmendSave={onAmendSave}
    >
      {overview
        ? <p className="prose">{overview}</p>
        : <Ghost lines={3} />}
    </Sec>
  );

  // 3 — Organizational Context (Phase 26 — ORG-02)
  // Renders above Client Service Results and Key Responsibilities when the
  // advisor has populated record.org_context via the new Socratic step.
  // Section number n is incremented conditionally so the downstream
  // Responsibilities/Classification/Qualifications sections renumber
  // correctly when this section is hidden (org_context is null).
  if (r.org_context) {
    n++;
    sections.push(
      <Sec
        key="org_ctx" n={String(n)} title="Organizational Context"
        src="Advisor-provided" fresh={isFresh('org_context')}
        editable={reviewing} onEdit={() => onEditStep('org_context')}
        sectionKey="org_ctx" reviewing={reviewing}
        amendmentNote={amendmentNotes?.org_ctx}
        amendmentPanel={amendmentPanels?.org_ctx}
        onAmendToggle={onAmendToggle} onAmendSave={onAmendSave}
      >
        <p className="prose">{r.org_context}</p>
      </Sec>
    );
  }

  // 3b — Client Service Results (Phase 23 data capture; preview was missing — ORG-02 prereq)
  // The data has been captured via the client_service_results step since
  // Phase 23 (WG-03); preview rendering is added in Phase 26 alongside the
  // org_context Sec so the document reflects everything the advisor answered.
  if (r.client_service_results) {
    n++;
    sections.push(
      <Sec
        key="csr" n={String(n)} title="Client Service Results"
        src="Advisor-provided" fresh={isFresh('client_service_results')}
        editable={reviewing} onEdit={() => onEditStep('client_service_results')}
        sectionKey="csr" reviewing={reviewing}
        amendmentNote={amendmentNotes?.csr}
        amendmentPanel={amendmentPanels?.csr}
        onAmendToggle={onAmendToggle} onAmendSave={onAmendSave}
      >
        <p className="prose">{r.client_service_results}</p>
      </Sec>
    );
  }

  // 3c — Responsibilities narrative (Phase 27 — RESP-02).
  // Renders above Key Responsibilities (key="du") when the advisor has
  // populated record.responsibilities_narrative via the new Socratic
  // step. Section number n is incremented conditionally so the downstream
  // Classification / Qualifications / DRF sections renumber correctly
  // when this section is hidden (responsibilities_narrative is null).
  // Mirrors the org_ctx / csr Sec template exactly.
  if (r.responsibilities_narrative) {
    n++;
    sections.push(
      <Sec
        key="resp_narrative" n={String(n)} title="Responsibilities"
        src="Advisor-provided" fresh={isFresh('responsibilities_narrative')}
        editable={reviewing} onEdit={() => onEditStep('responsibilities_narrative')}
        sectionKey="resp_narrative" reviewing={reviewing}
        amendmentNote={amendmentNotes?.resp_narrative}
        amendmentPanel={amendmentPanels?.resp_narrative}
        onAmendToggle={onAmendToggle} onAmendSave={onAmendSave}
      >
        <p className="prose">{r.responsibilities_narrative}</p>
      </Sec>
    );
  }

  // Key Responsibilities (always rendered; renumbers dynamically when the
  // optional org_context / csr / resp_narrative Secs above are present)
  n++;
  sections.push(
    <Sec
      key="du" n={String(n)} title="Key Responsibilities"
      src={hasDuties ? 'NOC 2021' : null} ghost={!hasDuties} fresh={isFresh('duties')}
      editable={reviewing} onEdit={() => onEditStep('duties')}
      sectionKey="du" reviewing={reviewing}
      amendmentNote={amendmentNotes?.du} amendmentPanel={amendmentPanels?.du}
      onAmendToggle={onAmendToggle} onAmendSave={onAmendSave}
    >
      {hasDuties
        ? (
          <ul className="doc-duties">
            {r.duties.map(d => (
              <li key={d.id} className={`doc-duty${d.advisor ? ' is-advisor' : ''}`}>
                {/* Phase 22 SJD-02: SJD provenance badge — distinct visual marker for
                    duties seeded by sjd-start (source="sjd"). Shows before the duty
                    text so users see provenance at a glance, parallel to how NOC
                    duties are already marked by the section's `src` header. */}
                {d.source === 'sjd' && <span className="tag tag--sjd">SJD</span>}
                {d.text || d.polished}
                {d.orphan && reviewing && <OrphanBadge rationale={d.orphan_rationale} />}
              </li>
            ))}
          </ul>
        )
        : (
          <div>
            <Ghost lines={2} />
            <p className="ghost-note">Select duties from the NOC list — they will appear here, verbatim and traceable.</p>
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
        sectionKey="cls" reviewing={reviewing}
        amendmentNote={amendmentNotes?.cls} amendmentPanel={amendmentPanels?.cls}
        onAmendToggle={onAmendToggle} onAmendSave={onAmendSave}
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
        sectionKey="cls" reviewing={reviewing}
        amendmentNote={amendmentNotes?.cls} amendmentPanel={amendmentPanels?.cls}
        onAmendToggle={onAmendToggle} onAmendSave={onAmendSave}
      >
        {/* JES scorecard — renders once jes_total_points is set (JES-04).
            Gate on jes_total_points (not jes_scores.length) so non-EC groups
            (which return factors:[] from the backend) also render the scorecard.
            When JES is not yet scored, show the plain classification block. */}
        {r.jes_total_points != null ? (
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
              rationale: `Occupational group ${r.confirmed_og.og_code} at level ${r.og_level < 10 ? '0' + r.og_level : r.og_level}, confirmed by the Socratic question bank signals and the confirmed NOC code.`,
            }}
            onOverride={onJesOverride}
          />
        ) : (
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
        sectionKey="drf" reviewing={reviewing}
        amendmentNote={amendmentNotes?.drf} amendmentPanel={amendmentPanels?.drf}
        onAmendToggle={onAmendToggle} onAmendSave={onAmendSave}
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

  // 6 — Qualifications (DOC-01: always render with ghost state when not visited)
  n++;
  const quals = r.quals || QUAL_DEFAULT;
  const qualsGhost = !r.qualsVisited;
  sections.push(
    <Sec
      key="q" n={String(n)} title="Essential Qualifications"
      src={qualsGhost ? null : "TBS Qualification Standard"} ghost={qualsGhost} fresh={isFresh('quals')}
      editable={reviewing} onEdit={() => onEditStep('quals')}
      sectionKey="q" reviewing={reviewing}
      amendmentNote={amendmentNotes?.q} amendmentPanel={amendmentPanels?.q}
      onAmendToggle={onAmendToggle} onAmendSave={onAmendSave}
    >
      {qualsGhost
        ? (
          <div>
            <Ghost lines={3} />
            <p className="ghost-note">Essential qualifications appear here once you have confirmed the classification.</p>
          </div>
        )
        : (
          <div>
            <p className="prose" style={{ marginBottom: 12 }}>
              <span className="qual-sub-k">EDUCATION</span>
              {quals.education}
            </p>
            <p className="prose">
              <span className="qual-sub-k">EXPERIENCE</span>
              {quals.experience}
            </p>
          </div>
        )}
    </Sec>
  );

  // provenance footer
  const provTags = [];
  if (hasDuties) provTags.push('NOC 2021');
  if (safeCls.status === 'resolved') provTags.push(safeCls.factors ? 'EC JES 2017' : safeCls.standard);
  if (safeCls.group) provTags.push('TBS OG Definitions');
  if (r.drf) provTags.push('DND DRF');
  if (r.qualsVisited) provTags.push('TBS Qualification Standard');
  if (r.duties && r.duties.some(d => d.advisor)) provTags.push('Advisor-added');
  // Phase 22 SJD-02: surface the SJD source in the provenance footer when
  // seeded duties are present. Parallel to the NOC/DRF/Advisor-added tags.
  if (r.sjd_source) provTags.push('DND SJD Library');

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

export { DocumentPane, OrphanBadge };
