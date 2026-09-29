"""Independent OpenFOAM RANS reference for the weighted rotor model.

Uniform block mesh, no-slip floor, slip side/top walls, fixed velocity inlet and
pressure outlet. Unknown author inputs remain explicit configuration assumptions.
SIMPLE iteration numbers are never exported as physical animation time.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess

from common.export import digest, write
from common.provenance import snapshot_sources
from common.runtime import trial_root
from common.storage import Storage

IMAGE = 'opencfd/openfoam-default@sha256:097e45046a74ee1dae3e6135df0c42723ba55092d246e7c9932f3bfa1e89b7b2'


def header(name, kind='dictionary'):
    return f'FoamFile {{ version 2.0; format ascii; class {kind}; object {name}; }}\n'


def vector(values):
    return '('+' '.join(f'{v:.14g}' for v in values)+')'


def cpp_vector(values):
    return '('+', '.join(f'{v:.14g}' for v in values)+')'


def rotor_source(config):
    """Generate the independent C++ source, with MPI-global weighted sampling."""
    radius = config['rotor_diameter_m']/2
    inner = config['inner_diameter_m']/2
    sigma = config['sigma_m']
    half = config['rotor_thickness_m']/2
    ct = config['ct']
    axis = config.get('axis', [1, 0, 0])
    norm = math.sqrt(sum(x*x for x in axis))
    if norm <= 0 or not math.isfinite(norm):
        raise ValueError('Rotor axis must be finite and nonzero')
    axis = [x/norm for x in axis]
    imposed = config.get('prescribed_thrust_N')
    load = (f'{float(imposed)/config["rho_kg_m3"]:.17g}' if imposed is not None else
            f'2.0*{math.pi*radius**2:.17g}*induction/(1.0-induction)*sqr(diskSpeed)')
    return header('fvOptions') + '''
paperRotor
{
    type vectorCodedSource;
    active yes;
    selectionMode all;
    fields (U);
    name paperWeightedRotor;
    codeInclude
    #{
        #include "fvCFD.H"
    #};
    codeAddSup
    #{
''' + f'''
        const vector hub{cpp_vector(config['hub_xyz_m'])};
        const vector axis{cpp_vector(axis)};
        const vector hubVelocity{cpp_vector(config.get('hub_velocity_m_s', [0, 0, 0]))};
        const scalar induction = (1.0-sqrt(1.0-{ct:.17g}))/2.0;
        const scalarField& volumes = mesh().V();
        const vectorField& centres = mesh().C();
        const volVectorField& velocity = mesh().lookupObject<volVectorField>("U");
        scalarField weights(volumes.size(), 0.0);
        scalar weightedVolume = 0.0;
        vector weightedVelocity = vector::zero;
        forAll(volumes, celli)
        {{
            const vector delta = centres[celli]-hub;
            const scalar axial = delta & axis;
            const scalar radial2 = max(scalar(0), magSqr(delta)-sqr(axial));
            if (mag(axial) <= {half:.17g} && radial2 <= {radius**2:.17g}
                && radial2 >= {inner**2:.17g})
            {{
                weights[celli] = exp(-sqr(axial)/(2.0*{sigma**2:.17g}));
                weightedVolume += weights[celli]*volumes[celli];
                weightedVelocity += weights[celli]*volumes[celli]*velocity[celli];
            }}
        }}
        reduce(weightedVolume, sumOp<scalar>());
        reduce(weightedVelocity, sumOp<vector>());
        if (weightedVolume <= VSMALL)
            FatalErrorInFunction << "Unresolved rotor" << exit(FatalError);
        const scalar diskSpeed = mag((weightedVelocity/weightedVolume-hubVelocity)&axis);
        const scalar thrustOverRho = {load};
        vector integratedSource = vector::zero;
        forAll(volumes, celli)
        {{
            const vector source = thrustOverRho*weights[celli]*volumes[celli]/weightedVolume*axis;
            // fvOptions matrix is on RHS; positive matrix source gives negative
            // physical force after equation assembly. Verify with the signed-load case.
            eqn.source()[celli] += source;
            integratedSource += source;
        }}
        reduce(integratedSource, sumOp<vector>());
        if (Pstream::master())
            Info << "PAPER_ROTOR " << mesh().time().value() << " " << diskSpeed
                 << " " << thrustOverRho*{config['rho_kg_m3']:.17g}
                 << " " << mag(integratedSource-thrustOverRho*axis)
                 << endl;
''' + '''
    #};
    codeCorrect #{ #};
    codeConstrain #{ #};
}
'''


def build_case(target, config, model, iterations, processes=1):
    if model not in ('kEpsilon', 'kOmegaSST'):
        raise ValueError('Unsupported reference turbulence model')
    if iterations < 1:
        raise ValueError('Positive iteration limit required')
    if not isinstance(processes, int) or not 1 <= processes <= 8:
        raise ValueError('Use between one and eight reference processes')
    scales = ('inlet_m_s', 'rotor_diameter_m', 'rotor_thickness_m', 'sigma_m', 'cutoff_sigma',
              'rho_kg_m3', 'cell_m', 'kinematic_viscosity_m2_s',
              'turbulence_intensity', 'turbulence_length_m')
    if any(not math.isfinite(config[k]) or config[k] <= 0 for k in scales):
        raise ValueError('Reference scales must be finite and positive')
    if not 0 < config['ct'] < 1 or not 0 <= config['inner_diameter_m'] < config['rotor_diameter_m']:
        raise ValueError('Invalid rotor parameters')
    if not math.isclose(config['rotor_thickness_m'], 2*config['sigma_m']*config['cutoff_sigma']):
        raise ValueError('Rotor thickness must equal the Gaussian support used by WeightedRotor')
    lengths = config['domain_xyz_m']; h = config['cell_m']
    if len(lengths) != 3 or len(config['hub_xyz_m']) != 3:
        raise ValueError('Expected three spatial dimensions')
    counts = [round(x/h) for x in lengths]
    if any(n <= 0 or not math.isclose(n*h, length) for n, length in zip(counts, lengths)):
        raise ValueError('Reference domain must divide into uniform cubic cells')
    target.mkdir(parents=True, exist_ok=False)
    def put(name, value):
        path = target/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    lx, ly, lz = lengths
    vertices = [(0,0,0),(lx,0,0),(lx,ly,0),(0,ly,0),(0,0,lz),(lx,0,lz),(lx,ly,lz),(0,ly,lz)]
    put('system/blockMeshDict', header('blockMeshDict')+f'''
scale 1;
vertices ({' '.join(vector(v) for v in vertices)});
blocks (hex (0 1 2 3 4 5 6 7) ({' '.join(map(str,counts))}) simpleGrading (1 1 1));
edges ();
boundary
(
 inlet {{ type patch; faces ((0 4 7 3)); }}
 outlet {{ type patch; faces ((1 2 6 5)); }}
 bottom {{ type wall; faces ((0 3 2 1)); }}
 top {{ type symmetryPlane; faces ((4 5 6 7)); }}
 side0 {{ type symmetryPlane; faces ((0 1 5 4)); }}
 side1 {{ type symmetryPlane; faces ((3 7 6 2)); }}
);
mergePatchPairs ();
''')
    symmetry = 'top {type symmetryPlane;} side0 {type symmetryPlane;} side1 {type symmetryPlane;}'
    def field(name, dimensions, initial, inlet, outlet, bottom, kind='volScalarField'):
        put('0/'+name, header(name,kind)+f'''
dimensions {dimensions};
internalField uniform {initial};
boundaryField {{ inlet {{{inlet}}} outlet {{{outlet}}} bottom {{{bottom}}} {symmetry} }}
''')
    U = config['inlet_m_s']; k = 1.5*(U*config['turbulence_intensity'])**2
    epsilon = .09**.75*k**1.5/config['turbulence_length_m']
    omega = math.sqrt(k)/(.09**.25*config['turbulence_length_m'])
    field('U', '[0 1 -1 0 0 0 0]', vector([U,0,0]), f'type fixedValue; value uniform ({U} 0 0);',
          f'type inletOutlet; inletValue uniform ({U} 0 0); value uniform ({U} 0 0);', 'type noSlip;', 'volVectorField')
    field('p', '[0 2 -2 0 0 0 0]', '0', 'type zeroGradient;', 'type fixedValue; value uniform 0;', 'type zeroGradient;')
    for name, val, dims, wall in [('k', k, '[0 2 -2 0 0 0 0]', 'kqRWallFunction'),
                                 ('epsilon', epsilon, '[0 2 -3 0 0 0 0]', 'epsilonWallFunction'),
                                 ('omega', omega, '[0 0 -1 0 0 0 0]', 'omegaWallFunction')]:
        field(name, dims, val, f'type fixedValue; value uniform {val};',
              f'type inletOutlet; inletValue uniform {val}; value uniform {val};',
              f'type {wall}; value uniform {val};')
    field('nut', '[0 2 -1 0 0 0 0]', '0', 'type calculated; value uniform 0;',
          'type calculated; value uniform 0;', 'type nutkWallFunction; value uniform 0;')
    put('constant/transportProperties', header('transportProperties')+f'transportModel Newtonian;\nnu [0 2 -1 0 0 0 0] {config["kinematic_viscosity_m2_s"]};\n')
    put('constant/turbulenceProperties', header('turbulenceProperties')+f'simulationType RAS;\nRAS {{ RASModel {model}; turbulence on; printCoeffs on; }}\n')
    put('constant/fvOptions', rotor_source(config))
    put('system/decomposeParDict', header('decomposeParDict')+f'numberOfSubdomains {processes};\nmethod scotch;\n')
    put('system/fvSchemes', header('fvSchemes')+'''
ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes {
 default none;
 div(phi,U) bounded Gauss linearUpwind grad(U);
 div(phi,k) bounded Gauss upwind;
 div(phi,epsilon) bounded Gauss upwind;
 div(phi,omega) bounded Gauss upwind;
 div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }
''')
    put('system/fvSolution', header('fvSolution')+'''
solvers {
 p { solver GAMG; tolerance 1e-8; relTol 0.05; smoother GaussSeidel; }
 "(U|k|epsilon|omega)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0.05; }
}
SIMPLE { nNonOrthogonalCorrectors 0; consistent yes;
 residualControl { p 1e-6; U 1e-6; "(k|epsilon|omega)" 1e-6; }
}
relaxationFactors { fields { p 0.3; } equations { U 0.5; k 0.5; epsilon 0.5; omega 0.5; } }
''')
    probes = []
    for distance in (1,3,5):
        hx, hy, hz = config['hub_xyz_m']; diameter = config['rotor_diameter_m']
        probes.append(f'wake{distance}D {{ type uniform; axis y; start {vector([hx+distance*diameter, hy-1.5*diameter, hz])}; end {vector([hx+distance*diameter,hy+1.5*diameter,hz])}; nPoints 121; }}')
    put('system/controlDict', header('controlDict')+f'''
application simpleFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime {iterations}; deltaT 1;
writeControl timeStep; writeInterval {iterations}; purgeWrite 0;
writeFormat ascii; writePrecision 12; writeCompression off;
timeFormat general; timePrecision 8; runTimeModifiable true;
functions {{
 profiles {{ type sets; libs ("libsampling.so"); writeControl writeTime;
   interpolationScheme cellPoint; setFormat raw; fields (U k nut);
   sets ({' '.join(probes)});
 }}
}}
''')
    write(target/'configuration.json', dict(config, turbulence_model=model, iterations=iterations, processes=processes,
           openfoam_image=IMAGE, grid_cells_xyz=counts,
           inlet_turbulence={'k': k, 'epsilon': epsilon, 'omega': omega},
           boundary_conditions={'inlet': 'fixed U', 'outlet': 'p=0; velocity inletOutlet',
                                'bottom': 'no-slip with wall functions', 'sides_and_top': 'symmetry/slip'},
           time_semantics='steady SIMPLE iteration, NOT physical seconds',
           reproduction_status='independent_reference_under_validation'))


def execute(target):
    """Run with the host user's UID, limited CPUs, and no access to other data."""
    config = json.loads((target/'configuration.json').read_text())
    processes = config['processes']
    solver = ('simpleFoam > log.simpleFoam 2>&1' if processes == 1 else
              f'decomposePar > log.decomposePar 2>&1 && mpirun --oversubscribe -np {processes} '
              'simpleFoam -parallel > log.simpleFoam 2>&1 && reconstructPar -latestTime > log.reconstructPar 2>&1')
    command = ['docker', 'run', '--rm', '--name', 'rotor-reference-'+target.name,
               '--user', f'{os.getuid()}:{os.getgid()}', '--cpus', str(processes), '--network', 'none',
               '-e', 'OMP_NUM_THREADS=1',
               '-e', 'HOME=/tmp/foam-home', '-v', f'{target.resolve()}:/case', '-w', '/case',
               '--entrypoint', '/bin/bash', IMAGE, '-lc',
               'mkdir -p /tmp/foam-home; source /usr/lib/openfoam/openfoam2312/etc/bashrc; '
               'blockMesh > log.blockMesh 2>&1 && checkMesh > log.checkMesh 2>&1 && '+solver]
    write(target/'status.json', {'state': 'running', 'command': command})
    completed = subprocess.run(command, check=False)
    write(target/'status.json', {'state': 'solver_finished' if completed.returncode == 0 else 'failed',
                                'returncode': completed.returncode,
                                'validated': False})
    if completed.returncode:
        raise RuntimeError(f'OpenFOAM failed; inspect {target}/log.simpleFoam')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=['kEpsilon','kOmegaSST'], default='kOmegaSST')
    parser.add_argument('--cell', type=float, default=.04)
    parser.add_argument('--iterations', type=int, default=1500)
    parser.add_argument('--processes', type=int, default=4)
    parser.add_argument('--intensity', type=float, default=.01)
    parser.add_argument('--length', type=float, default=.03)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    storage = Storage.load()
    config = json.loads((storage.metadata('actuator_lab')/'configs/paper_rotor_10ms.json').read_text())
    config.update(cell_m=args.cell, kinematic_viscosity_m2_s=1.5e-5,
                  turbulence_intensity=args.intensity, turbulence_length_m=args.length)
    config['assumptions'] = [
        'Uniform-grid independent reference: not yet a reproduction of the full wind tunnel geometry.',
        'Domain and hub position inherited from pilot; source geometry and original inlet turbulence require verification.',
        'Inlet intensity and length scale are explicit assumed values, not author data.',
        'Gaussian sigma and cutoff, full outer-disk thrust area with annular force support remain provisional.',
        'Official OpenFOAM 2312 RANS closures; no wave limiter is needed for this single-phase reference.',
        'No blades, nacelle, tower or electrical power; SIMPLE iterations are not physical time.'
    ]
    target = trial_root('actuator_lab', 'openfoam_rotor_reference')
    build_case(target, config, args.model, args.iterations, args.processes)
    revision = snapshot_sources(storage.root, target/'source_snapshot.tar.gz')
    write(target/'provenance.json', {'code_revision': revision, 'dirty': True,
                                    'source_snapshot_sha256': digest(target/'source_snapshot.tar.gz')})
    print(target, flush=True)
    if not args.prepare_only:
        execute(target)


if __name__ == '__main__':
    main()
