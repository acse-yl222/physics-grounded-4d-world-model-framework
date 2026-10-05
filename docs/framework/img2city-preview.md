# Local Img2City geometry preview

`p4d import-img2city` imports an existing GLB and its `buildings.json` into an
independent protocol run and named view. It does not regenerate buildings, execute
model calls, upload assets, or replace the original scene/default view.

```sh
p4d import-img2city /path/to/model.glb --metadata /path/to/buildings.json \
  --scene south_ken --run-id img2city_preview --view-id img2city_preview
p4d serve --port 8769
```

Open `/src/visualization/viewer/?scene=south_ken&view=img2city_preview` to use the
registered view. For a camera fitted tightly to this model, open
`/src/visualization/viewer/?manifest=/project/south_ken/runs/img2city_preview/manifest.json`.
The registered scene retains its original larger spatial extent.

The adapter uses the source `anchor.lat0`, `anchor.lon0` and `anchor.proj=equirect`
recorded by Img2City, rebases horizontal coordinates to the canonical scene origin,
and preserves local ground zero. The source projection uses 111320*cos(lat0) metres
per longitude degree and 110540 metres per latitude degree. This is the original
local approximation, not surveyed terrain or a full geodetic reprojection. Check
independent control points before combining it with physical fields.

Source GLB and metadata are unchanged. A root transform is added to the retained
GLB; the binary payload and embedded textures are preserved. Authored animations
are omitted from the preview because this import is a static geometry layer, not
a protocol traffic replay. Skins and morph targets require a baked export first.

The manifest records source hashes, coordinate conversion, transformed mesh bounds,
and an import-adapter snapshot. The historical generation revision is explicitly
unknown; the adapter snapshot does not claim to reproduce the original generation.
`complete` means the import is validated, not that the city reconstruction is complete
or visually accepted.

The importer writes a trial under `cache/south_ken/img2city_import/` and then retains
the self-contained result under `project/south_ken/runs/`. Large run assets remain
Git-ignored. A fresh run/view ID is required for each import. The copied Img2City
generation package remains independently configurable; no wind, thermal, flooding
or traffic computation is automatically connected by this preview.
