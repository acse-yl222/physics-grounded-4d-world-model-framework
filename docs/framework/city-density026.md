# Three-scene activity update 026

The shared 3D viewer now displays 600 illustrative UAVs and 100 directed computed routes per scene, with 2.5-pixel corridors and screen-sized station labels. South Kensington and White City retain their original 870-route datasets and select a connected 100-route network through all 30 stations. Canary Wharf has 20 stations and 100 newly computed Wave PDE routes, audited against the building voxels; there is no multi-aircraft collision scheduling or verified real-world landing access.

| Scene | Visible / moving at 600 s | Peak visible | Collision events / teleports |
|---|---:|---:|---:|
| South Kensington | 1721 / 963 | 3232 | 5 / 0 |
| White City | 1373 / 1034 | 2396 | 0 / 0 |
| Canary Wharf | 1402 / 766 | 2610 | 3 / 0 |

Traffic is recorded SUMO output with synthetic demand, not observed traffic. Playback preserves actual seconds 1–1200 and starts at 600 s. The time controls do not imply coupling with the separately computed weather or UAV clocks. Model-only junction exclusions affect 48/7690, 52/8550 and 29/7951 road edges respectively; road geometry is preserved. Residual collision events remain disclosed, not suppressed. Zero White City events do not establish calibration.

The per-scene `city_density026.json` configurations identify immutable retained runs. These include inputs, code snapshots, commands, actual trajectories, signal states, verification and browser exports. Deterministic pose recovery matched every original position and signal; South legacy float export has at most 0.000243 m sampled encoding error. No missing traffic frames are invented.

Validation: protocol manifests and 12 Node tests passed. Browser checks cover all three scenes, actor counts, 100-route selection, station counts, seeking, visibility, camera bounds and actual traffic counts. The full Python suite ran 190 tests with 9 skips and five pre-existing errors in `test_public_windfarm_resources`: the baseline builder lacks its expected `windfarm_resources` function. Other tests passed. Publication preserves the existing wind-farm resource configuration.

Publication uses `tools/build_public_site.py` then `tools/package_city_density.py` against a separate Pages checkout. Only selected browser exports are copied; geometry manifests and environmental field assets remain unchanged. Framework development stays on the feature branch; Pages uses its deployment branch.
