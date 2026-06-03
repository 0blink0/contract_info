# hiddenimports changelog

## 2026-05-28

- Added initial `ctrx_backend.spec` hiddenimports baseline.
- Split hiddenimports by `common/windows/linux`.
- Locked excludes with explicit `psycopg2` removal.

## 2026-06-02

- Phase 23 (KB-PKG-01): Appended lancedb/pyarrow/sentence-transformers/torch/tokenizers/
  transformers/huggingface_hub entries to `windows_hidden` for KB embedding pipeline
  packaging.
- Rationale: lancedb uses a Rust extension (`lancedb._lib`) and pyarrow uses C extensions;
  PyInstaller static analysis cannot resolve all dynamic imports. sentence-transformers
  requires torch, tokenizers, transformers, and huggingface_hub at runtime.
- Platform scope: Windows only (D-02); Linux deferred to next milestone.
