# Portable app / Interspeech 2026 validation

Verified on Windows x64, 2026-11-05. App code v0.2.0, bundled TinyTeX v2026.11.

## Official input

- Conference source: https://interspeech2026.org/pages/author-resources/submission-policy
- Paper kit linked by that site: https://drive.google.com/file/d/1Nq1j_1AfOtadLkBx71-vLVLxZOaiAnzs/view
- SHA256: `7cddd7ab6136e8ca0157b9dbd479cb016f321cd54dff6582dffa8e059980a712`
- Files used: `template.tex`, `Interspeech.cls`, `IEEEtran.bst`, `mybib.bib`, `figure.pdf`.
- Camera-ready uses the original source. Review changes only the active document-class option to `\documentclass{Interspeech}`.
- The kit is downloaded by the validation script, not vendored into this repository.

## Results

| Mode | Pages | Cold compile + render | Unchanged-source cache hit | Unresolved references/citations |
| --- | ---: | ---: | ---: | --- |
| Camera-ready | 6 | 2.83 s | 0.0069 s | None in final pass |
| Review | 6 | 2.77 s | 0.0072 s | None in final pass |

These are single-run local backend measurements, including PDFium rendering for cold builds. UI image loading is not included. Cold-build time varies with system load; no cold-build speedup is claimed.

Both outputs are A4. Review hides the sample author names and includes line numbers; camera-ready shows the sample author block. All pages were visually inspected, with the figure page also checked at full size using Poppler. The template emits underfull-box and shell-escape-disabled notices, but no missing package or unresolved citation remains in the final pass. The official template content/formatting was not rewritten to suppress notices.

## Regression checks

- Eleven tests: data persistence, path escape refusal, real TeX success/failure, failed-build PDF invalidation, content cache invalidation, nested entry files with adjacent inputs, local-only AI URLs, settings persistence, portable data-directory selection, incremental deployment copies, Windows parent-termination cleanup.
- Packaged EXE self-test: system TeX and external renderers excluded from PATH, bundled pdfLaTeX/BibTeX/PDFium used successfully.
- Existing documents/settings are copied from the former LocalAppData location into `D:\RocalPaper\data`; the old copy is retained.
- Existing TeX and existing GGUF assets are reused rather than downloaded or duplicated.

Reproduce with `python validate_interspeech.py --app-root <application-folder>` using the desktop build environment. It creates new validation projects on each run to avoid overwriting edited manuscripts.
