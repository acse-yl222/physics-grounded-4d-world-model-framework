"""
config.py = all simulation params (in SI units)
"""

from common.layout import scene_input

from dataclasses import dataclass, field
import numpy as np

# INDIVIDUAL TRAITS = spec for per-bird trait sampling i.e. creates individuals rather than clones
# NOTE: currently avoiding traits that were tuned based on STARFLAG metrics to preserve behavior
# each trait is the individual disposition along one internal-state axis:
#   energy_drain_rate = how fast this bird tires
#   sensitivity = disposition i.e. optimistic (>1) feels bad stimuli less AND recovers faster / pessimistic (<1) feels bad stimuli more AND recovers slower
#   excitability = jumpiness i.e. how much arousal spikes at anything
INDIVIDUAL_TRAITS = {  # name: (spread_as_fraction_of_mean, clip_min, clip_max)
    "energy_drain_rate": (0.15, 0.001, 0.05),
    "valence_disposition": (0.20, 0.4, 1.6),
    "arousal_excitability": (0.20, 0.3, 2.0),
}

# AFFECTIVE STATE = per-bird valence/arousal
# valence = quality (signed, -1 bad, +1 good)
# arousal = activation level (unsigned, 0 calm, 1 activated)
# each influence contributes an additive (d_valence, d_arousal) to the target, and the smoothed state relaxes toward that target with a time constant (tau)
# valence takes the sign of an influence (good/bad), arousal takes its magnitude

# per-influence gains = how strongly each source pushes valence / arousal
# (dv, da) pairs w/ dv signed, da unsigned TODO: tune
AFFECT_GAINS = {
    # influence: (d_valence_gain, d_arousal_gain)
    "predator": (-1.0, 1.0),  # predator threat = very bad, very activating
    "pollution": (-0.6, 0.3),  # bad air = negative, mildly activating
    "noise": (-0.4, 0.3),  # noise = a bit negative, mildly activating
    "low_energy": (-0.5, 0.0),  # energy depletion = negative valence, not arousing
    "maneuvering": (0.0, 0.6),  # hard steering = activating, sign-neutral
    "flock_turbulence": (0.0, 0.5),  # being jostled = activating
    "calm_baseline": (0.15, 0.0),  # mild positive pull when nothing is wrong
}

# affect -> Oklab mapping ( a=green/red, b=blue/yellow)
# tuple is (value_at_extreme_low, value_at_extreme_high)
VALENCE_A_RANGE = (
    0.13,
    -0.05,
)  # valence -1 (bad) = +0.13 a (red); +1 (good) = -0.05 a (green)
AROUSAL_B_RANGE = (
    -0.09,
    0.09,
)  # arousal 0 (calm) = -0.09 b (blue); 1 (aroused) = +0.09 b (yellow)
AFFECT_L_RANGE = (0.45, 0.73)  # base body lightness from energy (low energy = darker)

# BEHAVIORAL STATES = what "mode" each bird is in
# state-dependent weights = control the relative importance of each force from forces.py
# each row has [w_separation, w_alignment, w_cohesion, w_roost, target_speed]
STATE_PARAMS = np.array(
    [
        # sep   ali    coh    roost   speed
        [0.5, 0.5, 0.5, 0.0, 8.0],  # 0: FORAGE TODO: implement foraging
        [0.622, 1.762, 0.367, 1.0, 14.0],  # 1: TRANSIT
        [
            0.7937,
            0.9999,
            0.2341,
            0.4980,
            12.9766,
        ],  # 2: MURMURATION (optimized on STARFLAG metrics)
        [
            0.3,
            0.3,
            0.5,
            4.0,
            4.0,
        ],  # 3: DESCENT = slow, strong roost pull, still flocking
        [0.0, 0.0, 0.0, 0.0, 0.0],  # 4: ROOST = stationary, all forces zero
    ],
    dtype=np.float64,
)


# per-state gain on the wind response (anemotaxis)
# indexed like STATE_PARAMS by behavioral state
# full in TRANSIT, low in MURMURATION so wind-driven speed/heading changes don't break the STARFLAG metrics, and zero once landed
WIND_RESPONSE_GAIN = np.array(
    [
        0.0,  # 0 FORAGE
        0.0,  # 1 TRANSIT = wave routing (with wind) renders this obsolete
        0.0,  # 2 MURMURATION
        0.0,  # 3 DESCENT
        0.0,  # 4 ROOST = on the ground, no wind response
    ],
    dtype=np.float64,
)

# per-state gain on wave-routing guidance
# primary navigator in TRANSIT
WAVE_GUIDANCE_GAIN = np.array(
    [
        0.0,  # 0 FORAGE
        1.0,  # 1 TRANSIT = primary long-range navigator
        0.0,  # 2 MURMURATION
        0.3,  # 3 DESCENT
        0.0,  # 4 ROOST
    ],
    dtype=np.float64,
)

# FIELD_RESPONSES = Berdahl kinesis (speed modulation), per scalar field
#   'sign': +1 aversive (speed up where the field is high to leave bad regions fast)
#           -1 appetitive (slow down where high, to linger)
#   'gain': fraction of base target speed the field adds/removes at full (normalized) intensity
FIELD_RESPONSES = {  # TODO: tweak
    "pollution": {"sign": +1.0, "gain": 0.5},
    "noise": {"sign": +1.0, "gain": 0.5},
}

# per-state gain on the field speed modulation
# full in TRANSIT, low in MURMURATION (speed spread threatens H2010 dynamics), 0 when landed
FIELD_RESPONSE_GAIN = np.array(
    [
        0.0,  # 0 FORAGE
        0.0,  # 1 TRANSIT
        1.0,  # 2 MURMURATION
        0.6,  # 3 DESCENT
        0.0,  # 4 ROOST
    ],
    dtype=np.float64,
)

# to test effects w/ or w/o
# WIND_RESPONSE_GAIN[:] = 0
# FIELD_RESPONSE_GAIN[:] = 0


@dataclass
class SimConfig:
    """
    Default parameters based on starlings.

    Override when constructing e.g. SimConfig(n_birds=2000, dt=0.02)
    """

    # WORLD LAYOUT
    # all spatial features e.g. roosts, roads, point sources of pollution/noise
    geometry_path: str = None  # path to separate geometry .npz from glb_to_geo.py; None = use geometry from scaled_wind_path
    geometry_path: str = field(
        default_factory=lambda: str(scene_input("south_ken", "birds", "geometry.npz"))
    )
    world: dict = None

    # WORLD GENERATION = auto-placement of roosts/forage sites based on voxel geometry
    world_generation: str = "naive"  # "off" = use config.world provided below only, "naive" = auto-generate (replaces manual), "supplement" = keep manual AND fill quota
    world_gen_n_roosts: int = 1  # target number of roosts for auto-generation
    world_gen_n_forage: int = 3  # target number of forage sites for auto-generation
    world_gen_min_roost_area: float = 200.0  # m^2, initial minimum rooftop area to qualify as a roost (relaxed progressively if not enough found)
    world_gen_min_forage_area: float = 400.0  # m^2, initial minimum open-ground area for forage (relaxed progressively if not enough found)

    def __post_init__(self):
        if self.world is None:
            self.world = {
                "roosts": [
                    {
                        # 'center': [0.0, 43.0, 1.1], # center of roost surface
                        # 'center': [-34.5, 29.5, 13.5], # center of roost surface
                        "center": [
                            133,
                            -88,
                            50,
                        ],  # center of roost surface (height doesn't matter because it will be draped)
                        # 'center': [110, 15, 22], # on roof
                        "size": [20.0, 20.0],  # [length, width] in meters
                        "forward": [1.0, 0.0, 0.0],  # direction of length axis
                        "normal": [0.0, 0.0, 1.0],  # surface normal
                        "quality": 1.0,
                    },
                ],
                "roads": [
                    # {'y': 50.0, 'pollution_decay': 20.0, 'noise_decay': 35.0},
                ],
                "point_sources": [
                    {
                        "pos": [128, -354, 40],
                        "type": "pollution",
                        "strength": 1.0,
                        "decay": 40.0,
                    },
                    # {'pos': [132, -61, 8], 'type': 'pollution', 'strength': 1.0, 'decay': 40.0},
                    # {'pos': [134, -86, 30], 'type': 'pollution', 'strength': 1.0, 'decay': 40.0},
                ],
                "forage_sites": [  # foraging sites
                    {
                        "center": [242, -320, 15],
                        "size": [75.0, 75.0],
                        "forward": [1.0, 0.0, 0.0],
                        "normal": [0.0, 0.0, 1.0],
                        "quality": 1.0,
                    },
                    {
                        "center": [155, 147, 7],
                        "size": [50.0, 50.0],
                        "forward": [1.0, 0.0, 0.0],
                        "normal": [0.0, 0.0, 1.0],
                        "quality": 0.7,
                    },
                    {
                        "center": [-317, 34, 42],
                        "size": [30.0, 30.0],
                        "forward": [1.0, 0.0, 0.0],
                        "normal": [0.0, 0.0, 1.0],
                        "quality": 0.5,
                    },
                ],
            }

    floor_z: float = 0.0  # domain ground plane (m): birds cannot descend below this anywhere outside the geometry

    # SIMULATION SETUP
    n_birds: int = 500  # number of birds
    dt: float = 0.05  # timestep (s) e.g. 0.05 = 20fps
    n_steps: int = 4000  # total timesteps
    seed: int = 42  # RNG seed for reproducibility
    enable_individuality: bool = True  # sample per-bird traits from INDIVIDUAL_TRAITS distributions
    valence_disposition: float = 1.0  # affective disposition (per-bird sampled; >1 optimistic feels less negative + recovers faster, <1 pessimistic)
    arousal_excitability: float = 1.0  # mean arousal-response multiplier (per-bird sampled)
    start_state: int = 1  # 2 = MURMURATION, 1 = TRANSIT, etc

    # DAY CYCLE CLOCK
    n_days: float = 1.75  # how many days fit into the duration of the run i.e. day_length = (n_steps * dt) / n_days
    day_phase_start: float = (
        0.25  # where in the day the sim starts: 0=midnight, 0.25=dawn, 0.5=noon, 0.75=dusk
    )

    # TOPOLOGICAL INTERACTIONS
    k_neighbors: int = 7  # number of topological neighbors
    r_hard_sphere: float = 0.2  # the distance at which birds would collide (half wingspan)
    r_separation: float = (
        3.5933  # outer boundary of avoidance zone (outside of which no separation force)
    )
    separation_gaussian_floor: float = (
        0.0054  # separation force strength at r_separation boundary, as fraction of max
    )
    blind_angle: float = 1.3617  # cone behind the bird where it cannot see
    separation_mode: str = "multi"  # 'single' (H2015) or 'multi' (H2010) neighbor separation

    # FLIGHT PHYSICS
    mass: float = 0.08  # bird mass in kg
    cl_cd_ratio: float = 3.3  # lift-to-drag coefficient ratio coeff_lift/coeff_drag
    cruise_speed: float = 8.2095  # v0, speed at which lift = weight and thrust = drag (m/s)
    gravity: float = 9.81  # gravitational acceleration (m/s^2)
    max_load_factor: float = 3.0  # maximum lift bird is allowed to generate lift as a multiple of weight (n = L/mg) TODO: empirical value
    speed_relaxation: float = 0.8619  # tau, relaxation time in seconds = how quickly bird returns to its target speed after deviating
    physics_sub_steps: int = 10  # reaction time... birds re-assess surroundings once per dt, but physics integrated 10 times per dt TODO: is it better to keep this as absolute or relative to dt?
    w_noise: float = 0.0049  # random force magnitude in Newtons

    # FLIGHT CONSTRAINTS
    max_turn_rate: float = 4.0  # maximum heading change rate (rad/s)
    max_bank_angle: float = 1.2  # maximum roll angle (rad)
    v_min: float = 2.0  # minimum airspeed during flight (m/s)
    v_min_descent: float = 2.0  # minimum airspeed during landing flare (m/s)
    v_min_sustained: float = (
        6.0  # minimum sustained airspeed (m/s), floor for kinesis target-setting
    )
    v_max: float = 18.0  # maximum airspeed (m/s)
    max_climb_angle: float = 1.047  # maximum flight pitch form horizontal (rad) ~= 60deg TODO: make it empirically grounded

    # BANKING DYNAMICS
    w_bank_in: float = 6.7119  # roll-in weight (into turn)
    w_bank_out: float = 1.0291  # roll-out weight (recovery to level)

    # WIND RESPONSE (anemotaxis) tuning TODO: tune, or empirical
    tau_wind: float = 0.8  # timescale (s) over which a bird nulls the wind it feels; compensation strength ~= mass/tau_wind
    k_wind_bail: float = (
        0.5  # max cross-wind steering force (N) when a headwind saturates the bird's airspeed
    )

    # WAVE ROUTING = first-arrival-time navigation around buildings toward the roost
    enable_wave_routing: bool = True
    w_wave_guidance: float = 1.5  # steering weight for following -grad T home TODO: tune vs w_roost

    route_use_wind: bool = (
        True  # fold local wind magnitude into routing cost (route around strong wind)
    )
    route_wind_static: bool = True  # solve wind cost once at startup (do not update each wind frame), the bird's knowledge is an imperfect familiarity i.e. habitual route rather than live-updating clairvoyance

    route_use_pollution: bool = True  # fold pollution into routing cost (prefer cleaner ways home)
    route_pollution_cost: float = (
        2.0  # strength of the pollution route penalty (0 = ignore) TODO: tune
    )

    route_use_noise: bool = True  # fold noise into routing cost (prefer quieter ways home)
    route_noise_cost: float = 0.5  # strength of the noise route penalty (0 = ignore) TODO: tune

    # ROOST
    murmuration_entry_radius: float = (
        20.0  # distance from roost (m) where birds switch to murmurating
    )
    roost_descent_time_frac: float = (
        0.75  # fraction of total sim time after which birds begin roosting (fallback)
    )

    w_roost_vertical: float = 0.3367  # vertical spring force weight
    roost_vertical_damping: float = 0.0097  # damping coefficient for vertical oscillation
    roost_flight_offset: float = 20.0  # meters above roost that murmuration birds orbit at
    descent_vertical_multiplier: float = 1.0  # vertical spring multiplier during descent
    descent_slowdown_height: float = 20.0  # meters above surface where descent deceleration begins
    descent_flare_drag: float = (
        10.0  # drag multiplier at surface (1.0 = no extra drag, more = more braking)
    )
    roost_land_tolerance: float = 0.1  # meters from surface at which a descending bird lands
    roost_tanh_halfdist: float = (
        50.0  # distance (m) at which horizontal roost pull reaches half strength
    )
    roost_altitude_band: float = 4.4946  # meters of vertical freedom before altitude spring engages

    # INITIAL CONDITIONS
    # spawn_point: tuple = (-445.0, -60.0, 5.0) # absolute (x, y, z) center of the spawn cluster
    spawn_point: tuple = (
        128.0,
        -487.0,
        27.0,
    )  # absolute (x, y, z) center of the spawn cluster
    init_flock_radius: float = 8.0  # cluster tightness (m), small = organized start
    min_start_alt: float = 2.0  # override the "above tallest building" spawn floor; None = keep it, 2.0 = 2.0 is now the min starting altitude

    # WIND
    wind_mode: str = "none"  # wind model to use TODO: switch permanently to SCALED?
    wind_strength: float = (
        3.0  # base wind speed (m/s) for simple wind models TODO: remove this and just use scaled
    )
    wind_direction: tuple = (
        1.0,
        0.0,
        0.0,
    )  # wind direction (unit vector) TODO: remove this and just use scaled

    # SCALED wind field (precomputed)
    scaled_wind_path: str = field(
        default_factory=lambda: str(scene_input("south_ken", "birds", "geometry.npz"))
    )
    # scaled_wind_path: str = "data/wind_field_SK.npz" # path to .npz from generate_wind.py
    embed_detailed_model: bool = (
        False  # embed the detailed GLB in the viewer (large HTML), false = voxel boxes only
    )
    detailed_model_path: str = (
        "vis/southken_detailed.glb"  # GLB embedded when embed_detailed_model is True
    )
    scaled_wind_speed: float = 5.0  # scaling to convert non-dimensional velocities in SCALED to m/s TODO: confirm correct scaling
    scaled_grid_origin: tuple = (
        -512,
        -512,
        0,
    )  # (x, y, z) position of grid cell (0,0,0) in simulation coords (meters)
    scaled_dt: float = 24.0  # seconds per SCALED timestep TODO: confirm correct scaling

    # OBSTACLE AVOIDANCE
    w_building_avoidance: float = 8.0  # force weight in Newtons TODO: rename
    building_detection_dist: float = 8.0  # how far birds sense buildings (m) TODO: is there an empirical value for this, also rename

    # ENVIRONMENT
    enable_environment: bool = True  # toggle environmental perception
    enable_predator: bool = False  # toggle predator agent
    w_pollution_avoidance: float = 1.5  # how strongly birds avoid polluted areas
    w_noise_avoidance: float = 0.0235  # how strongly birds avoid noisy areas

    # BIRD INTERNAL ENERGY
    energy_drain_rate: float = 0.01  # energy lost per timestep during flight
    energy_drain_speed_exponent: float = 3.0  # energy cost proportional to (airspeed / v_max)^3.0

    # AFFECTIVE STATES
    # relaxation time constants (seconds) = how fast the mood chases its target
    # arousal is faster (spikes then settles), valence slower (a lingering mood) TODO: empirical, tweak
    tau_valence: float = 4.0
    tau_arousal: float = 1.5

    # LIGHT
    roost_light_threshold: float = 0.1  # light level below which roosting can begin

    # TEMPERATURE PARAMETERS
    cold_cohesion_boost: float = 0.5  # extra cohesion when temp < cold_threshold
    cold_threshold: float = 8.0  # temperature (°C) below which cohesion boost activates

    # PREDATOR PARAMETERS
    predator_detection_radius: float = 80.0  # how far birds can see the predator (m)
    w_predator_avoidance: float = (
        5.0  # predator evasion weight (high = top priority after separation)
    )

    # STATE TRANSITION TUNING (murmuration)
    energy_roost_threshold: float = (
        0.3  # bird wants to roost sooner if energy falls below this value
    )
    energy_roost_sensitivity: float = 0.5  # how strongly low energy raises roost threshold
    energy_roost_max_boost: float = 0.15  # max threshold boost from low energy
    stress_roost_sensitivity: float = 0.1  # how strongly high stress raises roost threshold
    stress_roost_max_boost: float = 0.1  # max threshold boost from stress
    cold_roost_sensitivity: float = 0.02  # how strongly cold raises roost threshold
    cold_roost_max_boost: float = 0.1  # max threshold boost from cold
    roost_max_chance_per_step: float = 0.1  # maximum probability of roosting per timestep
    roost_chance_ramp: float = 0.1  # how quickly roost probability grows with increased darkness (birds in deeper darkness roost faster)
    lock_state: int = (
        -1
    )  # if >= 0, update_states is a no-op and all birds stay in this state (optimization safety)

    # DAWN DEPARTURE (to foraging, from roost)
    dawn_light_threshold: float = (
        0.1  # light level at which the first (earliest) wave leaves the roost
    )
    n_dawn_waves: int = 5  # number of discrete departure waves
    wave_light_step: float = 0.05  # extra light needed per successive wave (later waves leave when it's brighter i.e. later)
    wave_energy_bias: float = (
        0.3  # 0-1 = how strongly energy biases wave order (higher energy leaves earlier)
    )

    # DUSK RETURN (to roost, from foraging)
    # departure is light-triggered, birds farther from roost leave earlier to budget travel time
    # well-fed birds depart sooner (can afford the commute, so don't need to keep feeding)
    dusk_light_threshold: float = (
        0.55  # base light level below which foraging birds begin returning
    )
    dusk_distance_scale: float = (
        200.0  # reference distance (m), a bird this far gets full distance boost
    )
    dusk_distance_boost: float = (
        0.15  # threshold added for birds at reference distance (farther = leave earlier)
    )
    dusk_energy_bias: float = 0.1  # threshold added for a fully fed bird (well-fed = leave earlier)
    dusk_departure_noise: float = (
        0.08  # per-bird noise on threshold for natural straggle (reuses wave_rand)
    )

    # FORAGE = arrival, ground feeding  TODO: tune
    forage_arrival_frac: float = (
        0.6  # outbound bird starts DESCENT when within this fraction of its site's half size
    )
    forage_land_tolerance: float = (
        0.2  # height above ground (m) at which a descending forage bird lands
    )

    # AREA-RESTRICTED SEARCH
    ars_dwell_time: float = (
        0.5  # base seconds a bird dwells/probes between hops (randomly scaled by 0.5-1.5x)
    )
    ars_hop_extensive: float = 0.6  # hop distance (m) in extensive mode (longer, covers ground)
    ars_hop_intensive: float = (
        0.15  # hop distance (m) in intensive mode (short, stays on the patch)
    )
    ars_hop_duration: float = (
        0.3  # seconds one hop takes (a real ballistic arc over multiple steps)
    )
    ars_hop_height: float = 0.12  # peak height (m) of the hop arc
    ars_turn_extensive: float = (
        0.3  # hop-turn sigma (rad) extensive (~17 deg, hops nearly straight ahead)
    )
    ars_turn_intensive: float = 1.5  # hop-turn sigma = std (rad), large = very variable directions and turns a lot when hopping, 0 means always go straight
    ars_giveup_hops: int = 6  # foodless hops in a row before switching intensive -> extensive
    ars_food_threshold: float = 0.1  # minimum food density for a hop to count as a "find"
    ars_enhancement: float = 0.4  # when extensive bird searching for new patch, it is influenced this percent toward a group of birds actually feeding
    ars_energy_intake: float = (
        0.004  # energy gained per step while feeding (scaled by local food density)
    )
    ars_depletion_per_probe: float = 0.02  # food removed at the bird's cell per probe
    ars_food_recovery: float = (
        0.005  # food regrown per grid cell per second (slow, so patches stay transient)
    )

    # spatial food field (per-site 2D grid)
    food_field_resolution: int = 32  # grid cells per axis per forage site (32x32 = 1024 cells)
    food_patch_density: float = (
        0.005  # Gaussian food blobs per m^2 of site (count scales with area)
    )
    food_patch_sigma_m: float = 5  # absolute blob radius in meters

    # OUTPUTS
    save_every: int = 1  # save a frame every N timesteps
    metrics_every: int = 20  # compute and print metrics every N timesteps
