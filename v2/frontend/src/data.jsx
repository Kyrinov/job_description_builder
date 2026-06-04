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
    gear: '<circle cx="10" cy="10" r="2.6" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M10 2v2.5M10 15.5V18M18 10h-2.5M4.5 10H2M15.7 4.3l-1.8 1.8M6.1 13.9l-1.8 1.8M15.7 15.7l-1.8-1.8M6.1 6.1L4.3 4.3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
    shield: '<path d="M10 3l6 2v5c0 4-2.6 6.4-6 7.5C6.6 16.4 4 14 4 10V5z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>'
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

  /* ---- Classification engine ------------------------------------ */
  // weights carried on scope answers
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
    const lvNum = levelFromScope(r);
    if (!lvNum) {
      return { status: 'group', group: wt.group, groupName: wt.groupName,
               standard: wt.standard, confidence: 0.61 };
    }
    const code = `${wt.group}-0${lvNum}`;
    // confidence rises when scope answers are consistent (low spread)
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
  const DUTY_SUGGESTIONS = [
    { plain: 'Clean up contaminated sites',
      polished: 'Plans, leads and delivers environmental assessment and remediation projects at defence establishments, ensuring compliance with federal environmental legislation.' },
    { plain: 'Advise leadership on environmental risk',
      polished: 'Provides expert advice and recommendations to senior management on environmental risks, contaminated-sites liability, and greenhouse-gas reduction strategies.' },
    { plain: 'Develop environmental policy & standards',
      polished: 'Develops, analyzes and interprets environmental policies, standards and program frameworks, and assesses their implications for departmental operations.' },
    { plain: 'Work with regulators and communities',
      polished: 'Manages relationships with regulatory authorities, Indigenous communities and stakeholders to support the department\u2019s environmental obligations.' },
    { plain: 'Write briefings for senior decision-makers',
      polished: 'Prepares briefing materials, options analyses and reports for senior decision-makers, translating complex technical findings into clear recommendations.' },
    { plain: 'Track and report on emissions targets',
      polished: 'Monitors and reports on environmental performance indicators \u2014 including emissions reduction and contaminated-sites liability \u2014 against departmental targets.' },
    { plain: 'Represent DND on working groups',
      polished: 'Leads or contributes to multidisciplinary working groups and represents the department in interdepartmental environmental initiatives.' }
  ];

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

  /* ============================================================
     The interview script
     ============================================================ */
  const STEPS = [
    /* ----- Phase 1: Role ----- */
    { id: 'title', phase: 0, icon: I.user,
      q: 'Let\u2019s build this job description together. What\u2019s the role you\u2019re hiring for?',
      helper: 'Just a working title in plain words \u2014 we\u2019ll handle the official classification for you.',
      input: { type: 'text', placeholder: 'e.g. Environmental Officer', preset: 'Environmental Officer' },
      apply: (r, a) => ({ title: a }),
      transcript: a => a },

    { id: 'branch', phase: 0, icon: I.org,
      q: r => `Which team will the ${r.title || 'new hire'} join?`,
      helper: 'The branch or directorate they\u2019ll work in.',
      input: { type: 'text', placeholder: 'e.g. Real Property Operations \u2014 Environmental Services', preset: 'Real Property Operations \u2014 Environmental Services' },
      apply: (r, a) => ({ branch: a }),
      transcript: a => a },

    { id: 'reports', phase: 0, icon: I.ladder,
      q: 'Who will this position report to?',
      helper: 'The supervisor\u2019s title is enough.',
      input: { type: 'text', placeholder: 'e.g. Manager, Environmental Services', preset: 'Manager, Environmental Services' },
      apply: (r, a) => ({ reports: a }),
      transcript: a => a },

    { id: 'supervises', phase: 0, icon: I.user,
      q: 'Will this person supervise or lead others?',
      helper: 'This helps us gauge the level of responsibility.',
      input: { type: 'choices', options: [
        { id: 'none', title: 'No \u2014 individual contributor' },
        { id: 'few', title: 'Leads 1\u20133 people or a small team' },
        { id: 'team', title: 'Manages a team of 4\u201310' },
        { id: 'many', title: 'Leads multiple teams' }
      ]},
      apply: (r, a) => ({ supervises: a.title }),
      transcript: a => a.title },

    /* ----- Phase 2: Focus ----- */
    { id: 'summary', phase: 1, icon: I.compass,
      q: r => `In a sentence or two, what is the ${r.title || 'role'} mostly about?`,
      helper: 'Plain language is perfect. We\u2019ll turn this into a polished position overview.',
      input: { type: 'textarea', placeholder: 'e.g. Leads environmental cleanup and advises the base on meeting federal environmental rules and emissions targets.',
               preset: 'Leads environmental assessment and cleanup projects across defence sites, and advises leadership on meeting federal environmental rules and emissions targets.' },
      apply: (r, a) => ({ summary: a }),
      transcript: a => a.length > 60 ? a.slice(0, 60) + '\u2026' : a },

    { id: 'workType', phase: 1, icon: I.list,
      q: 'Which best describes the main type of work?',
      helper: 'This is how we find the right occupational group \u2014 the public-service family this job belongs to.',
      input: { type: 'choices', source: 'workTypes' },
      apply: (r, a) => ({ workType: a.id }),
      transcript: a => a.title },

    /* ----- Phase 3: Scope / level ----- */
    { id: 'scopeDirection', phase: 2, icon: I.ladder,
      q: 'Day to day, how much direction does this person work under?',
      helper: 'There are no wrong answers \u2014 this is one of three questions that set the level.',
      input: { type: 'scale', ends: ['Lots of guidance', 'Highly independent'], options: [
        { v: 1, lbl: 'Regular supervision' },
        { v: 2, lbl: 'General direction' },
        { v: 3, lbl: 'Sets own objectives' }
      ]},
      apply: (r, a) => ({ scopeDirection: a.v }),
      transcript: a => a.lbl },

    { id: 'scopeAdvises', phase: 2, icon: I.compass,
      q: 'When this person makes a recommendation, who acts on it?',
      helper: 'This tells us how far their advice reaches.',
      input: { type: 'scale', ends: ['Stays local', 'Reaches the top'], options: [
        { v: 1, lbl: 'Supervisor reviews it' },
        { v: 2, lbl: 'Middle management' },
        { v: 3, lbl: 'Senior management (DG+)' }
      ]},
      apply: (r, a) => ({ scopeAdvises: a.v }),
      transcript: a => a.lbl },

    { id: 'scopeImpact', phase: 2, icon: I.flag,
      q: 'What\u2019s the biggest thing this person is responsible for?',
      helper: 'The scope of what could go right \u2014 or wrong \u2014 on their watch.',
      input: { type: 'scale', ends: ['Focused', 'Far-reaching'], options: [
        { v: 1, lbl: 'A set of assigned tasks' },
        { v: 2, lbl: 'A program or project portfolio' },
        { v: 3, lbl: 'A multi-year strategy / budget' }
      ]},
      apply: (r, a) => ({ scopeImpact: a.v }),
      transcript: a => a.lbl },

    /* ----- Phase 4: Responsibilities ----- */
    { id: 'duties', phase: 3, icon: I.list,
      q: 'Here are the responsibilities managers usually pick for a role like this.',
      helper: 'Tick the ones that fit, and add anything in your own words \u2014 we\u2019ll phrase them formally for you.',
      input: { type: 'duties' },
      apply: (r, a) => ({ duties: a }),
      transcript: a => `${a.length} ${a.length === 1 ? 'responsibility' : 'responsibilities'}` },

    /* ----- Phase 5: Mission ----- */
    { id: 'drf', phase: 4, icon: I.shield,
      q: 'Which part of National Defence\u2019s mission does this role support?',
      helper: 'We\u2019ll link the position to the right Departmental Result \u2014 a requirement for DND positions.',
      input: { type: 'drf' },
      apply: (r, a) => ({ drf: a }),
      transcript: a => a.cr },

    /* ----- Phase 6: Qualifications then review ----- */
    { id: 'quals', phase: 5, icon: I.cap,
      q: 'Last step \u2014 here are the essential qualifications for this level.',
      helper: 'Pre-filled from the qualification standard for the classification. Edit anything that doesn\u2019t fit.',
      input: { type: 'quals' },
      apply: (r, a) => ({ quals: a }),
      transcript: () => 'Reviewed' }
  ];

const PHASES = ['Role', 'Focus', 'Level', 'Duties', 'Mission', 'Review'];

export {
  I, STEPS, PHASES, DRF, WORK_TYPES, DUTY_SUGGESTIONS, QUAL_DEFAULT,
  EC_ELEMENTS, computeClassification, refineDuty, ecFactors
};
