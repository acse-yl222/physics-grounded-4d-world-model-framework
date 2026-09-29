# Paper rotor port and controlled comparison

Source: Davidson, Barajas & Lara, **Turbines and thrusters: A versatile OpenFOAM framework for modelling aerial rotors on floating bodies**, corrected proof, 2026, https://doi.org/10.1016/j.joes.2026.07.020 (32 pages).

## What is implemented

- `../solvers/mac_torch.py`: pure PyTorch port of our MAC solver, with a fixed Conv3d pressure stencil. Staggered velocities, first-order upwind advection, masked pressure operator, multigrid-preconditioned CG, pressure outlet. No trained weights; this is a fixed-operator physics solver, not learned neural inference.
- `rotor.py`: paper §2.2 Gaussian weighting, finite cylinder/annulus, arbitrary rotor orientation/position, weighted relative hub inflow, Ct-to-induction mapping, velocity-dependent turbine thrust or prescribed signed thrust, equal/opposite fluid force, body force and lever-arm torque. This torque is platform pitching torque, **not blade shaft torque**.
- `verify.py`: force conservation, relative-velocity response, agreement with old Ct-prime loading, pressure divergence, uniform flow, GPU comparison to original Triton code.
- `compare.py`: matched small single-phase CFD experiment isolating implementation backend and rotor spatial weighting. It does **not** use the original windfarm geometry, and is **not** Appendix B.2 validation.

## Reproduction boundary

The paper's full model uses overInterDyMFoam, VoF/MULES, k-omega SST with a wave-related limiter, overset interpolation, sixDoFRigidBodyMotion, wave generation/absorption and mooring restraints. None of those extra coupled modules has been reproduced here. Prescribing a moving hub does not solve floating-body dynamics. PyTorch pressure projection is not OpenFOAM SIMPLE/PIMPLE.

No author case dictionary or original author result array is available in this workspace.
The old `compare.py` remains **our Triton solver vs its PyTorch port vs a different rotor force kernel**.
On 2026-09-29 an independent official OpenFOAM 2312 container reference was added (see below);
it does not turn the old comparison into an OpenFOAM validation or speed benchmark.

## Formula correspondence

Paper Eqs. 8-11:

`ud = abs(dot(sum(u_i W_i V_i)/sum(W_i V_i) - v_hub, axis))`

`a = (1 - sqrt(1-Ct))/2`

`T = 2 rho A a/(1-a) ud^2 = 0.5 rho A Ct_prime ud^2`

For Ct=0.75, a=0.25 and Ct_prime=4/3: this is exactly the existing load law for a stationary hub and identical sampled velocity. New differences arise from spatial weighting, relative motion and coupling, not from renaming the algorithm.

Paper Eq.6 contains a cell-volume factor and describes a source per mass while Eq.5 writes a momentum source. Here dimensions are explicit: integrated cell force is `-T axis W_i V_i / sum(W V)`; cell acceleration is that divided by `rho V_i`. Thus `sum(rho acceleration V) = -body_force`. There is no extra grid-dependent volume multiplier.

Positive thrust is force on the body along `axis`; fluid force is opposite. Set signed thrust/axis consistently for fan use. Swept area is pi R^2; inner hole changes force support only (a documented assumption requiring original case confirmation for B.2).

## Controlled pilot

Domain 9.6 x 3.2 x 3.2 m, hub (2.4,1.6,1.6) m, D=0.8 m, U=2 m/s, Ct=0.75, rho=1.225, sigma=0.2 m, Gaussian cut at +/-2 sigma for paper kernel. Legacy variant uses untruncated axial Gaussian and logistic radial edge 0.05 m. These are pilot settings, not quoted paper benchmark parameters. Same full-disc area, inflow, pressure solver and 1 s startup ramp in each case. No explicit viscosity/turbulence closure; first-order advection adds numerical diffusion.

0.1 m mesh: 96x32x32 cells; 10 physical seconds; 667 steps. Fine run: 0.05 m, 192x64x64; same physical kernel and duration. No steady-state certification or engineering validation. Saved slices are staggered x-face velocities at nearest hub-height plane, not reconstructed cell-centred full vectors.

TF32 is disabled for pressure convolutions: reduced precision caused the independent divergence test to fail on RTX 5090. CPU float32 and GPU full-float32 tests pass. Timing is a single small-case run including startup/compilation, not a general performance benchmark. Pure PyTorch uses more temporary memory than fused Triton; full windfarm memory feasibility has not been tested.

## Paper B.2 setup for the next validation stage

The paper specifies U=10 m/s, Ct=0.95, outer diameter 0.4647 m, inner diameter 0.09 m, axial thickness 0.08 m, slip side/top, no-slip bottom, flow outlet, no tower or nacelle. It uses steady simpleFoam with k-epsilon and k-omega SST, approximately 3.4 million cells, and profiles at x/D=1,3,5. Table 8 gives anisotropic medium spacing (0.033,0.046,0.033) m. This port currently assumes cubic cells and lacks those closures/no-slip wall treatment.

Need original case dictionaries or independently justified values for turbulence inlet conditions, wall functions, numerical schemes and interpretation of annular area/width before claiming matched validation. Digitising published plots would provide approximate references only, not author raw data. Table 9 reports 19.7% grid uncertainty for the selected wind-tunnel control quantity: even matching this figure does not establish globally converged accuracy.

## Run

### Independent OpenFOAM RANS reference

```sh
PYTHONPATH=src python -m urban_flow.paper_rotor.openfoam_reference --model kOmegaSST --iterations 2000
PYTHONPATH=src python -m urban_flow.paper_rotor.openfoam_reference --model kEpsilon --iterations 2000
PYTHONPATH=src python -m urban_flow.paper_rotor.analyze_reference <printed-run-directory>
```

Requires the official image pinned by digest in `openfoam_reference.py` and a working
Docker service. The generator uses a uniform mesh, no-slip floor with wall functions,
slip top/side walls and the official RANS closures. Its independent C++ weighted source
uses global reductions across MPI partitions. It runs with the calling user's identity,
no container network, and access only to its new cache case directory.

At present this isolates closure/boundary differences on the pilot domain. Original
wind-tunnel geometry, Gaussian details and inlet turbulence are still under verification.
The reference's inlet turbulence intensity/length are explicit configurable assumptions,
not claimed author values. `solver_finished` is not numerical convergence; the analyzer
checks residuals, continuity and thrust-window drift separately. Reference profiles are
static protocol layers: SIMPLE iterations must never become animation seconds. See
`project/actuator_lab/reproduction_progress.md` for remaining evidence and live runs.

### 10 m/s uniform-grid experiment

The independent entrypoint below uses the wind-tunnel rotor parameters (10 m/s,
Ct=0.95, outer/inner diameters 0.4647/0.09 m, thickness 0.08 m). Configuration:
`project/actuator_lab/configs/paper_rotor_10ms.json`. It does not change old runs.

```sh
PYTHONPATH=src python -m urban_flow.paper_rotor.wind_tunnel
PYTHONPATH=src python -m urban_flow.paper_rotor.wind_tunnel --cell .02
PYTHONPATH=src python -m unittest discover -s tests -p test_paper_rotor.py -v
```

Use an environment with Torch, Triton, NumPy, Matplotlib and jsonschema; `--backend
torch` selects the reference backend. Results go to a unique
`cache/actuator_lab/paper_rotor_10ms/<run_id>` directory, with a protocol manifest,
source snapshot, configuration, thrust history, exact hub-height velocity slices,
profiles at 1D/3D/5D and overview plot. Time stepping uses a CFL bound and an
acceleration bound; cell-to-face integrated force conservation is checked at every
step. Refinement keeps physical rotor dimensions and smoothing fixed.

This is a **numerical pilot, not completed paper validation**. The domain, hub
position, density, Gaussian sigma/cutoff and startup are explicitly recorded
choices, not author-case data. The 0.04 m pilot has only two cells across rotor
thickness; 0.02 m has four. MAC retains slip bottom and first-order upwinding with
no turbulence closure. The paper's no-slip bottom, k-epsilon / k-omega SST,
experimental inlet turbulence, full tunnel geometry and author reference profiles
are not reproduced. Final thrust is compared with ideal unbounded actuator theory
only as a diagnostic, never as experimental validation. A prescribed uniform
10 m/s *disk* speed is not the same as 10 m/s upstream speed after induction.

```sh
PYTHONPATH=src python -m urban_flow.paper_rotor.verify
PYTHONPATH=src python -m urban_flow.paper_rotor.compare --out cache/actuator_lab/legacy_pilot/manual
PYTHONPATH=src python -m urban_flow.paper_rotor.compare --out cache/actuator_lab/legacy_pilot/manual/refined --cell .05 --refine-only
```
Dependencies: torch, numpy, matplotlib, pillow; optional Triton for GPU backend comparison.
