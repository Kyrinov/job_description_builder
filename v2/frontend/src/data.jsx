/* ============================================================
   JD Builder — data layer
   Interview script, content, and the classification engine.
   Grounded in: NOC 2021, EC Job Evaluation Standard (2017),
   DND Departmental Results Framework.
   ============================================================ */

/* ---- icons (small, reused) ------------------------------------ */
const I = {
    spark: '<path d="M12 3l1.9 4.6L18.5 9.5 13.9 11.4 12 16l-1.9-4.6L5.5 9.5l4.6-1.9z" fill="currentColor"/>',
    check: '<path d="M4 10l4 4 8-9" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
    user: '<circle cx="10" cy="6.5" r="3.2" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M3.5 17c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
    org: '<rect x="7" y="3" width="6" height="4" rx="1" fill="none" stroke="currentColor" stroke-width="1.6"/><rect x="3" y="13" width="5" height="4" rx="1" fill="none" stroke="currentColor" stroke-width="1.6"/><rect x="12" y="13" width="5" height="4" rx="1" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M10 7v3M10 10H5.5v3M10 10h4.5v3" fill="none" stroke="currentColor" stroke-width="1.6"/>',
    compass: '<circle cx="10" cy="10" r="7.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M13 7l-1.6 4.4L7 13l1.6-4.4z" fill="currentColor"/>',
    ladder: '<path d="M6 3v14M14 3v14M6 7h8M6 11h8M6 15h8" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
    list: '<path d="M4 6h12M4 10h12M4 14h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
    flag: '<path d="M5 3v14M5 4h9l-1.6 3L14 10H5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"/>',
    cap: '<path d="M10 4l8 3.5-8 3.5-8-3.5z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M5 9v4c0 1.2 2.2 2.5 5 2.5s5-1.3 5-2.5V9" fill="none" stroke="currentColor" stroke-width="1.6"/>',
    leaf: '<path d="M16 4C9 4 4 8 4 15c5 1 12-2 12-11z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M7 13c3-3 6-4 8-4.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>',
    money: '<circle cx="10" cy="10" r="7.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M10 6v8M8 8.2c0-1 1-1.6 2-1.6s2 .6 2 1.5-1 1.3-2 1.5-2 .6-2 1.5 1 1.5 2 1.5 2-.6 2-1.4" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>',
    chip: '<rect x="5" y="5" width="10" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 2v2M12 2v2M8 16v2M12 16v2M2 8h2M2 12h2M16 8h2M16 12h2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
    gear: '<circle cx="10" cy="10" r="2.6" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M10 2v2.5M10 15.5V18M18 10h-2.5M4.5 10H2M15.7 4.3l-1.8 1.8M6.1 13.9l-1.8 1.8M15.7 15.7l-1.8-1.8M6.1 6.1L4.3 4.3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
    shield: '<path d="M10 3l6 2v5c0 4-2.6 6.4-6 7.5C6.6 16.4 4 14 4 10V5z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
    warn: '<path d="M10 3L18 17H2L10 3z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><line x1="10" y1="9" x2="10" y2="13" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="10" cy="15" r="0.8" fill="currentColor"/>'
  };

  // JS copy of OG_LEVELS from v2/backend/app/data/constants.py.
  // Avoids an API round-trip for static reference data used in og_level cfgOverride.
  const OG_LEVELS = {
    EC: [1,2,3,4,5,6,7,8],
    IT: [1,2,3,4,5],
    AS: [1,2,3,4,5,6,7,8],
    FI: [1,2,3,4],
    CR: [1,2,3,4,5,6,7],
    PM: [1,2,3,4,5,6,7],
    GT: [1,2,3,4,5,6,7,8],
    EL: [1,2,3,4,5,6,7,8,9],
    FB: [1,2,3,4,5,6,7,8],
    FS: [1,2,3,4],
    AI: [1,2,3,4,5,6,7],
    AU: [1,2,3,4,5,6],
  };

  /* ---- DND Departmental Results Framework (real data) ----------- */
  const DRF = [
    { id: 'ops', icon: I.shield, cr: 'Operations',
      result: 'Canadians are protected against threats to and attacks on Canada',
      indicators: ['% of operations that meet stated objectives', '% of force elements deployed within established timelines'] },
    { id: 'ready', icon: I.gear, cr: 'Ready Forces',
      result: 'Canadian Armed Forces are ready to conduct concurrent operations',
      indicators: ['% of force elements ready for operations against established targets', '% of military equipment serviceable for training and operations'] },
    { id: 'team', icon: I.user, cr: 'Defence Team',
      result: 'The health and well-being of the Defence Team is well supported',
      indicators: ['% of civilian employees who describe the workplace as psychologically healthy', '% of the Defence Team that reflects Canadian labour-market availability'] },
    { id: 'sustain', icon: I.leaf, cr: 'Sustainable Bases, IT Systems & Infrastructure',
      result: 'Defence activities are carried out in a safe and environmentally responsible manner',
      indicators: [
        '% of greenhouse-gas emissions reduction relative to a 2005 baseline',
        '% of reduction in contaminated-sites liability against the previous year\u2019s closing liability',
        '% of Defence Energy and Environment Strategy commitments met or exceeded'
      ], recommended: true },
    { id: 'procure', icon: I.money, cr: 'Procurement of Capabilities',
      result: 'Defence procurement is streamlined and equipment is delivered on time',
      indicators: ['% of major projects on schedule', '% of contracts awarded within established timelines'] },
    { id: 'future', icon: I.compass, cr: 'Future Force Design',
      result: 'Defence capabilities are designed to meet future threats',
      indicators: ['Degree to which capability gaps are addressed by Defence research', '% of innovation initiatives transitioned to capability'] }
  ];

  /* ---- Work-type families → occupational group ------------------ */
  const WORK_TYPES = [
    { id: 'policy', icon: I.leaf, title: 'Policy, research & environmental analysis',
      desc: 'Analyzes issues, develops options, and advises on programs or regulations',
      group: 'EC', groupName: 'Economics and Social Science Services', standard: 'EC Job Evaluation Standard (2017)', recommended: true },
    { id: 'program', icon: I.list, title: 'Program & project delivery',
      desc: 'Plans, coordinates and delivers programs, services or projects',
      group: 'EC', groupName: 'Economics and Social Science Services', standard: 'EC Job Evaluation Standard (2017)' },
    { id: 'finance', icon: I.money, title: 'Financial management',
      desc: 'Budgeting, forecasting, costing and financial advice',
      group: 'FI', groupName: 'Financial Management', standard: 'FI / CT Job Evaluation Standard (2023)' },
    { id: 'it', icon: I.chip, title: 'Information technology & data',
      desc: 'Systems, applications, data and digital services',
      group: 'IT', groupName: 'Information Technology', standard: 'IT Job Evaluation Standard' },
    { id: 'admin', icon: I.org, title: 'Administration & coordination',
      desc: 'Operational, administrative and corporate-services support',
      group: 'AS', groupName: 'Administrative Services', standard: 'AS / PA Job Evaluation Standard' },
    { id: 'eng', icon: I.gear, title: 'Engineering & technical',
      desc: 'Engineering, applied science and technical assessment',
      group: 'EN', groupName: 'Engineering', standard: 'EN Job Evaluation Standard' }
  ];

  /* ---- EC Job Evaluation Standard — 9 weighted elements --------- */
  /* degree→points scales taken verbatim from the 2017 standard.   */
  const EC_ELEMENTS = [
    { name: 'Decision making',                 cat: 'Responsibility', pts: { 1:5, 2:15, 3:35, 4:60, 5:90, 6:125, 7:165, 8:210 } },
    { name: 'Leadership & operational mgmt',   cat: 'Responsibility', pts: { 1:5, 2:20, 3:50, 4:90, 5:140 } },
    { name: 'Communication',                   cat: 'Skill',          pts: { 1:5, 2:25, 3:50, 4:75, 5:100, 6:140, 7:180 } },
    { name: 'Knowledge of specialized fields', cat: 'Skill',          pts: { 1:5, 2:15, 3:35, 4:55, 5:80, 6:105 } },
    { name: 'Contextual knowledge',            cat: 'Skill',          pts: { 1:5, 2:20, 3:40, 4:60, 5:80, 6:105 } },
    { name: 'Research & analysis',             cat: 'Skill',          pts: { 1:5, 2:30, 3:75, 4:120, 5:165, 6:210 } },
    { name: 'Physical effort',                 cat: 'Effort',         pts: { 1:3, 2:4, 3:6, 4:10, 5:15 } },
    { name: 'Sensory effort',                  cat: 'Effort',         pts: { 1:2, 2:3, 3:5, 4:10 } },
    { name: 'Working conditions',              cat: 'Conditions',     pts: { 1:5, 2:8, 3:12, 4:17, 5:25 } }
  ];
  // degree vectors per EC level (index aligns with EC_ELEMENTS)
  const EC_DEGREES = {
    'EC-04': [4, 2, 4, 4, 3, 3, 1, 2, 2],
    'EC-05': [5, 3, 5, 5, 4, 4, 1, 2, 2],
    'EC-06': [6, 4, 6, 5, 5, 5, 1, 2, 2]
  };

  function ecFactors(level) {
    const deg = EC_DEGREES[level] || EC_DEGREES['EC-05'];
    return EC_ELEMENTS.map((el, i) => ({
      name: el.name, cat: el.cat, degree: deg[i], points: el.pts[deg[i]]
    }));
  }

  // approximate totals for non-EC groups so the badge always reads sensibly
  const GENERIC_TOTALS = { FI: { 4: 470, 5: 560, 6: 660 }, IT: { 4: 480, 5: 575, 6: 690 },
                           AS: { 4: 430, 5: 510, 6: 600 }, EN: { 4: 500, 5: 600, 6: 720 } };

  /* ---- Classification engine (Phase 15 stub) --------------------- */
  /* Phase 16 will replace this with evidence-based OG ranker.     */
  /* Current logic uses prototype workType + scope scales. Stays   */
  /* referenced by app.jsx for legacy badge render; will be removed */
  /* when Phase 16 lands OgConfirmList.                            */
  function levelFromScope(r) {
    const s = (r.scopeDirection || 0) + (r.scopeAdvises || 0) + (r.scopeImpact || 0);
    if (!s) return null;
    if (s <= 4) return 4;
    if (s <= 7) return 5;
    return 6;
  }

  function computeClassification(r) {
    if (!r.workType) return { status: 'analyzing' };
    const wt = WORK_TYPES.find(w => w.id === r.workType);
    if (!wt) return { status: 'analyzing' };
    const lvNum = levelFromScope(r);
    if (!lvNum) {
      return { status: 'group', group: wt.group, groupName: wt.groupName,
               standard: wt.standard, confidence: 0.61 };
    }
    const code = `${wt.group}-0${lvNum}`;
    const vals = [r.scopeDirection, r.scopeAdvises, r.scopeImpact];
    const spread = Math.max(...vals) - Math.min(...vals);
    const confidence = Math.min(0.96, 0.99 - spread * 0.06);
    let factors = null, points;
    if (wt.group === 'EC') {
      factors = ecFactors(code);
      points = factors.reduce((a, f) => a + f.points, 0);
    } else {
      points = (GENERIC_TOTALS[wt.group] || { 5: 520 })[lvNum] || 520;
    }
    const rationale = `You described work carried out with ${['','close oversight','general direction','substantial autonomy'][r.scopeDirection]||'general direction'}, advising ${['','a supervisor','middle management','senior management'][r.scopeAdvises]||'management'}, and responsible for ${['','assigned tasks','a program or portfolio','a multi-year strategy'][r.scopeImpact]||'a program'}. That profile maps to ${code} under the ${wt.standard}.`;
    return { status: 'resolved', group: wt.group, groupName: wt.groupName,
             standard: wt.standard, code, level: lvNum, confidence, points, factors, rationale };
  }

  /* ---- Suggested duties (plain trigger → polished statement) ---- */
  /* Group-keyed so the duties match the OG group the advisor has been       */
  /* steered toward via the Socratic question bank. Falls back to a generic */
  /* set when no group is derivable (e.g. EN, unmapped NOC, or revisit with  */
  /* no answers yet). Each set covers the typical work patterns of that OG.  */
  const DUTY_SUGGESTIONS = {
    EC: [
      { plain: 'Develop and analyze policy options',
        polished: 'Develops, analyzes and interprets policy options, program frameworks and strategic guidance, and assesses their implications for departmental operations.' },
      { plain: 'Provide evidence-based advice to management',
        polished: 'Provides expert advice, options analyses and recommendations to senior management on programs, policies and emerging issues.' },
      { plain: 'Conduct research on economic or social issues',
        polished: 'Plans, leads and conducts research on economic, social, environmental or policy issues using appropriate qualitative and quantitative methods.' },
      { plain: 'Prepare briefing materials and submissions',
        polished: 'Prepares briefing materials, ministerial correspondence, cabinet documents and submissions for senior decision-makers.' },
      { plain: 'Lead or contribute to interdepartmental committees',
        polished: 'Leads or contributes to interdepartmental committees, working groups and horizontal initiatives on policy and program matters.' },
      { plain: 'Liaise with central agencies and stakeholders',
        polished: 'Manages relationships with central agencies, other departments, stakeholders and external partners to advance departmental objectives.' },
      { plain: 'Monitor and report on program performance',
        polished: 'Develops performance indicators, monitors program delivery and reports on outcomes against established targets and commitments.' }
    ],
    FI: [
      { plain: 'Develop and manage budgets and forecasts',
        polished: 'Develops, manages and monitors budgets, financial plans and forecasts in accordance with Treasury Board policies and departmental priorities.' },
      { plain: 'Prepare financial reports and analyses',
        polished: 'Prepares financial reports, costing analyses, variance explanations and recommendations for senior management and central agencies.' },
      { plain: 'Advise on financial management controls',
        polished: 'Advises management on financial management policies, internal controls, expenditure review and compliance with financial authorities.' },
      { plain: 'Review financial transactions for compliance',
        polished: 'Reviews financial transactions, commitments and expenditures to ensure accuracy, completeness and compliance with applicable authorities.' },
      { plain: 'Coordinate funding and resource allocation',
        polished: 'Coordinates funding, resource allocation and financial arrangements with central agencies, other departments and program areas.' },
      { plain: 'Support financial planning cycles',
        polished: 'Supports the departmental financial planning cycle, including estimates, main estimates, supplementary estimates and year-end closing.' },
      { plain: 'Liaise with auditors and review bodies',
        polished: 'Liaises with internal audit, the Office of the Auditor General and other review bodies on financial management matters.' }
    ],
    IT: [
      { plain: 'Design and develop software systems',
        polished: 'Designs, develops, tests and maintains software systems, applications and digital services in accordance with enterprise architecture and security standards.' },
      { plain: 'Provide technical advice and support',
        polished: 'Provides technical advice, troubleshooting support and guidance to clients, team members and stakeholders on IT systems and solutions.' },
      { plain: 'Manage IT projects and initiatives',
        polished: 'Plans, manages and delivers IT projects and initiatives, including requirements, scope, schedule, risk and stakeholder engagement.' },
      { plain: 'Ensure data quality and integrity',
        polished: 'Implements controls and processes to ensure the quality, integrity, security and availability of data and information assets.' },
      { plain: 'Analyze requirements and propose solutions',
        polished: 'Analyzes business requirements, evaluates options and proposes technical solutions that meet user needs and align with enterprise standards.' },
      { plain: 'Document technical designs and procedures',
        polished: 'Documents technical designs, configurations, operating procedures and user guides to support the maintainability and continuity of IT services.' },
      { plain: 'Coordinate with stakeholders on requirements',
        polished: 'Coordinates with clients, stakeholders and vendors to elicit, refine and validate requirements throughout the project lifecycle.' }
    ],
    AS: [
      { plain: 'Coordinate administrative and operational services',
        polished: 'Coordinates and delivers administrative, operational and corporate services in support of program delivery and organizational objectives.' },
      { plain: 'Manage logistics, scheduling and resources',
        polished: 'Manages logistics, scheduling, workspace, equipment and resources to support the effective operation of the unit or program.' },
      { plain: 'Prepare correspondence and briefing materials',
        polished: 'Prepares correspondence, briefing materials, meeting agendas and minutes for management and stakeholders.' },
      { plain: 'Maintain records and information systems',
        polished: 'Maintains records, files, databases and information management systems to ensure the integrity, accessibility and confidentiality of information.' },
      { plain: 'Liaise with internal and external stakeholders',
        polished: 'Liaises with internal and external stakeholders, clients and partners to coordinate activities, exchange information and resolve issues.' },
      { plain: 'Support program and service delivery',
        polished: 'Provides operational and administrative support for program and service delivery, including intake, processing and follow-up activities.' },
      { plain: 'Organize meetings, events and travel',
        polished: 'Organizes meetings, events, conferences and travel arrangements, including logistics, materials, hospitality and expense reconciliation.' }
    ],
    default: [
      { plain: 'Develop and deliver work products',
        polished: 'Develops and delivers work products, analyses and recommendations in support of the unit\u2019s mandate and objectives.' },
      { plain: 'Provide advice to stakeholders',
        polished: 'Provides advice, guidance and recommendations to management, colleagues and stakeholders on issues within the area of responsibility.' },
      { plain: 'Coordinate with internal and external partners',
        polished: 'Coordinates with internal and external partners to advance shared objectives, exchange information and resolve issues.' },
      { plain: 'Prepare reports and briefing materials',
        polished: 'Prepares reports, briefing materials, correspondence and other documents to support decision-making and communication.' },
      { plain: 'Represent the department in meetings',
        polished: 'Represents the department in meetings, committees and working groups on matters within the area of responsibility.' },
      { plain: 'Monitor and report on key metrics',
        polished: 'Monitors and reports on key performance indicators, project status and program outcomes against established targets.' },
      { plain: 'Support team and organizational objectives',
        polished: 'Supports team and organizational objectives through collaboration, knowledge-sharing and contribution to a positive work environment.' }
    ]
  };

  /* Resolve the OG group from the advisor's Socratic answers and return the  */
  /* matching duty set. Used by the duties step so suggestions are not the  */
  /* hardcoded environmental set from the prototype.                        */
  function getDutySuggestions(answers) {
    const sig = typeof accumulateSignals === 'function' ? accumulateSignals(answers) : null;
    const group = sig && sig.dominant;
    if (group && DUTY_SUGGESTIONS[group]) return DUTY_SUGGESTIONS[group];
    return DUTY_SUGGESTIONS.default;
  }

  /* refine a manager's plain words into a formal duty statement */
  const VERB_MAP = {
    'clean up': 'Remediates', 'cleanup': 'Remediates', 'deal with': 'Manages', 'handle': 'Administers',
    'write': 'Prepares', 'writing': 'Prepares', 'help': 'Supports', 'make sure': 'Ensures',
    'talk to': 'Liaises with', 'look after': 'Oversees', 'run': 'Leads', 'track': 'Monitors and reports on',
    'manage': 'Manages', 'lead': 'Leads', 'develop': 'Develops', 'provide': 'Provides',
    'coordinate': 'Coordinates', 'organise': 'Coordinates', 'organize': 'Coordinates',
    'review': 'Reviews', 'plan': 'Plans', 'deliver': 'Delivers', 'advise': 'Advises',
    'analyse': 'Analyzes', 'analyze': 'Analyzes', 'oversee': 'Oversees', 'prepare': 'Prepares',
    'maintain': 'Maintains', 'support': 'Supports', 'monitor': 'Monitors', 'assess': 'Assesses',
    'build': 'Develops', 'create': 'Develops', 'fix': 'Resolves', 'check': 'Verifies'
  };
  function refineDuty(raw) {
    let t = (raw || '').trim().replace(/\s+/g, ' ');
    if (!t) return '';
    const low = t.toLowerCase();
    for (const k of Object.keys(VERB_MAP)) {
      if (low.startsWith(k + ' ')) {
        const rest = t.slice(k.length).trim();
        let out = VERB_MAP[k] + ' ' + rest;
        if (!/[.!?]$/.test(out)) out += '.';
        return out.charAt(0).toUpperCase() + out.slice(1);
      }
    }
    // no recognised leading verb → wrap formally
    let out = 'Performs duties related to ' + low;
    if (!/[.!?]$/.test(out)) out += '.';
    return out;
  }

  /* ---- Qualification standard (EC-05 default) ------------------- */
  const QUAL_DEFAULT = {
    education: 'Graduation with a degree from a recognized post-secondary institution with specialization in environmental science, economics, public policy or a discipline relevant to the position.',
    experience: 'Significant* experience in environmental program or policy analysis, including providing advice and recommendations to management. (*Significant = depth and breadth normally acquired over approximately three years.)'
  };

  /* ---- Signal accumulation from QUESTION_BANK answers ----------- */
  /* Pure derived function — never persisted to record or backend.   */
  function accumulateSignals(answers) {
    const qbStepIds = [
      'qb_work_output_type', 'qb_work_audience',
      'qb_knowledge_specialization', 'qb_policy_interpretation',
    ];
    const tally = {};
    for (const stepId of qbStepIds) {
      const ans = answers[stepId];
      if (!ans || !ans.signals) continue;
      for (const ogCode of (ans.signals.og_candidates || [])) {
        tally[ogCode] = (tally[ogCode] || 0) + 1;
      }
    }
    const sorted = Object.entries(tally).sort((a, b) => b[1] - a[1]);
    return sorted.length > 0 ? { dominant: sorted[0][0], tally } : null;
  }

  /* ============================================================
     The interview script — v2.0 6-phase conversational flow.
     ============================================================ */
  const STEPS = [
    /* ----- Phase 0: Role ----- */
    { id: 'title',   phase: 0, icon: I.user, q: 'What is the job title for this position?', helper: 'Use the official or working title — you can refine it later.', input: { type: 'text', placeholder: 'e.g. Senior Policy Analyst', preset: '' }, apply: (r, a) => ({ title: a }), transcript: a => a },
    { id: 'branch',  phase: 0, icon: I.org,  q: 'Which branch or directorate does this position sit within?', helper: 'e.g. Strategic Policy Branch, ADM(Mat)', input: { type: 'text', placeholder: 'e.g. Strategic Policy Branch', preset: '' }, apply: (r, a) => ({ branch: a }), transcript: a => a },
    { id: 'reports', phase: 0, icon: I.ladder, q: 'Who does this position report to?', helper: 'Use the title of the direct supervisor — e.g. Director General, Strategic Policy', input: { type: 'text', placeholder: 'e.g. Director, Policy Development', preset: '' }, apply: (r, a) => ({ reports: a }), transcript: a => a },
    { id: 'reports_to_military', phase: 0, icon: I.shield,
      q: 'Does this position report to a military officer?',
      helper: 'This determines whether CAF rank equivalence information is displayed in the final document.',
      input: { type: 'choices', options: [
        { id: 'yes', title: 'Yes — reports to a military officer' },
        { id: 'no', title: 'No — reports to a civilian supervisor' },
      ] },
      apply: (r, a) => ({ reports_to_military: a.id === 'yes' }),
      transcript: a => a ? a.title : 'Pending' },
    { id: 'supervises', phase: 0, icon: I.user, q: 'Will this person supervise or lead others?', helper: 'This helps us gauge the level of responsibility.', input: { type: 'choices', options: [{ id: 'none', title: 'No — individual contributor' }, { id: 'few', title: 'Leads 1–3 people or a small team' }, { id: 'team', title: 'Manages a team of 4–10' }, { id: 'many', title: 'Leads multiple teams' }] }, apply: (r, a) => ({ supervises: a.title }), transcript: a => a.title },

    /* ----- Phase 1: Work Type (QUESTION_BANK-driven) ----- */
    { id: 'summary', phase: 1, icon: I.spark, q: 'Describe the primary work of this position in your own words.', helper: 'A few sentences is enough. Focus on what the person actually does, not the org chart.', input: { type: 'textarea', placeholder: 'e.g. Develops and coordinates departmental policy on environmental regulations; provides briefings to senior leadership; manages relationships with central agencies.' }, apply: (r, a) => ({ summary: a }), transcript: a => a },
    { id: 'qb_work_output_type', phase: 1, icon: I.list,
      q: 'What best describes the main type of output this person produces?',
      helper: 'Think about what they actually deliver — not their title.',
      input: { type: 'choices', options: [
        { id: 'analysis_advice', title: 'Analysis, options, or recommendations for decision-makers', signals: { og_candidates: ['EC'], jes_factor_hints: ['Research & analysis', 'Decision making'], teer_affinity: [1, 2] } },
        { id: 'financial_reports', title: 'Financial plans, budgets, or costing reports', signals: { og_candidates: ['FI'], jes_factor_hints: ['Knowledge of specialized fields'], teer_affinity: [1, 2] } },
        { id: 'systems_data', title: 'Systems, applications, or digital services', signals: { og_candidates: ['IT'], jes_factor_hints: ['Knowledge of specialized fields'], teer_affinity: [1, 2] } },
        { id: 'admin_coordination', title: 'Administrative coordination, logistics, or operational support', signals: { og_candidates: ['AS'], jes_factor_hints: ['Leadership & operational mgmt'], teer_affinity: [2, 3, 4] } },
      ] },
      apply: (r, a) => ({ qb_work_output_type: a.id }),
      transcript: a => a.title },
    { id: 'qb_work_audience', phase: 1, icon: I.user,
      q: 'Who primarily uses or acts on what this person produces?',
      helper: 'Consider who would be worse off if this person stopped producing their work.',
      input: { type: 'choices', options: [
        { id: 'senior_mgmt_decisions', title: 'Senior management, for decisions or briefings', signals: { og_candidates: ['EC', 'FI'], jes_factor_hints: ['Communication', 'Decision making'], teer_affinity: [1, 2] } },
        { id: 'operational_teams', title: 'Operational teams and staff working within the organization', signals: { og_candidates: ['AS', 'IT'], jes_factor_hints: ['Leadership & operational mgmt'], teer_affinity: [2, 3] } },
        { id: 'external_stakeholders', title: 'External stakeholders, partner organizations, or the public', signals: { og_candidates: ['EC'], jes_factor_hints: ['Communication', 'Research & analysis'], teer_affinity: [1, 2] } },
      ] },
      apply: (r, a) => ({ qb_work_audience: a.id }),
      transcript: a => a.title },
    { id: 'qb_knowledge_specialization', phase: 1, icon: I.cap,
      q: 'How specialized is the knowledge this role requires?',
      helper: 'Focus on the depth of expertise, not the number of tasks.',
      input: { type: 'choices', options: [
        { id: 'deep_policy_science', title: 'Deep expertise in a field such as economics, environmental science, or public policy', signals: { og_candidates: ['EC'], jes_factor_hints: ['Knowledge of specialized fields', 'Contextual knowledge'], teer_affinity: [1, 2] } },
        { id: 'deep_finance_accounting', title: 'Deep expertise in accounting, financial systems, or budget management', signals: { og_candidates: ['FI'], jes_factor_hints: ['Knowledge of specialized fields'], teer_affinity: [1, 2] } },
        { id: 'deep_technology', title: 'Deep expertise in software development, infrastructure, or data systems', signals: { og_candidates: ['IT'], jes_factor_hints: ['Knowledge of specialized fields'], teer_affinity: [1, 2] } },
        { id: 'general_admin_skills', title: 'General organizational, administrative, and coordination skills', signals: { og_candidates: ['AS'], jes_factor_hints: ['Leadership & operational mgmt'], teer_affinity: [2, 3, 4] } },
      ] },
      apply: (r, a) => ({ qb_knowledge_specialization: a.id }),
      transcript: a => a.title },
    { id: 'qb_policy_interpretation', phase: 1, icon: I.flag,
      q: 'Does this person develop, interpret, or apply rules, policies, or standards?',
      helper: 'Select the option that best describes their primary relationship with rules and policy.',
      input: { type: 'choices', options: [
        { id: 'develops_policy', title: 'Develops or shapes policy, regulations, or strategic guidance', signals: { og_candidates: ['EC'], jes_factor_hints: ['Research & analysis', 'Contextual knowledge'], teer_affinity: [1, 2] } },
        { id: 'applies_financial_standards', title: 'Applies financial accounting standards, costing frameworks, or audit procedures', signals: { og_candidates: ['FI'], jes_factor_hints: ['Knowledge of specialized fields'], teer_affinity: [1, 2] } },
        { id: 'administers_established', title: 'Administers or implements established procedures and operational processes', signals: { og_candidates: ['AS', 'IT'], jes_factor_hints: ['Leadership & operational mgmt'], teer_affinity: [2, 3, 4] } },
      ] },
      apply: (r, a) => ({ qb_policy_interpretation: a.id }),
      transcript: a => a.title },

    /* ----- Phase 2: Classification ----- */
    { id: 'noc_confirm', phase: 2, icon: I.compass,
      q: 'Review the top NOC matches and confirm the best fit for this role.',
      helper: 'Select the NOC code that best describes the work.',
      input: { type: 'noc_confirm', candidates: [] },
      apply: (r, a) => ({ confirmed_noc: a }),
      transcript: a => a ? (a.noc_code + ' — ' + a.title) : 'Pending' },

    { id: 'og_confirm', phase: 2, icon: I.compass,
      q: 'Review the top occupational group matches and confirm the best fit.',
      helper: 'Select the occupational group that best fits the work described.',
      input: { type: 'og_confirm', candidates: [] },
      apply: (r, a) => ({ confirmed_og: a }),
      transcript: a => a ? (a.og_code + ' — ' + a.og_name) : 'Pending' },

    { id: 'og_level', phase: 2, icon: I.ladder,
      q: 'Select the level for this position.',
      helper: 'Level ranges are derived from the collective agreement for the confirmed occupational group.',
      input: { type: 'og_level', levels: [] },
      apply: (r, a) => ({ og_level: a }),
      transcript: a => a !== null && a !== undefined ? String(a) : 'Pending' },

    /* ----- Phase 3: Duties ----- */
    { id: 'duties', phase: 3, icon: I.list,
      q: 'Here are the responsibilities managers usually pick for a role like this.',
      helper: 'Tick the ones that fit, and add anything in your own words — we\u2019ll phrase them formally for you.',
      input: { type: 'duties' },
      apply: (r, a) => ({ duties: a }),
      transcript: a => `${a.length} ${a.length === 1 ? 'responsibility' : 'responsibilities'}` },

    /* ----- Phase 4: Qualifications ----- */
    { id: 'quals', phase: 4, icon: I.cap,
      q: 'Last step — here are the essential qualifications for this level.',
      helper: 'Pre-filled from the qualification standard for the classification. Edit anything that doesn\u2019t fit.',
      input: { type: 'quals' },
      apply: (r, a) => ({ quals: a }),
      transcript: () => 'Reviewed' }
  ];

const PHASES = ['Role', 'Work Type', 'Classification', 'Duties', 'Qualifications', 'Review'];

export {
  I, STEPS, PHASES, OG_LEVELS, DRF, WORK_TYPES, DUTY_SUGGESTIONS, QUAL_DEFAULT,
  EC_ELEMENTS, computeClassification, refineDuty, ecFactors,
  accumulateSignals, getDutySuggestions,
};
