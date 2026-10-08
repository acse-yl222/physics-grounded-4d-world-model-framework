"""State-carrying temperature solver extracted from the preserved diurnal implementation.

The model argument supplies the original shift and boundary-condition functions.
"""
import math
import numpy as np
import torch

def solve_from_state(model, fields, boundary_fields, velocity_config, temp3d_config, initial_temperature_c):
    """Copy of model.solve_temperature_fields_3d_torch with an initial temperature field (only change marked ###)."""
    device = torch.device(temp3d_config.temperature_solver_device)
    u_frames_np = (temp3d_config.velocity_scale * fields['u']).astype(np.float32)
    v_frames_np = (temp3d_config.velocity_scale * fields['v']).astype(np.float32)
    w_frames_np = (temp3d_config.velocity_scale * fields['w']).astype(np.float32)
    solid_mask_np = fields['solid_mask_3d'].astype(bool)
    study_area_3d_np = np.broadcast_to(fields['study_area_mask_2d'][None, :, :], solid_mask_np.shape).astype(bool)
    fluid_mask_np = (~solid_mask_np) & study_area_3d_np
    dx = float(velocity_config.model_resolution_m); dy = dx; dz = float(velocity_config.height_scale_m)
    max_speed = float(np.max(np.sqrt(u_frames_np ** 2 + v_frames_np ** 2 + w_frames_np ** 2)))
    stable_dt = temp3d_config.max_courant * min(dx, dy, dz) / max(max_speed, 1e-6)
    diffusion_dt = 0.18 * min(dx, dy, dz) ** 2 / max(temp3d_config.diffusion_coeff_m2_s, 1e-6)
    dt = min(stable_dt, diffusion_dt, temp3d_config.frame_duration_s)
    substeps = max(1, int(math.ceil(temp3d_config.frame_duration_s / max(dt, 1e-6)))); dt = temp3d_config.frame_duration_s / substeps
    u_frames = torch.as_tensor(u_frames_np, device=device); v_frames = torch.as_tensor(v_frames_np, device=device); w_frames = torch.as_tensor(w_frames_np, device=device)
    solid_mask = torch.as_tensor(solid_mask_np, device=device); roof_mask = torch.as_tensor(fields['roof_mask_3d'].astype(bool), device=device)
    study_area_3d = torch.as_tensor(study_area_3d_np, device=device); fluid_mask = (~solid_mask) & study_area_3d; bottom_fluid = fluid_mask[0]
    bottom_exchange_coeff = torch.as_tensor(boundary_fields['surface_exchange_coeff_per_s'].astype(np.float32), device=device)
    ground_surface_temperature_excess_c = torch.as_tensor(boundary_fields['ground_surface_temperature_excess_c'].astype(np.float32), device=device)
    roof_surface_temperature_excess_3d = torch.as_tensor(boundary_fields['roof_surface_temperature_excess_3d'].astype(np.float32), device=device)
    ambient_temp_series_c = boundary_fields['ambient_temp_series_c'].astype(np.float32); inflow_temp_series_c = boundary_fields['inflow_temp_series_c'].astype(np.float32)
    surface_forcing_layer_count = int(boundary_fields['surface_forcing_layer_count'][0])
    temperature_c = torch.as_tensor(np.ascontiguousarray(initial_temperature_c, dtype=np.float32), device=device).clone()   ### initial state instead of uniform ambient
    model.impose_boundary_conditions_3d_torch(temperature_c, solid_mask, roof_mask, study_area_3d, roof_surface_temperature_excess_3d,
                                           current_ambient_temp_c=float(ambient_temp_series_c[0]), current_inflow_temp_c=float(inflow_temp_series_c[0]))
    frame_means = [float(temperature_c[fluid_mask].mean())]
    diffusion_coeff = float(temp3d_config.diffusion_coeff_m2_s); zero = torch.zeros((), device=device)
    with torch.no_grad():
        for frame_idx in range(u_frames.shape[0]):
            u = torch.where(fluid_mask, u_frames[frame_idx], zero); v = torch.where(fluid_mask, v_frames[frame_idx], zero); w = torch.where(fluid_mask, w_frames[frame_idx], zero)
            current_ambient_temp_c = float(ambient_temp_series_c[min(frame_idx + 1, len(ambient_temp_series_c) - 1)])
            current_inflow_temp_c = float(inflow_temp_series_c[min(frame_idx + 1, len(inflow_temp_series_c) - 1)])
            current_ground_surface_temperature_c = current_ambient_temp_c + ground_surface_temperature_excess_c
            for _ in range(substeps):
                sh = model.shift_with_edge_torch
                left = sh(temperature_c, 2, 1); right = sh(temperature_c, 2, -1); north = sh(temperature_c, 1, 1); south = sh(temperature_c, 1, -1)
                below = sh(temperature_c, 0, 1); above = sh(temperature_c, 0, -1); below[0] = temperature_c[0]
                # Optional impermeable upwind interfaces for geometry-derived frozen winds.
                # Coarse interpolation can otherwise transport hot solid-cell values into air.
                if getattr(temp3d_config, 'block_solid_advection', False):
                    left = torch.where(sh(solid_mask, 2, 1), temperature_c, left)
                    right = torch.where(sh(solid_mask, 2, -1), temperature_c, right)
                    north = torch.where(sh(solid_mask, 1, 1), temperature_c, north)
                    south = torch.where(sh(solid_mask, 1, -1), temperature_c, south)
                    below_adv = torch.where(sh(solid_mask, 0, 1), temperature_c, below)
                    above_adv = torch.where(sh(solid_mask, 0, -1), temperature_c, above)
                else:
                    below_adv, above_adv = below, above
                adv_x = torch.where(u >= 0, u * (temperature_c - left) / dx, u * (right - temperature_c) / dx)
                adv_y = torch.where(v >= 0, v * (temperature_c - north) / dy, v * (south - temperature_c) / dy)
                adv_z = torch.where(w >= 0, w * (temperature_c - below_adv) / dz, w * (above_adv - temperature_c) / dz)
                # Restore physical solid temperatures for conductive heat exchange.
                left = sh(temperature_c, 2, 1); right = sh(temperature_c, 2, -1); north = sh(temperature_c, 1, 1); south = sh(temperature_c, 1, -1)
                laplacian = (left - 2 * temperature_c + right) / dx ** 2 + (north - 2 * temperature_c + south) / dy ** 2 + (below - 2 * temperature_c + above) / dz ** 2
                surface_exchange_term = torch.zeros_like(temperature_c)
                for layer_idx in range(surface_forcing_layer_count):
                    layer_fluid = fluid_mask[layer_idx] & bottom_fluid
                    surface_exchange_term[layer_idx, layer_fluid] = bottom_exchange_coeff[layer_fluid] * (current_ground_surface_temperature_c[layer_fluid] - temperature_c[layer_idx, layer_fluid])
                nxt = temperature_c + dt * (-(adv_x + adv_y + adv_z) + diffusion_coeff * laplacian + surface_exchange_term)
                temperature_c[fluid_mask] = nxt[fluid_mask]
                model.impose_boundary_conditions_3d_torch(temperature_c, solid_mask, roof_mask, study_area_3d, roof_surface_temperature_excess_3d,
                                                       current_ambient_temp_c=current_ambient_temp_c, current_inflow_temp_c=current_inflow_temp_c)
            frame_means.append(float(temperature_c[fluid_mask].mean()))
    return temperature_c.cpu().numpy(), fluid_mask_np, {'dt_seconds': dt, 'substeps_per_frame': substeps, 'frame_means_c': frame_means}
