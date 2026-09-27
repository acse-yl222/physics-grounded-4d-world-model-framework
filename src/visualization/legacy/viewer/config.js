/* Deployment flags. Locally (and on the workstation) every scene's models sit in scenes/<id>/models/; on the GitHub Pages copy
   a city model over GitHub's 100 MB limit is fetched in parts from the companion Pages site (scene.json: model.parts_manifest,
   see model-source.js; release assets lack CORS headers). Everything else the page loads (supplement, refined buildings, field
   frames, replay data) is small enough to live in this repository. */
export const ON_PAGES = /\.github\.io$/.test(location.hostname);
