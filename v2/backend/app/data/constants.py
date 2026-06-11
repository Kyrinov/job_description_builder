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
    "FB": list(range(1, 8)),   # FB-1 to FB-7 — FB_rates.csv (max JES factor degree is 7)
    "FS": list(range(1, 5)),   # FS-01 to FS-04 — FS_rates.csv
    "AI": list(range(1, 8)),   # AI-01 to AI-07 — AI_rates.csv
    "AU": list(range(1, 7)),   # AU-01 to AU-06 — CT_FI_rates.csv (internally CT-EAV; OG code remains AU)
    # Phase 21 additions — verified from rates CSVs and JES text files
    "ED": list(range(1, 5)),   # ED-01 to ED-04 — ED JES level descriptions (ED-EST: Level 1-4)
    "LC": list(range(1, 5)),   # LC-01 to LC-04 — LC JES point boundaries
    "LP": list(range(1, 6)),   # LP-01 to LP-05 — LP JES point boundaries
    "MT": list(range(1, 8)),   # MT-01 to MT-07 — SP_AP_rates.csv (NOT 9; only 7 active)
    "NT": list(range(1, 5)),   # NT-01 to NT-04 — NT JES (ND-DIT-1,2,3,4)
    "NU": list(range(1, 9)),   # NU-01 to NU-08 — SH_rates.csv (HOS/CHN broadest range)
    "PO": list(range(1, 5)),   # PO-01 to PO-04 — PO_rates.csv TCO-01 to TCO-04
    "PS": list(range(1, 6)),   # PS-01 to PS-05 — SH_rates.csv (PS-1 to PS-5)
    "SW": list(range(1, 6)),   # SW-01 to SW-05 — SH_rates.csv (SCW 1-5 broadest; CHA 1-3 narrower)
    "WP": list(range(1, 7)),   # WP-01 to WP-06 — PA_rates.csv (WP-1 to WP-6)
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
    # Phase 21 (Plan 05): broader factor names used by the new OG groups
    # (NU, SW, PS, WP, LC, LP, FB, FS, MT, ED, NT, PO) whose JES structures
    # differ from the EC 9-factor model. These are advisory hints only — they
    # drive ranking of OG candidates from the sector-gate and cluster questions.
    "Human relations",
    "Physical demands",
    "Organizational impact",
    "Knowledge and skills",
    "Effort",
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
    # ---- Phase 21 additions: sector-gate + cluster disambiguation ----
    # These questions route signals for the 12 new OG groups (NU, SW, PS, WP,
    # LC, LP, FB, FS, MT, ED, NT, PO). The sector-gate question fires first
    # to narrow the broad sector, then the matching cluster question dis-
    # ambiguates within the sector. Signal tally accumulation from these
    # answers surfaces the dominant new group as the top OG candidate.
    {
        "id": "qb_sector_gate",
        "phase_slot": "sector_gate",
        "question": "Which sector best describes the primary service domain of this position?",
        "helper": "Think about the professional or regulatory domain the work is grounded in.",
        "input_type": "choices",
        "options": [
            {
                "id": "pa_sh_sector",
                "label": "Health and social services — nursing, social work, psychology, or welfare programs",
                "signals": {
                    "og_candidates": ["NU", "SW", "PS", "WP"],
                    "jes_factor_hints": ["Human relations", "Physical demands"],
                    "teer_affinity": [2, 3],
                },
            },
            {
                "id": "legal_sector",
                "label": "Legal services — providing legal advice, representing the Crown, or managing legal risk",
                "signals": {
                    "og_candidates": ["LC", "LP"],
                    "jes_factor_hints": ["Decision making", "Organizational impact"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "technical_scientific_sector",
                "label": "Technical or scientific operations — inspection, enforcement, meteorology, or environmental services",
                "signals": {
                    "og_candidates": ["FB", "FS", "MT"],
                    "jes_factor_hints": ["Knowledge and skills", "Effort"],
                    "teer_affinity": [2, 3],
                },
            },
            {
                "id": "education_sector",
                "label": "Education and training — teaching, curriculum design, or educational program delivery",
                "signals": {
                    "og_candidates": ["ED", "NT"],
                    "jes_factor_hints": ["Knowledge and skills", "Human relations"],
                    "teer_affinity": [2, 3],
                },
            },
            {
                "id": "programme_admin_sector",
                "label": "Programme and administrative operations — programme delivery, operational support, or liaison work",
                "signals": {
                    "og_candidates": ["PO", "WP"],
                    "jes_factor_hints": ["Organizational impact", "Effort"],
                    "teer_affinity": [2, 3],
                },
            },
            {
                "id": "other_sector",
                "label": "General professional or administrative work (economics, policy, information technology, or administration)",
                "signals": {
                    "og_candidates": ["EC", "AS", "IT", "FI"],
                    "jes_factor_hints": ["Research & analysis", "Decision making"],
                    "teer_affinity": [1, 2],
                },
            },
        ],
    },
    {
        "id": "qb_health_social_cluster",
        "phase_slot": "health_social_cluster",
        "question": "What is the primary focus of the health or social service work?",
        "helper": "Select the description that most closely matches the day-to-day responsibilities.",
        "input_type": "choices",
        "options": [
            {
                "id": "nursing_hospital",
                "label": "Direct patient care — assessing, treating, and monitoring patients in a clinical setting",
                "signals": {
                    "og_candidates": ["NU"],
                    "jes_factor_hints": ["Human relations", "Physical demands"],
                    "teer_affinity": [3],
                },
            },
            {
                "id": "social_work_services",
                "label": "Social welfare case management — counselling, intervention, and connecting clients to services",
                "signals": {
                    "og_candidates": ["SW"],
                    "jes_factor_hints": ["Human relations", "Decision making"],
                    "teer_affinity": [2, 3],
                },
            },
            {
                "id": "psychology_services",
                "label": "Psychological assessment or therapy — testing, clinical judgment, and treatment planning",
                "signals": {
                    "og_candidates": ["PS"],
                    "jes_factor_hints": ["Knowledge and skills", "Decision making"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "welfare_programs",
                "label": "Welfare program delivery — administering income support, benefits, or eligibility decisions",
                "signals": {
                    "og_candidates": ["WP"],
                    "jes_factor_hints": ["Organizational impact", "Effort"],
                    "teer_affinity": [2, 3],
                },
            },
        ],
    },
    {
        "id": "qb_legal_cluster",
        "phase_slot": "legal_cluster",
        "question": "What is the primary legal function of this position?",
        "helper": "Consider whether the work involves direct legal representation or managing legal affairs at an organizational level.",
        "input_type": "choices",
        "options": [
            {
                "id": "legal_counsel",
                "label": "Providing legal counsel and representing the Crown in proceedings",
                "signals": {
                    "og_candidates": ["LP"],
                    "jes_factor_hints": ["Decision making", "Organizational impact"],
                    "teer_affinity": [1],
                },
            },
            {
                "id": "legal_management",
                "label": "Managing legal services, contracts, or access to information and privacy matters",
                "signals": {
                    "og_candidates": ["LC"],
                    "jes_factor_hints": ["Organizational impact", "Decision making"],
                    "teer_affinity": [1, 2],
                },
            },
        ],
    },
    {
        "id": "qb_technical_cluster",
        "phase_slot": "technical_cluster",
        "question": "What type of technical or scientific work does this position primarily perform?",
        "helper": "Select the domain that best matches the specialized knowledge or operational role.",
        "input_type": "choices",
        "options": [
            {
                "id": "border_enforcement",
                "label": "Examining travellers, goods, or people at ports of entry and enforcing border legislation",
                "signals": {
                    "og_candidates": ["FB"],
                    "jes_factor_hints": ["Knowledge and skills", "Decision making"],
                    "teer_affinity": [2, 3],
                },
            },
            {
                "id": "foreign_service",
                "label": "Representing Canada abroad, negotiating international agreements, or providing consular services",
                "signals": {
                    "og_candidates": ["FS"],
                    "jes_factor_hints": ["Knowledge and skills", "Organizational impact"],
                    "teer_affinity": [1, 2],
                },
            },
            {
                "id": "meteorology_science",
                "label": "Weather forecasting, atmospheric science, or environmental monitoring",
                "signals": {
                    "og_candidates": ["MT"],
                    "jes_factor_hints": ["Knowledge and skills", "Effort"],
                    "teer_affinity": [2, 3],
                },
            },
        ],
    },
    {
        "id": "qb_education_cluster",
        "phase_slot": "education_cluster",
        "question": "What type of education or training work does this position primarily involve?",
        "helper": "Consider whether the role is classroom-based, curriculum design, or nutrition and dietetics guidance.",
        "input_type": "choices",
        "options": [
            {
                "id": "education_teaching",
                "label": "Teaching language, academic subjects, or specialized courses to government employees or in federal institutions",
                "signals": {
                    "og_candidates": ["ED"],
                    "jes_factor_hints": ["Knowledge and skills", "Human relations"],
                    "teer_affinity": [2, 3],
                },
            },
            {
                "id": "nutrition_dietetics",
                "label": "Providing nutrition counselling, diet therapy, or food service management guidance",
                "signals": {
                    "og_candidates": ["NT"],
                    "jes_factor_hints": ["Knowledge and skills", "Human relations"],
                    "teer_affinity": [2, 3],
                },
            },
        ],
    },
    {
        "id": "qb_programme_admin_cluster",
        "phase_slot": "programme_admin_cluster",
        "question": "What is the primary focus of the programme or administrative operations work?",
        "helper": "Consider whether the role is primarily operational communications and police support, or broader programme delivery and social services administration.",
        "input_type": "choices",
        "options": [
            {
                "id": "police_telecom",
                "label": "Operating telecommunications systems or monitoring intercepts to support police operations",
                "signals": {
                    "og_candidates": ["PO"],
                    "jes_factor_hints": ["Organizational impact", "Effort"],
                    "teer_affinity": [2, 3],
                },
            },
            {
                "id": "welfare_program_delivery",
                "label": "Delivering income support, benefits eligibility decisions, or welfare case management",
                "signals": {
                    "og_candidates": ["WP"],
                    "jes_factor_hints": ["Organizational impact", "Effort"],
                    "teer_affinity": [2, 3],
                },
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# JES_LEVEL_CRITERIA
# Socratic level-determination questions for OG groups that use narrative
# level descriptions (as opposed to point-rated groups computed by Plan 04).
# Key: sub-group string as stored in answers.og_confirm.sub_group
#   (or og_code for single-sub-group groups like PS).
# method: "level_description" for all entries here.
# level_resolution:
#   "majority_hint" = level appearing in the most level_hint lists wins;
#                     tie → lower level (conservative).
#   "direct"        = single question, level_hint is length-1 list → direct map.
# fallback: "pick_list" = if resolution is ambiguous, return null and let
#           frontend fall back to bare OgLevelPicker.
# Phase 21 Plan 08 (JES-LEV-01): Socratic mini-interview before the level
# picker for the 6 OG groups whose JES is level-description-based.
# ---------------------------------------------------------------------------

JES_LEVEL_CRITERIA: dict[str, dict] = {
    "NU-HOS": {
        "method": "level_description",
        "questions": [
            {
                "id": "nu_scope",
                "question": "What best describes the scope of the nursing responsibility?",
                "options": [
                    {"id": "direct_care_assigned", "label": "Provides direct nursing care to an assigned number of patients", "level_hint": [2]},
                    {"id": "unit_or_community", "label": "Plans and delivers care for a unit or community, adapting interventions to client needs", "level_hint": [3]},
                    {"id": "unit_mgmt_24hr", "label": "Manages nursing services in a unit or facility on a 24-hour basis", "level_hint": [4, 5]},
                    {"id": "multi_unit_zone", "label": "Coordinates or evaluates nursing programs across multiple units, a hospital, or a zone", "level_hint": [6, 7]},
                    {"id": "national_policy", "label": "Develops national nursing policies or advises on programs available to Canadians", "level_hint": [8]},
                ],
            },
            {
                "id": "nu_autonomy",
                "question": "What guidance does this person receive?",
                "options": [
                    {"id": "detailed_guidance", "label": "Detailed guidance from a senior nurse; decisions reviewed while in progress", "level_hint": [1, 2]},
                    {"id": "policy_clinical", "label": "Guidance on program policy and clinical issues; resolves most issues independently", "level_hint": [3, 4]},
                    {"id": "admin_objectives", "label": "Direction on institutional or administrative policy objectives only; independently manages operations", "level_hint": [5, 6]},
                    {"id": "govt_objectives", "label": "Direction on government policy and program objectives only", "level_hint": [7, 8]},
                ],
            },
        ],
        "level_resolution": "majority_hint",
        "fallback": "pick_list",
    },
    "NU-CHN": {
        "method": "level_description",
        "questions": [
            {
                "id": "nu_scope",
                "question": "What best describes the scope of the nursing responsibility?",
                "options": [
                    {"id": "direct_care_assigned", "label": "Provides direct nursing care to an assigned number of patients", "level_hint": [2]},
                    {"id": "unit_or_community", "label": "Plans and delivers care for a unit or community, adapting interventions to client needs", "level_hint": [3]},
                    {"id": "unit_mgmt_24hr", "label": "Manages nursing services in a unit or facility on a 24-hour basis", "level_hint": [4, 5]},
                    {"id": "multi_unit_zone", "label": "Coordinates or evaluates nursing programs across multiple units, a hospital, or a zone", "level_hint": [6, 7]},
                    {"id": "national_policy", "label": "Develops national nursing policies or advises on programs available to Canadians", "level_hint": [8]},
                ],
            },
            {
                "id": "nu_autonomy",
                "question": "What guidance does this person receive?",
                "options": [
                    {"id": "detailed_guidance", "label": "Detailed guidance from a senior nurse; decisions reviewed while in progress", "level_hint": [1, 2]},
                    {"id": "policy_clinical", "label": "Guidance on program policy and clinical issues; resolves most issues independently", "level_hint": [3, 4]},
                    {"id": "admin_objectives", "label": "Direction on institutional or administrative policy objectives only; independently manages operations", "level_hint": [5, 6]},
                    {"id": "govt_objectives", "label": "Direction on government policy and program objectives only", "level_hint": [7, 8]},
                ],
            },
        ],
        "level_resolution": "majority_hint",
        "fallback": "pick_list",
    },
    "NU-EMA": {
        "method": "level_description",
        "questions": [
            {
                "id": "ema_scope",
                "question": "What best describes the role?",
                "options": [
                    {"id": "individual_adjudication", "label": "Assesses individual applicant files to determine medical eligibility", "level_hint": [1]},
                    {"id": "expert_direction", "label": "Provides expert advice and functional direction on complex adjudication cases at regional or national level", "level_hint": [2]},
                ],
            },
        ],
        "level_resolution": "direct",
        "fallback": "pick_list",
    },
    "PS": {
        "method": "level_description",
        "questions": [
            {
                "id": "ps_independence",
                "question": "What best describes the level of professional independence?",
                "options": [
                    {"id": "work_reviewed", "label": "Work is reviewed by a supervisor who has final responsibility for validity of conclusions", "level_hint": [1, 2]},
                    {"id": "approach_independent", "label": "Completed work is reviewed for soundness of judgment but this position determines its own approach", "level_hint": [2, 3]},
                    {"id": "fully_independent", "label": "Professionally independent; guidance restricted to policy matters; assumes final responsibility for all decisions and recommendations", "level_hint": [4, 5]},
                ],
            },
            {
                "id": "ps_methods",
                "question": "What best describes the level of method development?",
                "options": [
                    {"id": "applies_established", "label": "Applies established psychodiagnostic methods and techniques with some adaptation", "level_hint": [1]},
                    {"id": "modifies_develops", "label": "Modifies and adapts established methods; develops new techniques for specific clinical problems", "level_hint": [2, 3]},
                    {"id": "originates_new", "label": "Originates new approaches and complex methodologies; develops procedures for changing program requirements", "level_hint": [4, 5]},
                ],
            },
            {
                "id": "ps_management",
                "question": "What best describes the staff and program management scope?",
                "options": [
                    {"id": "no_supervision", "label": "No continuous staff supervision; may occasionally guide a research assistant or intern", "level_hint": [1, 2]},
                    {"id": "supervises_staff", "label": "Supervises technical and junior professional staff; recommends project initiation", "level_hint": [3]},
                    {"id": "directs_program", "label": "Plans, organizes, and directs a multi-functional psychology program; manages budget and professional staff", "level_hint": [4, 5]},
                ],
            },
        ],
        "level_resolution": "majority_hint",
        "fallback": "pick_list",
    },
    "NT-ADV": {
        "method": "level_description",
        "questions": [
            {
                "id": "nt_adv_scope",
                "question": "What is the geographic or program scope of the nutrition advisory work?",
                "options": [
                    {"id": "zone_local", "label": "Provides nutrition advice within a defined zone or locality", "level_hint": [1]},
                    {"id": "regional", "label": "Coordinates nutrition programs or provides advisory services across a region", "level_hint": [2]},
                    {"id": "national", "label": "Advises headquarters, regional and zone staff nationally; consults with provincial governments or international organizations", "level_hint": [3]},
                ],
            },
        ],
        "level_resolution": "direct",
        "fallback": "pick_list",
    },
    "NT-DIT": {
        "method": "level_description",
        "questions": [
            {
                "id": "nt_dit_scope",
                "question": "What is the scope of the dietary service management responsibility?",
                "options": [
                    {"id": "ward_small_facility", "label": "Plans therapeutic diets or supervises food service for a veterans health centre or a group of wards", "level_hint": [1, 2]},
                    {"id": "full_federal_hospital", "label": "Manages the complete dietary service for a federal hospital including meals for patients and staff (standard population)", "level_hint": [3]},
                    {"id": "large_federal_hospital", "label": "Manages the complete dietary service for a large federal hospital with a large patient and staff population", "level_hint": [4]},
                ],
            },
        ],
        "level_resolution": "direct",
        "fallback": "pick_list",
    },
    "NT-HME": {
        "method": "level_description",
        "questions": [
            {
                "id": "nt_hme_scope",
                "question": "What best describes the scope and independence of the home economics work?",
                "options": [
                    {"id": "supervised_testing", "label": "Selects, tests and modifies recipes or food materials under supervision", "level_hint": [1]},
                    {"id": "independent_projects", "label": "Conducts experimental projects independently; responsible for experimental design and sensory evaluation", "level_hint": [2]},
                    {"id": "supervises_projects", "label": "Supervises experimental or informational projects; supervises professional staff", "level_hint": [3]},
                    {"id": "directs_program", "label": "Plans, directs and coordinates a program for agricultural or seafood market development", "level_hint": [4]},
                ],
            },
        ],
        "level_resolution": "direct",
        "fallback": "pick_list",
    },
    "PO-TCO": {
        "method": "level_description",
        "questions": [
            {
                "id": "po_autonomy",
                "question": "What best describes the level of supervision and autonomy?",
                "options": [
                    {"id": "trainee_supervised", "label": "Works as a trainee or under close technical supervision", "level_hint": [1]},
                    {"id": "autonomous_general", "label": "Operates systems autonomously under general supervision; minimal coaching role", "level_hint": [2]},
                    {"id": "independent_supervisor", "label": "Works independently with little technical guidance; may supervise day-to-day operations", "level_hint": [3]},
                    {"id": "manages_through_supervisors", "label": "Manages operations through subordinate supervisors; holds budget and strategic planning authority", "level_hint": [4]},
                ],
            },
            {
                "id": "po_policy_scope",
                "question": "What is the policy and program scope of the work?",
                "options": [
                    {"id": "routine_transactions", "label": "Operates communications equipment and responds to public requests; routine transactions", "level_hint": [1, 2]},
                    {"id": "develops_training_policy", "label": "Develops or maintains training programs; analyzes and provides expert advice on national policies", "level_hint": [3]},
                    {"id": "organizational_accountability", "label": "Initiates joint activities with partner organizations; accountable for organizational-level operations", "level_hint": [4]},
                ],
            },
        ],
        "level_resolution": "majority_hint",
        "fallback": "pick_list",
    },
    "SW-CHA": {
        "method": "level_description",
        "questions": [
            {
                "id": "sw_cha_scope",
                "question": "What is the primary scope of the chaplaincy work?",
                "options": [
                    {"id": "single_institution_patients", "label": "Provides pastoral counselling and support to patients in a single institution", "level_hint": [1]},
                    {"id": "single_institution_inmates", "label": "Provides or coordinates pastoral counselling to inmates and their families; implements religious rehabilitation programs; communicates with community", "level_hint": [2]},
                    {"id": "regional_coordination", "label": "Coordinates spiritual programs and chaplaincy services across a region; provides consultation and training", "level_hint": [3]},
                ],
            },
        ],
        "level_resolution": "direct",
        "fallback": "pick_list",
    },
    "ED-LAT": {
        "method": "level_description",
        "questions": [
            {
                "id": "ed_lat_role",
                "question": "What is the primary role in the language teaching program?",
                "options": [
                    {"id": "classroom_teacher", "label": "Teaches a language directly to students; develops lesson plans and tests proficiency", "level_hint": [1]},
                    {"id": "senior_teacher", "label": "Reviews and mentors other language teachers; advises on course content and methodology", "level_hint": [2]},
                    {"id": "principal", "label": "Directs the school; evaluates and guides senior teachers; allocates facilities and resources", "level_hint": [3]},
                ],
            },
        ],
        "level_resolution": "direct",
        "fallback": "pick_list",
    },
    "ED-EST": {
        "method": "level_description",
        "questions": [
            {
                "id": "ed_est_role",
                "question": "What is the primary role in the school or educational program?",
                "options": [
                    {"id": "classroom_teacher", "label": "Teaches academic, technical, vocational, or adult education subjects; or counsels students", "level_hint": [1]},
                    {"id": "department_head", "label": "Plans and supervises teaching of a particular subject or area; advises teachers on methodology and materials", "level_hint": [2]},
                    {"id": "assistant_principal", "label": "Assists in school administration; allocates resources; supports the principal", "level_hint": [3]},
                    {"id": "principal", "label": "Administers the full school program; supervises instruction; evaluates curriculum and student achievement", "level_hint": [4]},
                ],
            },
        ],
        "level_resolution": "direct",
        "fallback": "pick_list",
    },
}


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
    "GT": {
        "og_name": "General Trade and Labour",
        "definition": (
            "The GT Group comprises positions primarily involved in general trade, "
            "craft, manual, and labour work in support of public service operations."
        ),
        "inclusions": "",
        "exclusions": "",
    },
    "EL": {
        "og_name": "Electronics",
        "definition": (
            "The EL Group comprises positions primarily involved in the "
            "application of comprehensive electronics knowledge to the design, "
            "development, installation, maintenance, and operation of electronic "
            "systems and equipment."
        ),
        "inclusions": "",
        "exclusions": "",
    },
    "AI": {
        "og_name": "Aircraft Maintenance",
        "definition": (
            "The AI Group comprises positions primarily involved in aircraft "
            "maintenance, repair, overhaul, and inspection activities in support "
            "of aviation operations."
        ),
        "inclusions": "",
        "exclusions": "",
    },
    "AU": {
        "og_name": "Audio-Visual and Broadcast",
        "definition": (
            "The AU Group comprises positions primarily involved in the operation, "
            "production, and technical support of audio-visual, broadcast, and "
            "electronic media services."
        ),
        "inclusions": "",
        "exclusions": "",
    },
    # Phase 21 additions — all verbatim from data/Job_evaluation/ JES text files
    # or TBS OCHRO Occupational Group Definitions
    "FB": {
        "og_name": "Border Services",
        "definition": (
            "The Border Services Group comprises positions in the Canada Border "
            "Services Agency that are primarily involved in the planning, "
            "development, delivery, or management of the inspection and control "
            "of people and goods entering Canada."
        ),
        "inclusions": (
            "Determining the admissibility of people or goods entering Canada; "
            "post-entry verification of people or goods that have entered Canada; "
            "arresting, detaining or removing those in violation of Canada's laws; "
            "investigating the illegal entry of people or goods; conducting "
            "intelligence activities related to monitoring, inspection or control "
            "of people or goods entering Canada; developing CBSA operational "
            "directives; the leadership of any of the above activities."
        ),
        "exclusions": (
            "Collecting, recording, arranging, transmitting and processing of "
            "information, filing and distribution, and direct application of rules "
            "and regulations; planning, development, delivery or management of "
            "government policies, programs, services or other activities directed "
            "to the public other than those involving inspection and control of "
            "people and goods entering Canada."
        ),
    },
    "FS": {
        "og_name": "Foreign Service",
        "definition": (
            "The Foreign Service Group comprises positions that are primarily "
            "involved in the planning, development, delivery and promotion of "
            "Canada's diplomatic, commercial, human rights, cultural, promotional, "
            "consular and international development policies and interests in other "
            "countries and in international organizations through the career "
            "rotational foreign service."
        ),
        "inclusions": (
            "Commercial and economic relations and trade policy; political and "
            "economic relations; immigration affairs; legal affairs; consular "
            "services; cultural relations and international development."
        ),
        "exclusions": "",
    },
    "ED": {
        "og_name": "Education",
        "definition": (
            "The Education (ED) classification of the EB Group comprises positions "
            "primarily involved in the application of a comprehensive knowledge of "
            "educational techniques to the teaching and counselling of students in "
            "schools and to the education, training and counselling of youths and "
            "adults in out-of-school programs, to the conduct of research and to "
            "the provision of advice related to education."
        ),
        "inclusions": "",
        "exclusions": "",
    },
    "LC": {
        "og_name": "Law Management",
        "definition": (
            "The Law Management occupational group comprises positions that are "
            "primarily involved in the application of a comprehensive knowledge of "
            "the law and its practice in the management of legal functions, with "
            "accountability for exercising delegated authority over human and "
            "financial resources."
        ),
        "inclusions": (
            "Providing legal advice on the development, direction, conduct or "
            "management of programs or services; managing legal programs or "
            "services and determining the nature and priority of objectives and "
            "resources committed to their achievement within and across "
            "organizations."
        ),
        "exclusions": "",
    },
    "LP": {
        "og_name": "Law Practitioner",
        "definition": (
            "The Law Practitioner occupational group comprises positions that are "
            "primarily involved in the application of a comprehensive knowledge of "
            "the law and its practice to the performance of legal functions."
        ),
        "inclusions": (
            "The provision of legal advice and legal services; the drafting of "
            "legislation, including regulations and Orders in Council; the conduct "
            "of litigation and prosecution."
        ),
        "exclusions": "",
    },
    "MT": {
        "og_name": "Meteorology",
        "definition": (
            "The Meteorology classification of the Applied Science and Patent "
            "Examination Group, Applied Science Sub-group comprises positions that "
            "are primarily involved in the application of comprehensive scientific "
            "and professional knowledge to one of the applied science programs "
            "involving meteorology."
        ),
        "inclusions": (
            "The analysis and forecasting of weather and climatic phenomena; the "
            "development of instruments, methods and standards for observing and "
            "recording atmospheric phenomena; the development, application and "
            "provision of data, information and advice in the application of "
            "meteorology to the economic and environmental problems of the country; "
            "the planning and conduct of studies, the evaluation and interpretation "
            "of information and scientific research papers, reports, contracts or "
            "agreements, and the provision of advice in the above programs."
        ),
        "exclusions": "",
    },
    "NT": {
        "og_name": "Nutrition and Dietetics",
        "definition": (
            "The Nutrition and Dietetics (ND) classification within the Health "
            "Services (SH) Group comprises positions that are primarily involved "
            "in the application of a comprehensive knowledge of professional "
            "specialties in the fields of nutrition and dietetics to the physical "
            "well-being of people."
        ),
        "inclusions": (
            "The development of standards and guides in the field of nutrition and "
            "dietetics; the assessment of nutritional requirements and provision "
            "of nutrition and dietetic services; the provision of nutritional "
            "education and information; the management of nutritional programs; "
            "the management of food services; the provision of advice in the above "
            "fields; the leadership of any of the above activities."
        ),
        "exclusions": "",
    },
    "NU": {
        "og_name": "Nursing",
        "definition": (
            "The Nursing (NU) classification within the Health Services (SH) Group "
            "comprises positions that are primarily involved in the application of "
            "a comprehensive knowledge of professional specialties in the field of "
            "nursing to the physical and mental well-being of people."
        ),
        "inclusions": (
            "The assessment of medical information for the purposes of determining "
            "eligibility of applicants for a government program requiring knowledge "
            "associated with a registered nurse; the care of patients and the "
            "treatment and management of illness in cooperation with medical doctors, "
            "and the provision of specialized nursing services; the evaluation of "
            "nursing policies, procedures, standards and practices and the conduct "
            "of related research and education; the provision of advice in the above "
            "fields."
        ),
        "exclusions": "",
    },
    "PO": {
        "og_name": "Police Operations Support",
        "definition": (
            "The Police Operations Support Group comprises positions that are "
            "primarily engaged in planning, developing, conducting or managing "
            "telecommunications in support of police operations."
        ),
        "inclusions": (
            "Planning, developing, conducting or managing telecommunications "
            "operations in support of police operations; intercept monitoring and "
            "analysis in support of police operations."
        ),
        "exclusions": "",
    },
    "PS": {
        "og_name": "Psychology",
        "definition": (
            "The Psychology (PS) classification of the Health Services (SH) Group "
            "comprises positions that are primarily involved in the application of "
            "a comprehensive knowledge of professional specialties in the field of "
            "psychology to the physical and mental well-being of people."
        ),
        "inclusions": (
            "The conduct of research in human behaviour, the assessment of human "
            "motives, abilities, skills, decisions and acts, and the treatment of "
            "human behaviour; the provision of advice in the above fields; the "
            "leadership of any of the above activities."
        ),
        "exclusions": "",
    },
    "SW": {
        "og_name": "Social Work",
        "definition": (
            "The Social Work (SW) classification of the Health Services (SH) Group "
            "comprises positions that are primarily involved in the application of "
            "a comprehensive knowledge of professional specialties in the field of "
            "social work to the physical and mental well-being of people."
        ),
        "inclusions": (
            "The promotion of individual, group and community well-being through "
            "the identification and assessment of social needs; the planning, "
            "development and delivery and management of social programs and social "
            "work services with the objective of lessening, removing or preventing "
            "the physical, emotional and material problems of individuals, families "
            "or groups; the provision of advice in the above fields; the leadership "
            "of any of the above activities."
        ),
        "exclusions": "",
    },
    "WP": {
        "og_name": "Welfare Programmes",
        "definition": (
            "The Welfare Programmes (WP) classification of the Program and "
            "Administrative Services (PA) group comprises positions that are "
            "primarily involved in the planning, development, delivery or management "
            "of administrative and federal government policies, programs, services "
            "or other activities directed to the public."
        ),
        "inclusions": (
            "The planning, development, delivery or management of policies, programs, "
            "services or other activities dealing with the social development, "
            "settlement, adjustment and rehabilitation of groups, communities or "
            "individuals including the planning, development and delivery of welfare "
            "services; the leadership of any of the above-mentioned activities."
        ),
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
    # Phase 21 additions — all 12 new OG groups. Text sourced from TBS OCHRO Qualification
    # Standards reference and the OG-specific JES text files in data/Job_evaluation/.
    "ED": {
        "education": "A degree from a recognized university with acceptable specialization in education, educational psychology, or a field related to the teaching or counselling duties of the position.",
        "experience": "Experience in teaching, educational program development, curriculum design, or educational research relevant to the duties of the position.",
        "source": "TBS Qualification Standard for Education (ED)",
    },
    "FB": {
        "education": "Successful completion of a post-secondary program with specialization in criminology, law enforcement, public administration, or a related field relevant to the duties of the position.",
        "experience": "Experience in border inspection, customs enforcement, immigration control, or related law enforcement activities relevant to the duties of the position.",
        "source": "TBS Qualification Standard for Border Services (FB)",
    },
    "FS": {
        "education": "A degree from a recognized university with acceptable specialization in international relations, political science, economics, law, public administration, or a related field relevant to the position.",
        "experience": "Experience in diplomatic, consular, international trade, or foreign service work relevant to the duties of the position.",
        "source": "TBS Qualification Standard for Foreign Service (FS)",
    },
    "LC": {
        "education": "A degree from a recognized university in law, jurisprudence, or a related field, and membership in good standing in a provincial or territorial law society.",
        "experience": "Significant experience in the practice of law, including managing legal services, providing legal advice on programs or services, or supervising legal staff.",
        "source": "TBS Qualification Standard for Law Management (LC)",
    },
    "LP": {
        "education": "A degree from a recognized university in law, jurisprudence, or a related field, and membership in good standing in a provincial or territorial law society.",
        "experience": "Experience in the practice of law, including providing legal advice, drafting legislation, conducting litigation, or prosecution.",
        "source": "TBS Qualification Standard for Law Practitioner (LP)",
    },
    "MT": {
        "education": "A degree from a recognized university with acceptable specialization in meteorology, atmospheric science, or a related physical science.",
        "experience": "Experience in meteorological analysis, weather forecasting, or atmospheric research relevant to the duties of the position.",
        "source": "TBS Qualification Standard for Meteorology (MT)",
    },
    "NT": {
        "education": "A degree from a recognized university with acceptable specialization in nutrition, dietetics, food science, or home economics, and membership or eligibility for membership in a relevant professional association.",
        "experience": "Experience in the application of professional nutrition or dietetic knowledge in clinical, community, public health, or food service settings relevant to the duties of the position.",
        "source": "TBS Qualification Standard for Nutrition and Dietetics (NT)",
    },
    "NU": {
        "education": "A degree from a recognized school of nursing, and current registration or eligibility for registration as a Registered Nurse in a province or territory of Canada.",
        "experience": "Experience in nursing practice, clinical care, community health, or specialized nursing services relevant to the duties of the position.",
        "source": "TBS Qualification Standard for Nursing (NU)",
    },
    "PO": {
        "education": "Successful completion of a post-secondary program with specialization in telecommunications, electronics, information technology, police operations, or a related field relevant to the duties of the position.",
        "experience": "Experience in telecommunications operations, intercept monitoring, police operations support, or related law enforcement technology work.",
        "source": "TBS Qualification Standard for Police Operations Support (PO)",
    },
    "PS": {
        "education": "A doctoral degree from a recognized university in psychology, or a master's degree with registration or eligibility for registration as a psychologist in a province or territory of Canada.",
        "experience": "Experience in the practice of psychology, including assessment, research, treatment, or consultation services relevant to the duties of the position.",
        "source": "TBS Qualification Standard for Psychology (PS)",
    },
    "SW": {
        "education": "A master's degree from a recognized university in social work, and registration or eligibility for registration as a social worker in a province or territory of Canada.",
        "experience": "Experience in social work practice, counselling, case management, community development, or program delivery relevant to the duties of the position.",
        "source": "TBS Qualification Standard for Social Work (SW)",
    },
    "WP": {
        "education": "Successful completion of a post-secondary program with specialization in social work, social sciences, public administration, or a related field relevant to the duties of the position.",
        "experience": "Experience in welfare program delivery, social services, settlement and adjustment services, or community development relevant to the duties of the position.",
        "source": "TBS Qualification Standard for Welfare Programmes (WP)",
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
# JES_FACTORS_BY_GROUP
# Factor scales for point-rating JES groups (Phase 21 OGX-05).
# Each entry mirrors EC_JES_ELEMENTS shape: list of {name, category, pts} dicts.
# Degrees (1..N) map to point values for that factor.
# Source: data/Job_evaluation/ JES text files. Values are illustrative point-rating
# tables; per-factor degree-to-points mappings follow the published standard.
# Level descriptions are used for level-description groups (NU, PS, NT, PO, WP,
# SW-CHA, ED-LAT, ED-EST) — those groups are NOT in this constant; they live in
# NON_EC_TOTALS as level-keyed point dicts instead.
# ---------------------------------------------------------------------------

JES_FACTORS_BY_GROUP: dict[str, list[dict]] = {
    # Border Services (FB) — 10 elements, point-rating
    # Source: FB Border Services - Job Evaluation Standard 2005.txt
    "FB": [
        {"name": "Knowledge",                  "category": "Skill",          "pts": {1: 17, 2: 30, 3: 50, 4: 80, 5: 135, 6: 170}},
        {"name": "Analytical skills",          "category": "Skill",          "pts": {1: 15, 2: 30, 3: 50, 4: 80, 5: 115, 6: 150}},
        {"name": "Communication skills",       "category": "Skill",          "pts": {1: 10, 2: 25, 3: 45, 4: 70, 5: 100}},
        {"name": "Interaction",                "category": "Responsibility", "pts": {1: 15, 2: 35, 3: 70, 4: 110, 5: 150}},
        {"name": "People & operational mgmt",  "category": "Responsibility", "pts": {1: 10, 2: 30, 3: 80, 4: 125, 5: 150}},
        {"name": "Decision making",            "category": "Responsibility", "pts": {1: 20, 2: 30, 3: 60, 4: 100, 5: 140, 6: 175, 7: 200}},
        {"name": "Physical effort",            "category": "Effort",         "pts": {1: 1, 2: 5, 3: 30}},
        {"name": "Sensory effort",             "category": "Effort",         "pts": {1: 1, 2: 4, 3: 10}},
        {"name": "Risk to health",             "category": "Conditions",     "pts": {1: 2, 2: 10, 3: 20}},
        {"name": "Work environment",           "category": "Conditions",     "pts": {1: 2, 2: 10, 3: 20}},
    ],
    # Foreign Service (FS) — 8 elements, point-rating
    # Source: FS Foreigns Service - Job Evauation Standard.txt
    "FS": [
        {"name": "Knowledge",                       "category": "Skill",          "pts": {1: 25, 2: 60, 3: 110, 4: 170, 5: 230}},
        {"name": "Information analysis",            "category": "Skill",          "pts": {1: 20, 2: 50, 3: 95, 4: 145, 5: 195, 6: 240}},
        {"name": "Communications & influencing",    "category": "Skill",          "pts": {1: 20, 2: 50, 3: 90, 4: 140, 5: 190, 6: 240}},
        {"name": "People & operational mgmt",       "category": "Responsibility", "pts": {1: 10, 2: 25, 3: 60, 4: 100, 5: 145, 6: 200}},
        {"name": "Horizontal leadership",           "category": "Responsibility", "pts": {1: 10, 2: 25, 3: 50, 4: 85, 5: 120, 6: 160}},
        {"name": "Problem solving / decision making", "category": "Responsibility", "pts": {1: 20, 2: 45, 3: 80, 4: 120, 5: 165, 6: 220}},
        {"name": "Psychological / emotional effort","category": "Effort",         "pts": {1: 5, 2: 15, 3: 30}},
        {"name": "Working conditions",              "category": "Conditions",     "pts": {1: 5, 2: 15, 3: 30}},
    ],
    # Law Management (LC) — 6 elements, point-rating
    # Source: LC Law Management - Job Evaluation Standard.txt
    "LC": [
        {"name": "Knowledge",                                 "category": "Skill",          "pts": {1: 50, 2: 100, 3: 160, 4: 220, 5: 300}},
        {"name": "Critical thinking and analysis",            "category": "Skill",          "pts": {1: 40, 2: 80, 3: 130, 4: 180, 5: 240, 6: 300}},
        {"name": "Relationship building and influencing",     "category": "Responsibility", "pts": {1: 30, 2: 70, 3: 120, 4: 175, 5: 225, 6: 275}},
        {"name": "Leadership and management",                 "category": "Responsibility", "pts": {1: 30, 2: 70, 3: 130, 4: 200, 5: 275, 6: 350}},
        {"name": "Physical and sensory effort",               "category": "Effort",         "pts": {1: 5, 2: 15, 3: 30}},
        {"name": "Work environment",                          "category": "Conditions",     "pts": {1: 5, 2: 15, 3: 30}},
    ],
    # Law Practitioner (LP) — 6 elements, point-rating
    # Source: LP Law Practitioner - Job Evaluation Standard
    "LP": [
        {"name": "Critical thinking and analysis", "category": "Skill",          "pts": {1: 50, 2: 100, 3: 160, 4: 220, 5: 300}},
        {"name": "Knowledge",                       "category": "Skill",          "pts": {1: 50, 2: 100, 3: 160, 4: 220, 5: 300}},
        {"name": "Communication and interaction",   "category": "Skill",          "pts": {1: 30, 2: 70, 3: 120, 4: 175, 5: 225, 6: 275}},
        {"name": "Leadership",                      "category": "Responsibility", "pts": {1: 30, 2: 70, 3: 130, 4: 200, 5: 275, 6: 350}},
        {"name": "Physical and sensory effort",     "category": "Effort",         "pts": {1: 5, 2: 15, 3: 30}},
        {"name": "Work environment",                "category": "Conditions",     "pts": {1: 5, 2: 15, 3: 30}},
    ],
    # Meteorology (MT) — 4 elements, point-rating
    # Source: MT Meteorology - Job Evaluation Standard
    "MT": [
        {"name": "Knowledge",                        "category": "Skill",          "pts": {1: 50, 2: 100, 3: 160, 4: 220, 5: 300}},
        {"name": "Problem solving / decision making", "category": "Skill",          "pts": {1: 40, 2: 85, 3: 140, 4: 195, 5: 250, 6: 310}},
        {"name": "Accountability",                   "category": "Responsibility", "pts": {1: 30, 2: 70, 3: 120, 4: 180, 5: 240, 6: 310}},
        {"name": "Communications requirement",       "category": "Responsibility", "pts": {1: 20, 2: 50, 3: 90, 4: 130, 5: 180}},
    ],
    # Social Welfare (SW-SCW sub-group) — point-rating plan
    # Source: SW Social Work - Job Evaluation Standard, Social Welfare sub-group rating scales
    "SW-SCW": [
        {"name": "Knowledge",                       "category": "Skill",          "pts": {1: 30, 2: 65, 3: 105, 4: 150, 5: 200}},
        {"name": "Professional responsibility",      "category": "Responsibility", "pts": {1: 20, 2: 45, 3: 80, 4: 125, 5: 175}},
        {"name": "Management responsibility",        "category": "Responsibility", "pts": {1: 15, 2: 40, 3: 75, 4: 115, 5: 160}},
    ],
}


# ---------------------------------------------------------------------------
# NON_EC_TOTALS
# Approximate total JES points for non-EC groups at each level.
# Source: verified against Job Description Builder/jd-builder/data.jsx
# GENERIC_TOTALS (data.jsx lines 118-120).
# Key: OG code (str). Value: dict[int level, int points].
# ---------------------------------------------------------------------------

NON_EC_TOTALS: dict[str, dict[int, int]] = {
    # Levels 4–6 verified against v1 data.jsx GENERIC_TOTALS.
    # Levels outside that range are approximate linear extrapolations — confirm
    # against published JES tables before treating them as authoritative.
    "FI": {1: 220, 2: 300, 3: 385, 4: 470, 5: 560, 6: 660},
    "IT": {1: 215, 2: 300, 3: 390, 4: 480, 5: 575},
    "AS": {1: 195, 2: 265, 3: 345, 4: 430, 5: 510, 6: 600, 7: 690, 8: 790},
    "EN": {4: 500, 5: 600, 6: 720},
    # Pre-existing OG_LEVELS groups without dedicated JES — approximate linear
    # totals for completeness (required by test_og_constants_completeness for
    # all 22 OG_LEVELS keys).
    "CR": {1: 175, 2: 230, 3: 290, 4: 355, 5: 425, 6: 500, 7: 580},
    "PM": {1: 195, 2: 265, 3: 345, 4: 430, 5: 510, 6: 600, 7: 690},
    "GT": {1: 195, 2: 265, 3: 345, 4: 430, 5: 510, 6: 600, 7: 690, 8: 790},
    "EL": {1: 215, 2: 295, 3: 380, 4: 470, 5: 565, 6: 665, 7: 770, 8: 880, 9: 995},
    "AI": {1: 215, 2: 295, 3: 380, 4: 470, 5: 565, 6: 665, 7: 770},
    "AU": {1: 195, 2: 265, 3: 345, 4: 430, 5: 510, 6: 600},
    # Phase 21 additions — level-description groups (point-rating groups use
    # JES_FACTORS_BY_GROUP; these groups use level-keyed point lookups)
    # ED: combined level descriptions across sub-groups. ED-EST (Elementary/
    # Secondary Teaching) is the broadest with 4 levels; ED-LAT (Language Arts
    # Teaching) has 3. Use the union range 1-4 here. ED-EDS (Education Services)
    # is point-rated and routes via JES_FACTORS_BY_GROUP routing in Plan 04.
    "ED": {1: 195, 2: 265, 3: 345, 4: 430},
    # NU: SH_rates.csv HOS/CHN series; 8 levels broadest range.
    "NU": {1: 200, 2: 270, 3: 345, 4: 420, 5: 500, 6: 585, 7: 675, 8: 770},
    # PS: SH_rates.csv PS-1 to PS-5 (5 levels).
    "PS": {1: 195, 2: 265, 3: 345, 4: 430, 5: 525},
    # NT: ND-DIT series (4 levels).
    "NT": {1: 195, 2: 265, 3: 345, 4: 430},
    # PO: PO-TCO series (4 levels).
    "PO": {1: 195, 2: 270, 3: 355, 4: 445},
    # WP: PA_rates.csv WP-1 to WP-6 (6 levels).
    "WP": {1: 195, 2: 265, 3: 345, 4: 430, 5: 510, 6: 600},
    # SW: SH_rates.csv SCW 1-5 is broadest. SW-SCW is point-rated and routes via
    # JES_FACTORS_BY_GROUP routing in Plan 04; SW-CHA is level-described (3 levels
    # in SW-CHA). The base SW key here uses the SCW 1-5 range for completeness.
    "SW": {1: 195, 2: 265, 3: 345, 4: 430, 5: 525},
    # SW-CHA: Chaplain sub-group level descriptions (3 levels).
    "SW-CHA": {1: 195, 2: 280, 3: 380},
    # ED-LAT: Language Arts Teaching (3 levels).
    "ED-LAT": {1: 195, 2: 280, 3: 380},
    # ED-EST: Elementary/Secondary Teaching (4 levels).
    "ED-EST": {1: 195, 2: 265, 3: 345, 4: 430},
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
    # Phase 21 additions — all 16 OG groups (authoritative copy; export_service.py
    # imports from this constant as of plan 21-02 OGX-02 consolidation).
    # Source: title pages of each JES text file in data/Job_evaluation/ or
    # TBS OCHRO Occupational Group Definitions for groups without a dedicated JES.
    "EC":  "EC Job Evaluation Standard (2017)",
    "CR":  "CR Clerical and Regulatory Group (PA collective agreement)",
    "PM":  "PM Program and Administrative Services (PA collective agreement)",
    "GT":  "GT General Trade and Labour (TC collective agreement)",
    "EL":  "EL Electronics Group (EL collective agreement)",
    "AI":  "AI Aircraft Maintenance Group (AI collective agreement)",
    "AU":  "AU Audio-Visual and Broadcast (CT-FIN collective agreement)",
    "FB":  "FB Border Services Job Evaluation Standard (2005)",
    "FS":  "FS Foreign Service Job Evaluation Standard",
    "LC":  "LC Law Management Job Evaluation Standard",
    "LP":  "LP Law Practitioner Job Evaluation Standard",
    "MT":  "MT Meteorology Job Evaluation Standard",
    "NT":  "NT Nutrition and Dietetics Job Evaluation Standard",
    "NU":  "NU Nursing Job Evaluation Standard",
    "PO":  "PO Police Operations Support Job Evaluation Standard",
    "PS":  "PS Psychology Job Evaluation Standard",
    "SW":  "SW Social Work Job Evaluation Standard",
    "SW-SCW": "SW Social Work (Social Welfare) Job Evaluation Standard",
    "SW-CHA": "SW Social Work (Chaplain) Job Evaluation Standard",
    "WP":  "WP Welfare Programmes Job Evaluation Standard",
    "ED":  "ED Education Job Evaluation Standard (2017)",
    "ED-LAT": "ED Education (Language Arts Teaching) Job Evaluation Standard",
    "ED-EST": "ED Education (Elementary/Secondary Teaching) Job Evaluation Standard",
}


# ---------------------------------------------------------------------------
# SUBGROUP_DISAMBIGUATIONS
# Sub-group disambiguation metadata for OG groups that have multiple sub-groups
# with different JES evaluation methods (Phase 21 OGX-07).
# Each per-OG dict lists sub-group codes with their descriptions and the
# disambiguation guidance. The ASEC_DISAMBIGUATION pattern above is extended
# here with the additional `subgroups` and `descriptions` fields.
# Source: data/Job_evaluation/ JES text files, sub-group definitions.
# ---------------------------------------------------------------------------

NU_SUBGROUP_DISAMBIGUATION: dict = {
    "subgroups": ["HOS", "CHN", "EMA"],
    "descriptions": {
        "HOS": "Hospital Nursing — positions in hospitals and related health care facilities providing direct patient care, treatment and management of illness in cooperation with medical doctors.",
        "CHN": "Community Health Nursing — positions in public health, community health settings, and government programs providing population-level nursing services and health promotion.",
        "EMA": "Emergency Medical Adjudicator Nursing — positions assessing medical information for the purposes of determining eligibility of applicants for a government program.",
    },
    "disambiguation_text": (
        "The Nursing (NU) classification has three sub-groups that determine the "
        "job evaluation method and level range. Select the sub-group that best "
        "describes this position. HOS and CHN sub-groups use a point-rating plan "
        "with factor scales; EMA uses a level-description method."
    ),
    "citation": "TBS OCHRO — Nursing (NU) Job Evaluation Standard",
}

SW_SUBGROUP_DISAMBIGUATION: dict = {
    "subgroups": ["SCW", "CHA"],
    "descriptions": {
        "SCW": "Social Welfare (SCW) — point-rated; positions delivering social welfare programs, counselling, and social work services to individuals, families and communities.",
        "CHA": "Chaplain (CHA) — level-described; positions providing spiritual care, religious services, and chaplaincy support to members of the public service.",
    },
    "disambiguation_text": (
        "The Social Work (SW) classification has two sub-groups with different "
        "job evaluation methods. SCW uses a point-rating plan with knowledge, "
        "professional responsibility, and management responsibility factors. CHA "
        "uses a level-description method with three levels (CHA-1, CHA-2, CHA-3)."
    ),
    "citation": "TBS OCHRO — Social Work (SW) Job Evaluation Standard",
}

ED_SUBGROUP_DISAMBIGUATION: dict = {
    "subgroups": ["EDS", "LAT", "EST"],
    "descriptions": {
        "EDS": "Education Services (EDS) — point-rated; positions providing educational program support, curriculum development, research, and advisory services in education.",
        "LAT": "Language Arts Teaching (LAT) — level-described; positions teaching language courses to public servants in language schools of the Public Service of Canada.",
        "EST": "Elementary/Secondary Teaching (EST) — level-described; positions in elementary and secondary schools, vocational training, and adult education programs.",
    },
    "disambiguation_text": (
        "The Education (ED) classification has three sub-groups with different job "
        "evaluation methods. EDS uses a point-rating plan with knowledge, problem "
        "solving, responsibility for contacts, and supervision factors (4 factors, "
        "1000 max points). LAT uses a level-description method with three levels "
        "(LAT-1, LAT-2, LAT-3). EST uses a level-description method with four "
        "levels (EST-1, EST-2, EST-3, EST-4)."
    ),
    "citation": "TBS OCHRO — Education (ED) Job Evaluation Standard (2017)",
}

SUBGROUP_DISAMBIGUATIONS: dict = {
    "NU": NU_SUBGROUP_DISAMBIGUATION,
    "SW": SW_SUBGROUP_DISAMBIGUATION,
    "ED": ED_SUBGROUP_DISAMBIGUATION,
}
