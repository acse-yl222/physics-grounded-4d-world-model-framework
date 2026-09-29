/** Recorded sampling coordinates; world z becomes viewer y, world y becomes -z. */
export function movieLayout(meta, groundLength) {
  const [ny, nx] = meta.display_shape ?? [];
  const spacing = meta.display_cell_m;
  const offset = meta.display_first_center_offset_m;
  const origin = meta.origin_xyz_m;
  // Legacy exports omitted this field and explicitly recorded an 80 m AGL slice.
  const height = meta.slice_agl_m ?? 80;
  if (![ny, nx].every(n => Number.isInteger(n) && n >= 2) || groundLength !== ny * nx)
    throw Error('Wind display shape does not match terrain samples');
  if (!Number.isFinite(spacing) || spacing <= 0 || !Number.isFinite(offset) || !Number.isFinite(height)
      || !Array.isArray(origin) || origin.length !== 3 || !origin.every(Number.isFinite))
    throw Error('Invalid wind sampling coordinates');
  return {ny, nx, spacing, height, position(i, j, ground) {
    return [origin[0] + offset + i * spacing, ground + height, -(origin[1] + offset + j * spacing)];
  }};
}
