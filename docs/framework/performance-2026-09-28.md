# Playback and English UI audit — 2026-09-28

This change optimizes the three current public scene entrypoints (South Kensington,
White City and Wind farm) and the contract viewer. It preserves simulation values,
coordinates, timestamps and source geometry. It is not a claim of globally optimal
performance or physical validation.

## Changes

- Wind farm renders directly to its visible WebGL canvas. Normal playback no longer
  copies every frame through a second canvas. Explicit JPEG export still composites
  the scientific annotations. Static geometry is batched after moving rotors are
  detached; static comparisons reuse the field texture.
- Static or paused wind and contract views stop scheduling continuous rendering.
  City views skip GPU draws when nothing visible changes. Hidden tabs freeze the
  active animations and resume without counting the hidden interval.
- Grid widgets reuse unchanged frames. A late request cannot overwrite a subsequent
  return to the currently displayed frame; out-of-range data remains unavailable.
- Wind titles and legends are readable HTML overlays. Controls reserve stable space
  for the clock and Play/Pause labels to prevent layout movement during playback.
- Public website UI and local experiment UI are English. The Chinese framework
  protocol remains a repository document. Previously published comparison/report
  HTML now has managed source templates, so rebuilds preserve the translations.

## Evidence

Headless Chromium with SwiftShader, 1280 × 900; these measurements are not a hardware
FPS benchmark. Baseline wind capture counted 6,648 WebGL draw calls and 12 canvas
copies over two seconds (12 rendered frames, approximately 554 calls per frame).
The optimized view reports 113 calls per frame, with 459 static meshes merged into
18 batches. An idle 1.5-second sample added zero renders and zero texture updates.
Normal live playback performed zero canvas copies. Explicit JPEG export uses two.

Regression coverage:

- 40 Python checks and 10 JavaScript unit checks; protocol fixture validation.
- `browser_grid_timing.cjs`: binary interpolation, delayed-request race, unavailable
  time and recovery.
- `browser_idle_rendering.cjs`: contract-viewer idle/play/pause/layers and city
  pause/background/resume.
- `browser_wind_performance.cjs`: idle, model change, playback, pause, background,
  resize, canvas-copy count and composited JPEG export.
- `browser_legacy_controls.cjs`: desktop and mobile hit targets, keyboard seeking,
  field/layer controls and the three-scene navigation round trip.
- Full city models load from the existing public resource host, with no uncaught
  script errors or lost WebGL contexts in the tested runs.

The built site's HTML, JavaScript and module files (excluding third-party vendor
code) contain no Chinese text. Scene configuration and the companion resource
homepage/catalogue were also scanned. This text audit does not translate text
embedded in historical scientific images or third-party content.

## Limits

Large city geometry remains expensive to draw on low-powered devices; lightweight
mode remains available. The historical standalone UAV demo and unpublished solver
experiment viewers are not included in the new playback performance measurements.
Actual mobile GPUs, sustained memory behavior over many hours and every recorded
frame have not been exhaustively tested. Missing public bird trajectories remain
unavailable, with their controls disabled; no replacement trajectories were invented.
