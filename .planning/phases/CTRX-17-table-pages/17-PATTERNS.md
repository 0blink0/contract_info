# Phase 17 — Patterns

| New | Analog |
|-----|--------|
| `useSectionPreview` | `ExportPreview` load/save/dirty |
| `TablePreviewEditor` | Single tab in `ExportPreview.vue` |
| `VerificationExcerptTable` | `ValidationPanel` table styling (read-only) |
| `JobTableView` | Phase 16 stub + inject `detail.status` |
| Section API | `backend/tests/test_preview_section_api.py` contracts |

**Reuse:** `TABLE_DOWNLOAD_FILES`, `downloadBlob`, `useJobDetailInject`, `columnKeys()` helper from ExportPreview.
