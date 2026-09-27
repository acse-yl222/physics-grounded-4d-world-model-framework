"""
run_sim.py = configure, run, and save simulation
"""

import sys
import os
import time
import argparse
import json
import numpy as np

# add project root to path so imports work from scripts/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sim.config import SimConfig
from sim.integrator import init_state, step
from sim.predator import init_predator, update_predator
from sim.environment import get_environment
from sim.environment import day_fraction

def main():
    # parse command-line overrides (if any)
    parser = argparse.ArgumentParser(description="Bird flock simulation")
    parser.add_argument('--n_birds', type=int, default=None)
    parser.add_argument('--n_steps', type=int, default=None)
    parser.add_argument('--dt', type=float, default=None)
    parser.add_argument('--wind_mode', type=str, default=None)
    parser.add_argument('--heading_noise', type=float, default=None)
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--output', type=str, default='data/runs/latest.npz')
    args = parser.parse_args()
    
    # create configuration
    config = SimConfig()
    
    # apply command-line overrides (if any)
    if args.n_birds is not None: config.n_birds = args.n_birds
    if args.n_steps is not None: config.n_steps = args.n_steps
    if args.dt is not None: config.dt = args.dt
    if args.wind_mode is not None: config.wind_mode = args.wind_mode
    if args.heading_noise is not None: config.heading_noise = args.heading_noise
    if args.seed is not None: config.seed = args.seed
    
    # print configuration
    total_time = config.n_steps * config.dt
    print("=" * 60)
    print("BIRD FLOCK SIMULATION")
    print("=" * 60)
    print(f"  Birds:     {config.n_birds}")
    print(f"  Timestep:  {config.dt}s")
    print(f"  Duration:  {config.n_steps} steps = {total_time:.0f}s = {total_time/60:.1f} min")
    print(f"  Wind:      {config.wind_mode} ({config.scaled_wind_speed} m/s)")
    print(f"  Noise:     {config.w_noise} N (random force)")
    print(f"  Neighbors: {config.k_neighbors} (topological)")
    print(f"  Seed:      {config.seed}")
    print(f"  Output:    {args.output}")
    print("=" * 60)
    
    # set seed
    np.random.seed(config.seed)

    # initialize state
    state = init_state(config)

    # initialize predator
    predator = init_predator(config) if config.enable_predator else None
    
    # storage for frames (positions, velocities, etc at each saved timestep)
    frames_pos = []
    frames_vel = []
    frames_bank = []
    frames_bstate = []
    frames_time = []
    frames_energy = []
    frames_valence = []
    frames_arousal = []
    frames_predator_pos = []
    frames_light = [] # daylight
    frames_food = [] # per-site food field snapshots for viewer heatmap
    
    # main simulation loop
    wall_start = time.time()

    # pollution exposure logging = accumulate bird-seconds of pollution exposure, split by state
    # useful for comparing runs (e.g. kinesis gain 0 vs 1.0)
    exposure_total = 0.0 # sum over birds & steps of pollution*dt (bird-seconds of pollution)
    exposure_murm = 0.0 # same, restricted to MURMURATION birds
    murm_bird_steps = 0 # count of (murmuration bird, step) samples, for a per-bird mean

    for t in range(config.n_steps):
        # update predator position
        if predator is not None:
            predator = update_predator(predator, state['time'], config)
        
        # advance birds one timestep
        state = step(state, config, predator=predator)

        # accumulate pollution exposure (pollution value * dt = bird-seconds of exposure)
        poll = get_environment(state['pos'], state['time'], config)['pollution'] # (N,)
        exposure_total += float(poll.sum()) * config.dt
        murm = state['bstate'] == 2 # MURMURATION
        if murm.any():
            exposure_murm += float(poll[murm].sum()) * config.dt
            murm_bird_steps += int(murm.sum())

        # save frame
        if t % config.save_every == 0:
            frames_pos.append(state['pos'].copy())
            frames_vel.append(state['vel'].copy())
            frames_bank.append(state['bank'].copy())
            frames_bstate.append(state['bstate'].copy())
            frames_time.append(state['time'])
            frames_energy.append(state['energy'].copy())
            frames_valence.append(state['valence'].copy())
            frames_arousal.append(state['arousal'].copy())
            if predator is not None:
                frames_predator_pos.append(predator['pos'].copy())
            else:
                frames_predator_pos.append(np.array([0, 0, -100])) # offscreen
            sky_light = float(day_fraction(state['time'], config))
            frames_light.append(sky_light)
            food_snap = [ff['grid'].copy() for ff in state.get('food_fields', [])] # food field snapshots (one grid per forage site per saved frame)
            if food_snap:
                frames_food.append(np.stack(food_snap)) # (n_sites, res, res)

        # print progress
        if t % config.metrics_every == 0:
            elapsed = time.time() - wall_start
            steps_per_sec = (t + 1) / max(elapsed, 0.001)
            eta = (config.n_steps - t) / max(steps_per_sec, 0.001)
            bs = state['bstate']
            counts = f"F={int((bs==0).sum())} T={int((bs==1).sum())} M={int((bs==2).sum())} D={int((bs==3).sum())} R={int((bs==4).sum())}"
            print(f"  t={state['time']:6.1f}s | {counts} | {steps_per_sec:.0f} steps/s ETA {eta:.0f}s")
    
    # save results
    wall_total = time.time() - wall_start
    print("=" * 60)
    print(f"Simulation complete. Wall time: {wall_total:.1f}s")
    # pollution exposure summary
    n = config.n_birds
    print("-" * 60)
    print(f"  Pollution exposure (bird-seconds):   total={exposure_total:.1f}")
    print(f"    per-bird avg over run:             {exposure_total / max(n, 1):.3f}")
    print(f"    MURMURATION only, total:           {exposure_murm:.1f}")
    if murm_bird_steps > 0:
        print(f"    MURMURATION mean pollution/bird:   {exposure_murm / (murm_bird_steps * config.dt):.4f}")
    print("-" * 60)
    print(f"Saving {len(frames_pos)} frames to {args.output}...")
    
    # ensure output directory exists
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    
    # save as compressed numpy archive
    np.savez_compressed(
        args.output,
        # frame data (one entry per saved timestep)
        pos=np.array(frames_pos), # (n_frames, N, 3)
        vel=np.array(frames_vel), # (n_frames, N, 3)
        bank=np.array(frames_bank), # (n_frames, N)
        bstate=np.array(frames_bstate), # (n_frames, N)
        frame_times=np.array(frames_time), # (n_frames,)
        energy=np.array(frames_energy), # (n_frames, N)
        valence=np.array(frames_valence), # (n_frames, N) affective valence -1 to +1
        arousal=np.array(frames_arousal), # (n_frames, N) affective arousal 0 to 1
        predator_pos=np.array(frames_predator_pos), # (n_frames, 3)
        sky_light=np.array(frames_light), # daylight
        food_grids=np.array(frames_food) if frames_food else np.array([]), # (n_frames, n_sites, res, res)
        world_layout=json.dumps(config.world), # world layout i.e. roosts, roads, point sources

        # per-bird identity (sampled once at init, drives viewer pattern channels)
        identity_valence_disposition=state['identity']['valence_disposition'],
        identity_arousal_excitability=state['identity']['arousal_excitability'],
        identity_energy_drain_rate=state['identity']['energy_drain_rate'],

        # config (for reproducibility)
        n_birds=config.n_birds,
        dt=config.dt,
        k_neighbors=config.k_neighbors,
        wind_mode=config.wind_mode,
        seed=config.seed,
        n_days=config.n_days,
        day_phase_start=config.day_phase_start,
        world=json.dumps(config.world),
    )
    
    print(f"Done. Export with: python3 scripts/export_web.py {args.output}")


if __name__ == '__main__':
    main()
