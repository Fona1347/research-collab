# PDF Toolchain Appendix

Use this appendix when visual evidence requires PDF page rendering, image extraction, or visual QA. Keep tool details here rather than in the main workflow.

## Preferred Tool Order

1. Verified MinerU cache `manifest.json` plus `images/`.
2. The PDF skill or the local PDF workflow available in the host environment.
3. Poppler tools such as `pdfinfo` and `pdftoppm` for PDF inspection and page rendering.
4. PyMuPDF / `fitz` for page rendering, image extraction, and text block positioning.
5. `pypdf` for structural PDF operations only; do not use it as the main visual QA tool.
6. MinerU API wrapper only when local cache is missing or insufficient and the user explicitly allows external parsing/upload.

## Tool Selection

- Use MinerU `manifest.json` first to identify figure/table labels, captions, pages, and image paths.
- Use MinerU `images/` when images are present, readable, and match the selected figure/table.
- Use PDF page rendering to support figure/panel cropping when images are missing, cropped, unreadable, or mismatched.
- Prefer high-resolution rendering before cropping figures or panels.
- Treat whole-page rendering as an intermediate visual evidence source, not as the default final-note asset.
- Use whole-page rendering as page evidence or QA fallback when figure crops are unreliable.
- Use direct PDF parsing or external MinerU parsing only after user permission.

## Recommended Crop Workflow

1. Render the relevant PDF page at high resolution.
2. Crop the full figure or selected panel from that rendered page.
3. Visually inspect the crop for label, axis, legend, colorbar, scale bar, annotation, and caption consistency.
4. Save accepted crops at the note-specific asset root.
5. Retain the full-page render under `pages/` as QA fallback or page evidence.
6. Put intermediate crop candidates under `qa/` and rejected-but-retained crops under `unused/`.

PyMuPDF / `fitz` is an acceptable default local tool for page rendering, crop generation, and text block positioning. PIL/Pillow can help with resizing or format conversion, but its absence should not block the crop workflow if PyMuPDF can write the needed image output.

## Missing Toolchain Behavior

Do not silently skip visual evidence when tools are missing.

Report the exact missing capability and impact, for example:

- unable to render PDF pages because no PDF rendering tool is available;
- unable to inspect figure images because image files are inaccessible;
- unable to use MinerU cache because no matching verified cache was found.

Minimum viable fallbacks:

- If Zotero plus verified MinerU images are available, generate notes with cached images.
- If Zotero plus PDF is available but no rendering tool is available, generate a no-image note and keep a figure inventory.
- If captions and nearby text are available but images are not, use caption/nearby-text evidence and mark visual evidence as `needs caution`.
- If PDF/full-text access is not allowed, generate only from metadata, notes, and annotations.

Do not automatically install dependencies, download tools, or use network services unless the user explicitly asks.

## Output Rules

- Save visual outputs under the final note's Typora-style sibling asset directory: `<paper-dir>/<note-filename-without-.md>.assets/`.
- Use relative Markdown paths only.
- Put inserted cropped figures and panel crops at the asset root; put full page renders under `pages/`; put QA candidates under `qa/`; put rejected-but-retained crops under `unused/`.
- Prefer Typora-friendly HTML `<img />` syntax.
- Keep derived image width at or below 1200px when possible.
- Record tool limitations, selected fallback, and visual QA result in `source-inventory.md`.
