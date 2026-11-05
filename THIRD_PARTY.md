# Third-party components

The repository's MIT license applies to Rocal Paper source code only, not to
the downloaded TeX distribution, Python runtime, PDFium, fonts, model weights,
or other dependencies. This repository publishes source and build scripts;
it does not redistribute their binary bundles or model weights.

The local build downloads an unmodified, SHA256-verified TinyTeX archive from
its official release and includes it in the user's local application folder.
It retains the distribution's license files and package database.

| Component | Origin / terms |
| --- | --- |
| TinyTeX v2026.11 | https://github.com/rstudio/tinytex-releases/releases/tag/v2026.11 |
| TeX Live / packages / fonts | Individual licenses; `tex/TinyTeX/LICENSE.TL`, `LICENSE.CTAN`, package headers and `tlpkg/texlive.tlpdb`; https://tug.org/texlive/copying.html |
| TeX Live source | https://tug.org/texlive/svn/ and https://tug.org/texlive/acquire.html |
| Python | PSF license; https://docs.python.org/3/license.html |
| pywebview | BSD-3-Clause; https://github.com/r0x0r/pywebview |
| PyInstaller | GPL with bootloader exception; https://pyinstaller.org/en/stable/license.html |
| pypdfium2 / PDFium | Apache-2.0 OR BSD-3-Clause wrapper; PDFium BSD and third-party notices retained by `--collect-all`; https://github.com/pypdfium2-team/pypdfium2 |
| Pillow | HPND and third-party notices; https://github.com/python-pillow/Pillow |
| pythonnet / clr-loader / bottle and dependencies | Package notices copied into `licenses/python-packages` by the builder |
| Microsoft WebView2 | Windows component, used from the host; not redistributed here; https://developer.microsoft.com/microsoft-edge/webview2/ |

Before redistributing a built executable folder, review each component's
redistribution requirements, including corresponding source distribution for
GPL/LGPL components in TeX Live. A license-link list alone is not a substitute
for those obligations. Public binary releases are not part of this source release.
