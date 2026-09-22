# pubfig adapter contract

Sci Plot and pubfig have different JSON schemas. Sci Plot specs map tabular file
columns and enforce project/output safety. Upstream pubfig 0.3.x specs pass plotting
function arguments directly. Never forward a Sci Plot spec to pubfig render or claim
the two schemas are interchangeable.

The default backend setting is auto:

- Prefer a compatible installed pubfig 0.3.x adapter for theme/export support.
- Use the local deterministic Matplotlib renderer when pubfig is absent.
- Record the actual backend in the run log and CLI result.
- If the user explicitly selects pubfig, fail clearly when it is absent or outside
  the supported 0.3.x range; do not install it automatically.

All output paths are selected and staged by Sci Plot before calling an upstream
export function. Never pass through upstream overwrite=true. SVG, PDF, and PNG may use
the pubfig export surface, but Sci Plot passes an explicit FigureSpec, physical width,
height, raster DPI, untrimmed layout, and editable SVG text setting so pubfig defaults
cannot silently replace project settings. TIFF is always produced by the Sci Plot
Pillow adapter and verified as RGBA.

The declared optional dependency is pubfig>=0.3,<0.4. A newer minor or major line
requires a recorded source check, adapter review, isolated tests, and an explicit
dependency-constraint change.
