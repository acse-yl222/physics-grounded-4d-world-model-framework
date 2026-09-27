# Paper rotor port and controlled comparison

Source: Davidson, Barajas & Lara, **Turbines and thrusters: A versatile OpenFOAM framework for modelling aerial rotors on floating bodies**, corrected proof, 2026, https://doi.org/10.1016/j.joes.2026.07.020 (32 pages).

## What is implemented

- `../windfarm_2m/mac_torch.py`: pure PyTorch port of our MAC solver, with a fixed Conv3d pressure stencil. Staggered velocities, first-order upwind advection, masked pressure operator, multigrid-preconditioned CG, pressure outlet. No trained weights; this is a fixed-operator physics solver, not learned neural inference.
- `rotor.py`: paper §2.2 Gaussian weighting, finite cylinder/annulus, arbitrary rotor orientation/position, weighted relative hub inflow, Ct-to-induction mapping, velocity-dependent turbine thrust or prescribed signed thrust, equal/opposite fluid force, body force and lever-arm torque. This torque is platform pitching torque, **not blade shaft torque**.
- `verify.py`: force conservation, relative-velocity response, agreement with old Ct-prime loading, pressure divergence, uniform flow, GPU comparison to original Triton code.
- `compare.py`: matched small single-phase CFD experiment isolating implementation backend and rotor spatial weighting. It does **not** use the original windfarm geometry, and is **not** Appendix B.2 validation.

## Reproduction boundary

The paper's full model uses overInterDyMFoam, VoF/MULES, k-omega SST with a wave-related limiter, overset interpolation, sixDoFRigidBodyMotion, wave generation/absorption and mooring restraints. None of those extra coupled modules has been reproduced here. Prescribing a moving hub does not solve floating-body dynamics. PyTorch pressure projection is not OpenFOAM SIMPLE/PIMPLE.

No original OpenFOAM run or author result array is available in this workspace. Therefore no numerical accuracy or speed claim against OpenFOAM is supported. Workstation inspection found no simpleFoam or standard OpenFOAM installation. The comparison is **our Triton solver vs its PyTorch port vs a different rotor force kernel**, not OpenFOAM vs Neural Physics.

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

```sh
python tools/paper_rotor/verify.py
python tools/paper_rotor/compare.py --out output/paper_rotor
python tools/paper_rotor/compare.py --out output/paper_rotor/refined --cell .05 --refine-only
python tools/paper_rotor/render.py
```
Dependencies: torch, numpy, matplotlib, pillow; optional Triton for GPU backend comparison.
