# RocalPaper product foundation — 2026-11-05

## Intended user

A Japanese-speaking researcher who can describe the research but does not yet know LaTeX. The core loop is: describe a small change → understand an example → insert or revise → compile → inspect the result → undo or restore if necessary. Translation is also a learning activity; explanations must remain separate from manuscript text. An experienced TeX user's IDE is not the only design reference.

## Evidence and comparison

Reviewed SciPen Studio's [repository](https://github.com/scipenai/scipen-studio), [user guide](https://github.com/scipenai/scipen-studio/blob/main/docs/USER_GUIDE.md) and [releases](https://github.com/scipenai/scipen-studio/releases). These are documented features, not an independent stability benchmark. SciPen was not installed or stress-tested here.

| Area | SciPen documents | RocalPaper decision / gap |
| --- | --- | --- |
| Installation | OS installers; bundled WASM compilers | 0.3 NSIS installer, bundled Chromium/Python/TinyTeX; source remains public; binary publication is separate |
| Editing | Monaco, language servers, completion and diagnostics | Current textarea lacks syntax highlighting, completion, search/replace and precise error navigation; next editor milestone |
| PDF | pdf.js, zoom and two-way SyncTeX | Current page images/PDF download; independent PDFium worker; SyncTeX and per-pane zoom remain pending |
| Recovery | Local history, diffs and restore | 0.3 autosave, bounded per-file history, draft recovery; visual diff review and whole-project checkpoints remain pending |
| AI | Built-in agent, inline edits and reviewed changes | 0.3 learning tasks, translation explanations and offline lessons; retain explicit application of replacement text |
| Research workflow | Zotero and Overleaf sync | Pending; first add project/ZIP import and attachment UI before cloud synchronization |

## Why the old application could not close

The old `closing` callback synchronously queried renderer JavaScript and returned false whenever the UI's busy flag was true. It therefore deliberately blocked closing during slow work, and depended on a responding renderer for its own exit decision. The user's exact forced-exit crash has not been independently attributed to a native stack trace; no crash trace existed in the old build. Replacing Python syntax with another language alone would not establish reliability.

0.3 uses Electron for the window, installer integration and native close decisions. A separate Python worker hosts the existing document/LLM service. Parent-pipe EOF terminates that service; Windows Job Objects cover its descendants. PDFium runs in a further subprocess. Closing does not query renderer JavaScript and does not wait for TeX or LLM replies. The backend is loopback-only with a random session header, the renderer is sandboxed and context-isolated, and Node.js is not exposed to document content.

Electron costs more disk space and memory than a small native shell, but removes the pywebview/Windows WebView2 dependency and reuses the existing UI. Python remains suitable for the isolated document service. Tauri/Rust would also be a valid later choice, but changing every layer at once would add migration risk without proving the reported failure fixed. See [Electron isolation](https://www.electronjs.org/docs/latest/tutorial/context-isolation) and [process sandboxing](https://www.electronjs.org/docs/latest/tutorial/sandbox).

## Installation, updates and local AI

- The NSIS installer includes the application, Chromium, Python, TeX and PDF renderer. It creates shortcuts and an uninstaller. Re-running the installer updates the application while keeping data separate. See [electron-builder NSIS](https://www.electron.build/docs/nsis/).
- This is not a signed auto-update service. Before general binary distribution: obtain a signing identity, verify third-party redistribution inventory, add signed update metadata, staged downloads, rollback and interruption tests. Do not silently install unsigned remote updates.
- AI is optional. Existing local models are reused; large model weights are not downloaded silently. A proper setup wizard still needs memory/GPU/disk checks, download size/license information, pinned checksums, resumable download, CPU fallback and a short inference test. The existing Rocal LLM folder or a local OpenAI-compatible endpoint remains required for now.
- Missing TeX packages should become actionable diagnostics. Automatic package installation needs a controlled repository/version strategy and a repair path; it is not implemented by executing arbitrary commands from AI output.

## Release gates and next work

Priority 0: close during startup/compile/AI; abrupt parent exit without orphan children; input recovery; corrupted settings; failed saves; offline startup; upgrade and uninstall without deleting papers. Record what is actually tested, not only intended behavior.

Priority 1: ZIP/project import, attachment management, beginner onboarding, editor diagnostics and completion, structured AI response with code/explanation separation and diff review, AI setup wizard.

Priority 2: SyncTeX, bibliography manager integration, multi-engine/Biber support, signed automatic updates and broader OS support.

Before calling this a stable product: repeated clean-machine install/upgrade/uninstall, non-ASCII paths, low disk/read-only directories, unavailable/broken GPU runtime, large documents, resource-use measurement, multi-hour editing and AI sessions, renderer/backend fault injection, accessibility and keyboard review. The current build is a product-foundation preview, not a claim of production readiness.

## Observed checks in this iteration

- Fifteen Python tests and one Node recovery-race test passed locally, including real TeX and Windows process ownership.
- Packaged backend worked with system Python/TeX removed from PATH. Interspeech 2026 camera-ready and review each produced six pages (approximately 3.1 s and 2.9 s, single runs).
- During a deliberately infinite TeX loop, closing the desktop window terminated its backend in 23 ms according to the local lifecycle log. A separate packaged backend test measured parent-pipe shutdown under 10 ms and verified the TeX child terminated. These are individual local observations, not a timing guarantee.
- Packaged rendering initially hung when inheriting the backend's control input. Explicit `stdin=DEVNULL` for document subprocesses resolved the reproduction. The validation script covers that packaged path, not just source-mode execution.
- The real local 4B model initially suggested an unsuitable Japanese package. Learning prompts now identify the actual compiler, and extracted LaTeX examples are compiled in a separate temporary project before reporting verification. Unextractable or failed examples are explicitly marked; explanations remain model-generated and are not automatically applied. Offline lessons provide a deterministic starting point.
- Runtime npm dependencies have no reported advisories in `npm audit --omit=dev`; the build-only dependency tree still reports a moderate minimatch advisory through the macOS universal-packaging dependency. This is tracked as a tooling gap, not represented as a clean full-tree audit.

- Installer deployment to `D:\RocalPaper\app` completed successfully. Existing manuscript source hashes were unchanged. The installed application retained an autosaved test manuscript after forced process termination, reopened it, and generated its PDF in the UI. The test did not interrupt a disk write; filesystem/power-loss durability remains a separate release gate.
- Three packaged desktop startup/shutdown smoke runs completed with no surviving backend process.
