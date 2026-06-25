---
status: partial
phase: 25-accessible-template
source: [25-VERIFICATION.md]
started: 2026-06-16T19:30:00Z
updated: 2026-06-16T19:30:00Z
---

## Current Test

Phase 25 Accessible Template structurally and functionally complete (19/19 export tests, 150/150 full backend suite green). 9 visual items need human UAT for full sign-off.

## Tests

### 1. Visual layout inspection
expected: Part 1: 17-field position table is correctly formatted (Light Grid Accent 1 style); 3 signature blocks render with print-and-sign lines; Part 2 headings match GoC reference document order and styling; Effort/Working-conditions tables render with Factor/Degree/Points columns
result: [pending]

### 2. Signature blocks contain NO Jinja2-rendered text
expected: Each of the 3 signature blocks shows literal 'Name: ____', 'Signature: ____', 'Date: ____' print-and-sign lines (no field labels, no data binding)
result: [pending]

### 3. {%tr for %} loops in Effort and Working conditions tables
expected: Tables correctly expand/contract based on factor count; empty tables show only header row + placeholder paragraph; tables with factors show header + N data rows (no empty rows, no garbled for/endfor tags visible)
result: [pending]

### 4. Source Document Version Manifest section
expected: Heading 1 'Source Document Version Manifest' followed by one paragraph per source (NOC 4163, JES standard, OG, QUAL) with format 'SOURCE_TYPE - source_id (vsource_version, retrieved DATE)'
result: [pending]

### 5. Amendments appendix hidden when no amendments exist
expected: For a WD with no manager amendments, the 'Appendix: Manager Amendments for Review' Heading 1 should NOT appear in the document
result: [pending]

### 6. MT/AS placeholder rendering
expected: Effort and Working conditions sections show '[To be completed by advisor]' placeholder text; tables are empty (just header row)
result: [pending]

### 7. SPA download flow end-to-end
expected: Clicking 'Word document (.docx)' in the Review screen triggers a file download with a slugified filename like 'policy-analyst-work-description.docx' and the file opens correctly in Word
result: [pending]

### 8. Poster export parity
expected: POST /api/wd/{id}/export/poster still renders poster_template.docx with bilingual headers, OG/level, quals, and 3-5 duties - same output as before Phase 25
result: [pending]

### 9. Word Document Inspector
expected: No hidden fields, no personal metadata, no template-internal variables leaking into output
result: [pending]

## Summary

total: 9
passed: 0
issues: 0
pending: 9
skipped: 0
blocked: 0

## Gaps
