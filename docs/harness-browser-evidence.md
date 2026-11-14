# H4b browser evidence contract

The extension now emits `document_id`, an opaque UUID held in a WeakMap keyed by the actual Document. Snapshots and same-document URL updates reuse it; a replacement Document receives another value. The map survives content-script reinjection in the same realm. URL and revision remain separate concepts.

`Element.section_target` identifies one unique public DOM ID named by an actual same-document fragment link or single `aria-controls` relationship. Cross-document links, ambiguous IDREF lists, duplicate IDs, editable/private targets, unsafe IDs and redacted IDs do not establish a relationship. Closed shadow roots and iframe documents are not inspected or trusted as section evidence.

`Observation.sections` contains at most 24 `{key, label, in_view?, occluded?, scroll_container_id?, reveal_direction?}` entries. Keys are at most 80 characters; public labels at most 160. Section relationships and labels share the existing 6,000-character context budget. An incomplete scan of 2,000 DOM nodes invalidates all ID relationships because uniqueness cannot be established; `sections_truncated` signals this uncertainty. The cap is not a claim that omitted sections are absent.

Geometry-based section visibility intersects the target rectangle with the viewport and clipping ancestors, then requires an uncovered hit. Modal boundaries prevent underlying sections counting as uncovered. Geometry-disabled snapshots expose relationships only; they never claim visibility. A section with no hit-testing capability may be `in_view` but has no affirmative `occluded: false` proof.

`Element.reveal` is an optional `{container_id, direction}` hint. Section reveal hints use flat `scroll_container_id` and `reveal_direction` fields. A hint requires a known scroll pane, an available measured direction and exactly one offscreen axis. Covered panes, overlays, unknown panes and diagonal uncertainty produce no hint. The server must still enforce revision, safety and recovery limits; a hint is never permission to execute or evidence of task completion.

Validation results are reported in the parent implementation worklog. These are observation capabilities, not a claim of autonomous goal completion or installed-extension deployment.
