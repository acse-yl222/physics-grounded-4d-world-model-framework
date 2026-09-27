# Published resources and scene entrypoints

The framework repository owns solvers, viewers, schemas and scene/view configuration.
The companion [resource repository](https://github.com/acse-yl222/urban-world-model-models)
owns selected publishable geometry and simulation assets. Its historical repository URL
is retained for compatibility; its display name is Physics-Grounded 4D World Model Resources.

## Ownership and versioning

Canonical asset paths are `project/<scene>/<category>/<version>/...`; categories include
geometry, input, runs and previews. `resources.json` indexes resource IDs, scene IDs,
category, version, format, relative asset paths, sizes, SHA-256 hashes, source revision/path
and licensing notes. Published versions are immutable; changed assets get new versions.
Scene-local resources.json files list the matching resource IDs.

The resource catalogue is distinct from the simulation run contract. A resource can be
a chunked GLB, an original input or a legacy result export. Publishing an old result does
not make it protocol-compliant or scientifically validated. Preserve its recorded units,
coordinates, time sampling, masks and assumptions; use an explicit adapter for a new widget.

Four existing public resource versions are registered: South Kensington geometry,
White City geometry, windfarm geometry and windfarm movie/comparison data. No private
local dataset is selected for publication. Other city fields, replays and auxiliary assets
remain on the framework's pages branch until a separately validated migration.

## Compatibility

The historical `core008/manifest.json` and `white_city/manifest.json` URLs remain working
chunk manifests. Their file entries resolve to canonical part paths; clients resolve each
part relative to its manifest. Historical direct part URLs have moved. New configurations
use the canonical manifests. The existing model loader already supports relative paths.

The resource repository includes `tools/check_resources.py`, which verifies all indexed
file hashes/sizes, both canonical and compatibility manifests, assembled GLB header/size,
and scene ownership. Do not infer a global licence or reuse permission from public hosting.

## Website navigation

The homepage is a scene chooser, with South Kensington, White City and windfarm alongside
a separate synthetic protocol example. These published scene entries use the existing
specialized viewers; the example exercises the new unified protocol widget implementation.
`src/visualization/public-scenes.json` declares entrypoints and resource IDs. The unified
viewer's selector also links to those published scene viewers.

`tools/build_public_site.py` maps local legacy viewer routes to published routes and writes
canonical resource URLs. Windfarm loads its configurable data/model URLs from resources.json
next to its viewer. Old site asset routes remain available for compatibility.

For code-only clones with no local run directories, `p4d serve` resolves homepage scene
links to the published site. Local protocol scenes remain selectable in the unified viewer.
