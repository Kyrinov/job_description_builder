# Source: verified against data/rates_of_pay/*.csv (direct file inspection 2026-06-04)
# and data/CAF pay grades (single text file, effective April 1, 2025)
# See .planning/phases/11-data-foundation/11-RESEARCH.md for full verification log.

"""
app/data/constants.py — Authoritative data constants for v2.0.

OG_LEVELS: maps OG code -> list of level integers (1-indexed), derived from
    data/rates_of_pay/ CSV files. Corrects v1.0 errors: EC was 1-7 (now 1-8),
    IT was 1-4 (now 1-5), CS key removed (CS merged into IT).

CAF_RANK_OG_EQUIVALENCE: maps CAF rank name -> approximate civilian OG equivalents.
    ADVISORY ONLY — NOT AUTHORITATIVE. Derived by pay-band comparison from
    data/CAF pay grades (effective April 1, 2025). Label as
    "advisory - not authoritative" on all surfaces that display this table.

KNOWN_JES_FACTORS: frozenset of the 9 canonical EC JES factor name strings (use & not "and").
QUESTION_BANK: list of Socratic work-type question entries; drives Phase 15 conversation flow.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# OG_LEVELS
# Correct OG level ranges derived from data/rates_of_pay/ CSV files.
# Key: OG group code (string). Value: list of level integers (1-indexed).
#
# V1.0 bugs corrected here:
#   EC: was range(1, 8) = [1..7], now range(1, 9) = [1..8]  (EC-01 to EC-08)
#   IT: was range(1, 5) = [1..4], now range(1, 6) = [1..5]  (IT-01 to IT-05)
#   CS: removed — CS is not a current standalone OG group (merged into IT)
#   CR: was range(1, 7) = [1..6], now range(1, 8) = [1..7]  (CR-1 to CR-7)
#   PM: was range(1, 7) = [1..6], now range(1, 8) = [1..7]  (PM-1 to PM-7)
# ---------------------------------------------------------------------------

OG_LEVELS: dict[str, list[int]] = {
    # Focus groups for v2.0 OG classification (EC, IT, AS, FI)
    "EC": list(range(1, 9)),   # EC-01 to EC-08 — EC_rates.csv
    "IT": list(range(1, 6)),   # IT-01 to IT-05 — IT_CS_rates.csv (CS merged into IT)
    "AS": list(range(1, 9)),   # AS-1 to AS-8 — PA_rates.csv (PA collective agreement)
    "FI": list(range(1, 5)),   # FI-01 to FI-04 — CT_FI_rates.csv (internally CT-FIN; OG code remains FI)
    # Additional groups from confirmed CSV inspection
    "CR": list(range(1, 8)),   # CR-1 to CR-7 — PA_rates.csv
    "PM": list(range(1, 8)),   # PM-1 to PM-7 — PA_rates.csv
    "GT": list(range(1, 9)),   # GT-1 to GT-8 — TC_rates.csv
    "EL": list(range(1, 10)),  # EL-01 to EL-09 — EL_rates.csv
    "FB": list(range(1, 9)),   # FB-1 to FB-8 — FB_rates.csv
    "FS": list(range(1, 5)),   # FS-01 to FS-04 — FS_rates.csv
    "AI": list(range(1, 8)),   # AI-01 to AI-07 — AI_rates.csv
    "AU": list(range(1, 7)),   # AU-01 to AU-06 — CT_FI_rates.csv (internally CT-EAV; OG code remains AU)
}


# ---------------------------------------------------------------------------
# CAF_RANK_OG_EQUIVALENCE
# ADVISORY ONLY — NOT AUTHORITATIVE.
# Derived by annual pay-band comparison, effective April 1, 2025.
# Monthly pay * 12 compared to Step 1 to max-step of civilian OG levels (D-row rates).
# Source: data/CAF pay grades (single UTF-8 text file, verified 2026-06-04).
#
# Officer pay level D used as the representative anchor for general duty officers
# (most common general duty officer track). Documented choice per RESEARCH.md A4.
#
# approx_civilian_og_levels entries must use codes that exist in OG_LEVELS above.
# ---------------------------------------------------------------------------

CAF_RANK_OG_EQUIVALENCE: dict[str, dict] = {
    "Private / Sailor 2nd or 3rd Class": {
        "approx_annual_pay_cad": (52044, 71928),
        "approx_civilian_og_levels": ["AS-01", "CR-01", "CR-02"],
        "advisory": True,
        "note": "Entry-level NCM; pay band overlaps AS-01 ($61,632 Step 1) and CR-01/02 ranges.",
    },
    "Corporal / Sailor 1st Class (Standard)": {
        "approx_annual_pay_cad": (82296, 88044),
        "approx_civilian_og_levels": ["AS-03", "AS-04"],
        "advisory": True,
        "note": "Standard Cpl/S1 pay band overlaps AS-03 to AS-04 range.",
    },
    "Corporal / Sailor 1st Class (Specialist 1)": {
        "approx_annual_pay_cad": (91272, 96852),
        "approx_civilian_og_levels": ["AS-04", "AS-05"],
        "advisory": True,
        "note": "Spc1 pay band overlaps upper AS-04 and lower AS-05.",
    },
    "Corporal / Sailor 1st Class (Specialist 2)": {
        "approx_annual_pay_cad": (97656, 103632),
        "approx_civilian_og_levels": ["AS-05", "AS-06"],
        "advisory": True,
        "note": "Spc2 pay band overlaps AS-05 to AS-06 range.",
    },
    "Master Corporal / Master Sailor (Standard)": {
        "approx_annual_pay_cad": (85416, 94092),
        "approx_civilian_og_levels": ["AS-04", "AS-05"],
        "advisory": True,
        "note": "MCpl/MS pay band overlaps AS-04 ($80,411 Step 1) to AS-05.",
    },
    "Sergeant / Petty Officer 2nd Class (Standard)": {
        "approx_annual_pay_cad": (95508, 100080),
        "approx_civilian_og_levels": ["AS-05", "AS-06"],
        "advisory": True,
        "note": "Sgt/PO2 pay band overlaps AS-05 to lower AS-06.",
    },
    "Warrant Officer / Petty Officer 1st Class (Standard)": {
        "approx_annual_pay_cad": (104328, 107964),
        "approx_civilian_og_levels": ["AS-07"],
        "advisory": True,
        "note": "WO/PO1 pay band ($104k-$108k) falls within AS-07 range; EC-05 low end also overlaps.",
    },
    "Master Warrant Officer / Chief Petty Officer 2nd Class (Standard)": {
        "approx_annual_pay_cad": (116016, 120684),
        "approx_civilian_og_levels": ["AS-08"],
        "advisory": True,
        "note": "MWO/CPO2 pay band overlaps AS-08 low end ($116,218 Step 1) and EC-06 low end.",
    },
    "Chief Warrant Officer / Chief Petty Officer 1st Class": {
        "approx_annual_pay_cad": (126744, 146916),
        "approx_civilian_og_levels": ["AS-08", "EC-07", "EC-08"],
        "advisory": True,
        "note": "CWO/CPO1 pay range A/B/C spans $127k-$147k; overlaps AS-08 max and EC-07 to EC-08 low.",
    },
    "Second Lieutenant / Acting Sub-Lieutenant (pay levels D-E)": {
        "approx_annual_pay_cad": (84000, 114168),
        "approx_civilian_og_levels": ["AS-04", "AS-05", "AS-06", "AS-07", "AS-08"],
        "advisory": True,
        "note": "2Lt/A/SLt spans wide band (pay levels A-E); D/E levels used as anchor ($84k-$114k).",
    },
    "Lieutenant / Sub-Lieutenant (pay levels D-E)": {
        "approx_annual_pay_cad": (86000, 132684),
        "approx_civilian_og_levels": ["AS-05", "AS-06", "AS-07", "AS-08", "EC-07"],
        "advisory": True,
        "note": "Lt/SLt spans $65k-$133k across all pay levels; D/E anchor overlaps AS-05 to EC-07 low.",
    },
    "Captain / Lieutenant (Navy)": {
        "approx_annual_pay_cad": (106332, 140544),
        "approx_civilian_og_levels": ["EC-06", "EC-07", "EC-08"],
        "advisory": True,
        "note": "Capt/Lt(N) pay ($106k-$141k) overlaps EC-06 ($113,278 Step 1) to EC-08 low.",
    },
    "Major / Lieutenant-Commander": {
        "approx_annual_pay_cad": (143796, 161220),
        "approx_civilian_og_levels": ["EC-08"],
        "advisory": True,
        "note": "Maj/LCdr pay ($144k-$161k) is at EC-08 max range ($139,155-$159,046); IT-05 low end also overlaps.",
    },
    "Lieutenant-Colonel / Commander": {
        "approx_annual_pay_cad": (166644, 177348),
        "approx_civilian_og_levels": ["IT-05"],
        "advisory": True,
        "note": "LCol/Cdr pay ($167k-$177k) falls in IT-05 mid-range ($133,249-$173,642).",
    },
}


# ---------------------------------------------------------------------------
# KNOWN_JES_FACTORS
# Canonical JES factor names from EC JES 2017 (verified against EC_ELEMENTS in
# Job Description Builder/jd-builder/data.jsx). Used by test_question_bank.py
# to cross-reference jes_factor_hints in QUESTION_BANK signals.
# Key: N/A (frozenset). Value: exact factor name strings — use & not "and".
# ---------------------------------------------------------------------------

KNOWN_JES_FACTORS: frozenset[str] = frozenset({
    "Decision making",
    "Leadership & operational mgmt",
    "Communication",
    "Knowledge of specialized fields",
    "Contextual knowledge",
    "Research & analysis",
    "Physical effort",
    "Sensory effort",
    "Working conditions",
})


# ---------------------------------------------------------------------------
# QUESTION_BANK
# Socratic work-description questions that drive the work_type conversation phase.
# Each entry elicits a natural-language description from the manager; OG group
# is derived from accumulated signals, never directly selected by the user.
# QUES-02 constraint: OG codes must not appear in "question", "helper", or
# options[].label — only inside signals.og_candidates.
# Source: designed for v2.0; signals verified against OG_LEVELS and KNOWN_JES_FACTORS.
# Key: list index. Value: question entry dict with id, phase_slot, question,
#   helper, input_type, options (each option has id, label, signals).
# ---------------------------------------------------------------------------

QUESTION_BANK: list[dict] = [
    {
        "id": "work_output_type",
        "phase_slot": "work_type",
        "question": "What best describes the main type of output this person produces?",
        "helper": "Think about what they actually deliver — not their title.",
        "input_type": "choices",
        "options": [
            {
                "id": "analysis_advice",
                "label": "Analysis, options, or recommendations for decision-makers",
                "signals": {
                    "og_candidates": ["EC"],
                    "jes_factor_hints": ["Research & analysis", "Decision making"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "financial_reports",
                "label": "Financial plans, budgets, or costing reports",
                "signals": {
                    "og_candidates": ["FI"],
                    "jes_factor_hints": ["Knowledge of specialized fields"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "systems_data",
                "label": "Systems, applications, or digital services",
                "signals": {
                    "og_candidates": ["IT"],
                    "jes_factor_hints": ["Knowledge of specialized fields"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "admin_coordination",
                "label": "Administrative coordination, logistics, or operational support",
                "signals": {
                    "og_candidates": ["AS"],
                    "jes_factor_hints": ["Leadership & operational mgmt"],
                    "teer_affinity": [2, 3, 4],
                },
            },
        ],
    },
    {
        "id": "work_audience",
        "phase_slot": "work_type",
        "question": "Who primarily uses or acts on what this person produces?",
        "helper": "Consider who would be worse off if this person stopped producing their work.",
        "input_type": "choices",
        "options": [
            {
                "id": "senior_mgmt_decisions",
                "label": "Senior management, for decisions or briefings",
                "signals": {
                    "og_candidates": ["EC", "FI"],
                    "jes_factor_hints": ["Communication", "Decision making"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "operational_teams",
                "label": "Operational teams and staff working within the organization",
                "signals": {
                    "og_candidates": ["AS", "IT"],
                    "jes_factor_hints": ["Leadership & operational mgmt"],
                    "teer_affinity": [2, 3],
                },
            },
            {
                "id": "external_stakeholders",
                "label": "External stakeholders, partner organizations, or the public",
                "signals": {
                    "og_candidates": ["EC"],
                    "jes_factor_hints": ["Communication", "Research & analysis"],
                    "teer_affinity": [1, 2],
                },
            },
        ],
    },
    {
        "id": "knowledge_specialization",
        "phase_slot": "work_type",
        "question": "How specialized is the knowledge this role requires?",
        "helper": "Focus on the depth of expertise, not the number of tasks.",
        "input_type": "choices",
        "options": [
            {
                "id": "deep_policy_science",
                "label": "Deep expertise in a field such as economics, environmental science, or public policy",
                "signals": {
                    "og_candidates": ["EC"],
                    "jes_factor_hints": ["Knowledge of specialized fields", "Contextual knowledge"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "deep_finance_accounting",
                "label": "Deep expertise in accounting, financial systems, or budget management",
                "signals": {
                    "og_candidates": ["FI"],
                    "jes_factor_hints": ["Knowledge of specialized fields"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "deep_technology",
                "label": "Deep expertise in software development, infrastructure, or data systems",
                "signals": {
                    "og_candidates": ["IT"],
                    "jes_factor_hints": ["Knowledge of specialized fields"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "general_admin_skills",
                "label": "General organizational, administrative, and coordination skills",
                "signals": {
                    "og_candidates": ["AS"],
                    "jes_factor_hints": ["Leadership & operational mgmt"],
                    "teer_affinity": [2, 3, 4],
                },
            },
        ],
    },
    {
        "id": "policy_interpretation",
        "phase_slot": "work_type",
        "question": "Does this person develop, interpret, or apply rules, policies, or standards?",
        "helper": "Select the option that best describes their primary relationship with rules and policy.",
        "input_type": "choices",
        "options": [
            {
                "id": "develops_policy",
                "label": "Develops or shapes policy, regulations, or strategic guidance",
                "signals": {
                    "og_candidates": ["EC"],
                    "jes_factor_hints": ["Research & analysis", "Contextual knowledge"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "applies_financial_standards",
                "label": "Applies financial accounting standards, costing frameworks, or audit procedures",
                "signals": {
                    "og_candidates": ["FI"],
                    "jes_factor_hints": ["Knowledge of specialized fields"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "administers_established",
                "label": "Administers or implements established procedures and operational processes",
                "signals": {
                    "og_candidates": ["AS", "IT"],
                    "jes_factor_hints": ["Leadership & operational mgmt"],
                    "teer_affinity": [2, 3, 4],
                },
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# OG_DEFINITIONS
# Verbatim occupational group definitions for OG classification.
# Source: data/Job_evaluation/ text files + TBS OCHRO Occupational Group
# Definitions for groups not defined in a JES standard (AS, FI).
# EC: "EC Economics and Social Science Services - Job Evaluation Standard 2017.txt"
# IT: "IT Information Technology - Job Evaluation Standard.txt"
# AS: TBS OCHRO Administrative Services group definition (published standard;
#     PA collective agreement covers the AS group but does not contain the
#     group definition text itself).
# FI: TBS OCHRO Financial Management group definition (published standard;
#     CT-FIN collective agreement covers the FI group but does not contain
#     the group definition text itself).
# Key: OG code (str). Value: dict with og_name, definition, inclusions, exclusions.
# ---------------------------------------------------------------------------

OG_DEFINITIONS: dict[str, dict] = {
    "EC": {
        "og_name": "Economics and Social Science Services",
        "definition": (
            "The EC Group comprises positions primarily involved in the conduct "
            "of surveys, studies and projects in the social sciences; the "
            "identification, description and organization of archival, library, "
            "museum and gallery materials; the editing of legislation or the "
            "provision of advice on legal problems in specific fields; and the "
            "application of a comprehensive knowledge of economics, sociology "
            "or statistics to the conduct of economic, socio-economic and "
            "sociological research, studies, forecasts and surveys."
        ),
        "inclusions": "",
        "exclusions": "",
    },
    "AS": {
        "og_name": "Administrative Services",
        "definition": (
            "The Administrative Services (AS) Group comprises positions "
            "primarily involved in the planning, development, delivery, "
            "evaluation and management of programs, services and operations "
            "in support of the strategic and operational objectives of the "
            "federal public service, including the application of knowledge "
            "of administrative practices, procedures, policies, financial "
            "administration, human resources management, procurement, "
            "information management and reporting requirements to the "
            "delivery of public service programs and services."
        ),
        "inclusions": "",
        "exclusions": "",
    },
    "IT": {
        "og_name": "Information Technology",
        "definition": (
            "The Information Technology (IT) Group comprises positions for "
            "which the application of comprehensive computer systems knowledge "
            "is the primary requirement to the development, implementation "
            "and/or maintenance of IT systems and infrastructure."
        ),
        "inclusions": (
            "Notwithstanding the generality of the foregoing, for greater "
            "certainty, it includes positions that have, as their primary "
            "purpose, responsibility for one or more of the following "
            "activities: designing, developing, integrating, deploying, and/or "
            "maintaining software, hardware, or network systems; providing "
            "technical support, service and control for software, hardware, "
            "and network infrastructure; providing technical analysis, advice "
            "and recommendations on IT systems, products and services; "
            "researching, developing, implementing, or evaluating information "
            "technology policies, directives, standards, and frameworks; or "
            "leading, managing, or supervising any of the above activities."
        ),
        "exclusions": (
            "Positions excluded from the Information Technology Group are "
            "those whose primary purpose is included in the definition of any "
            "other occupational group or those in which one or more of the "
            "following activities is of primary importance: the planning, "
            "development, delivery or management of administrative and "
            "federal government policies, programs, services, or other "
            "activities directed to the public or to the Public Service; or "
            "the support or provision of administrative, scientific, "
            "professional or technical services that may involve limited or "
            "specific application of information technology skills and "
            "knowledge as an auxiliary to the performance of the activities "
            "central to the primary purpose of the position; or planning, "
            "business analysis, information management, or data manipulation "
            "activities that do not require comprehensive information "
            "technology systems knowledge; or the operation, scheduling or "
            "controlling of the operations of electronic equipment used in the "
            "processing of data; or where a comprehensive knowledge of "
            "engineering is the prime requirement."
        ),
    },
    "FI": {
        "og_name": "Financial Management",
        "definition": (
            "The Financial Management (FI) Group comprises positions primarily "
            "involved in the application of professional accounting, auditing "
            "and financial management knowledge to the planning, organization, "
            "direction and control of the financial operations of the federal "
            "public service, including financial planning, budgeting, "
            "comptrollership, financial reporting, internal audit, performance "
            "measurement and the provision of advice and recommendations on "
            "financial and accounting matters."
        ),
        "inclusions": "",
        "exclusions": "",
    },
    "CR": {
        "og_name": "Clerical and Regulatory",
        "definition": (
            "The CR Group comprises positions primarily involved in clerical, "
            "regulatory, and administrative support work of a clerical nature."
        ),
        "inclusions": "",
        "exclusions": "",
    },
    "PM": {
        "og_name": "Program and Administrative Services",
        "definition": (
            "The PM Group comprises positions primarily involved in program "
            "administration, project coordination, and public service delivery."
        ),
        "inclusions": "",
        "exclusions": "",
    },
}


# ---------------------------------------------------------------------------
# ASEC_DISAMBIGUATION
# Displayed verbatim when both AS and EC appear in top-3 OG candidates.
# Text derived from OG_DEFINITIONS EC + AS definition excerpts.
# Citation: TBS OCHRO Occupational Group Definitions.
# ---------------------------------------------------------------------------

ASEC_DISAMBIGUATION: dict = {
    "disambiguation_text": (
        "Economics and Social Science Services (EC): "
        + OG_DEFINITIONS["EC"]["definition"][:300]
        + " ... "
        "Administrative Services (AS): "
        + OG_DEFINITIONS["AS"]["definition"][:300]
        + " Review the position's primary work content against these definitions before confirming."
    ),
    "citation": "TBS OCHRO Occupational Group Definitions",
}


# ---------------------------------------------------------------------------
# QUAL_STANDARDS
# Default qualification standard text per OG group for GET /api/quals/default.
# Source: TBS Qualification Standards reference (published by TBS OCHRO).
# Minimum coverage: EC, AS, IT, FI.
# ---------------------------------------------------------------------------

QUAL_STANDARDS: dict[str, dict] = {
    "EC": {
        "education": "A degree from a recognized university with acceptable specialization in economics, sociology or statistics.",
        "experience": "Significant and recent experience in policy research and analysis, economic forecasting, or socio-economic studies relevant to the position being staffed.",
        "source": "TBS Qualification Standard for Economics and Social Science Services (EC)",
    },
    "AS": {
        "education": "Successful completion of two years of a post-secondary program with specialization in business administration, public administration, or a related field.",
        "experience": "Experience in administrative services, program support, or office management relevant to the duties of the position.",
        "source": "TBS Qualification Standard for Administrative Services (AS)",
    },
    "IT": {
        "education": "Successful completion of two years of an acceptable post-secondary educational program in computer science, information technology, information management, or another specialty relevant to the position.",
        "experience": "Experience in one or more information technology disciplines relevant to the duties of the position.",
        "source": "TBS Qualification Standard for Information Technology (IT)",
    },
    "FI": {
        "education": "A degree from a recognized university with specialization in accounting, business administration, commerce, finance, or a related field.",
        "experience": "Experience in financial management, comptrollership, or public sector financial operations relevant to the duties of the position.",
        "source": "TBS Qualification Standard for Financial Management (FI)",
    },
    # Default fallback — used when og_code is not one of the keys above (Phase 19 QUAL-01).
    # Mirrors the frontend QUAL_DEFAULTS['default'] entry in data.jsx.
    "default": {
        "education": "A degree or diploma from a recognized post-secondary institution in a field relevant to the duties of the position, or an equivalent combination of education and experience.",
        "experience": "Experience performing duties relevant to the position.",
        "source": "TBS Qualification Standards (general fallback)",
    },
}


# ---------------------------------------------------------------------------
# EC_JES_ELEMENTS
# EC JES 2017 factor scales — 9 elements, degree→points dicts.
# Source: verified against Job Description Builder/jd-builder/data.jsx
# EC_ELEMENTS (data.jsx lines 93-103).
# Key: list index. Value: dict with name (str), category (str), pts (dict[int, int]).
# ---------------------------------------------------------------------------

EC_JES_ELEMENTS: list[dict] = [
    {"name": "Decision making",                 "category": "Responsibility", "pts": {1:5, 2:15, 3:35, 4:60, 5:90, 6:125, 7:165, 8:210}},
    {"name": "Leadership & operational mgmt",   "category": "Responsibility", "pts": {1:5, 2:20, 3:50, 4:90, 5:140}},
    {"name": "Communication",                   "category": "Skill",          "pts": {1:5, 2:25, 3:50, 4:75, 5:100, 6:140, 7:180}},
    {"name": "Knowledge of specialized fields", "category": "Skill",          "pts": {1:5, 2:15, 3:35, 4:55, 5:80, 6:105}},
    {"name": "Contextual knowledge",            "category": "Skill",          "pts": {1:5, 2:20, 3:40, 4:60, 5:80, 6:105}},
    {"name": "Research & analysis",             "category": "Skill",          "pts": {1:5, 2:30, 3:75, 4:120, 5:165, 6:210}},
    {"name": "Physical effort",                 "category": "Effort",         "pts": {1:3, 2:4, 3:6, 4:10, 5:15}},
    {"name": "Sensory effort",                  "category": "Effort",         "pts": {1:2, 2:3, 3:5, 4:10}},
    {"name": "Working conditions",              "category": "Conditions",     "pts": {1:5, 2:8, 3:12, 4:17, 5:25}},
]


# ---------------------------------------------------------------------------
# EC_DEGREES
# Degree vectors per EC level (index aligns with EC_JES_ELEMENTS).
# Source: verified against Job Description Builder/jd-builder/data.jsx
# EC_DEGREES (data.jsx lines 105-108).
# Levels not in this table fall back to EC-05 (same fallback as data.jsx ecFactors()).
# ---------------------------------------------------------------------------

EC_DEGREES: dict[str, list[int]] = {
    "EC-04": [4, 2, 4, 4, 3, 3, 1, 2, 2],
    "EC-05": [5, 3, 5, 5, 4, 4, 1, 2, 2],
    "EC-06": [6, 4, 6, 5, 5, 5, 1, 2, 2],
}


# ---------------------------------------------------------------------------
# NON_EC_TOTALS
# Approximate total JES points for non-EC groups at each level.
# Source: verified against Job Description Builder/jd-builder/data.jsx
# GENERIC_TOTALS (data.jsx lines 118-120).
# Key: OG code (str). Value: dict[int level, int points].
# ---------------------------------------------------------------------------

NON_EC_TOTALS: dict[str, dict[int, int]] = {
    "FI": {4: 470, 5: 560, 6: 660},
    "IT": {4: 480, 5: 575, 6: 690},
    "AS": {4: 430, 5: 510, 6: 600},
    "EN": {4: 500, 5: 600, 6: 720},
}


# ---------------------------------------------------------------------------
# NON_EC_STANDARD_NAMES
# Human-readable JES standard name per non-EC group.
# Source: verified against Job Description Builder/jd-builder/data.jsx
# WORK_TYPES standard field (data.jsx lines 79-88).
# ---------------------------------------------------------------------------

NON_EC_STANDARD_NAMES: dict[str, str] = {
    "FI": "FI / CT Job Evaluation Standard (2023)",
    "IT": "IT Job Evaluation Standard",
    "AS": "AS / PA Job Evaluation Standard",
    "EN": "EN Job Evaluation Standard",
}
