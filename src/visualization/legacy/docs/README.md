# Project page

`docs/index.html` is the GitHub Pages site for this repository: one page that introduces every module
(geometry, wind, temperature, pollution, flooding, traffic, UAVs, birds, the viewer) and how they share one
coordinate frame. Figures in `docs/media/` are downscaled copies of `scenes/south_kensington/physics/figures/`,
`agents/demo_rev02/evidence/maps/`, `geometry/completion/reports/` and headless screenshots of `viewer/3d/`
(`?pose=…` URLs, see the page's "Run it" section).

Publish: push the repository to GitHub, then **Settings → Pages → Build and deployment → Source: Deploy from a
branch → Branch: main, folder: /docs**. The page is served at `https://<user>.github.io/<repo>/`.
The README and module links on the page are relative (`../README.md`, `../scenes/south_kensington/physics/…`) and resolve on
GitHub's rendered file view.

Preview locally: `python3 serve.py` then open `http://localhost:8787/docs/`.
