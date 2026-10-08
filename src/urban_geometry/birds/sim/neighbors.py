"""
neighbors.py = spatial queries for finding topological neighbors
"""

import numpy as np
from scipy.spatial import cKDTree


def find_topological_neighbors(positions, k):
    """
    Find the k closest neighbors for every bird.

    Args:
        positions: (N, 3) array, bird positions in 3D space (meters)
        k: int, number of neighbors to find

    Returns:
        indices: (N, k) array, indices of each bird's k closest neighbors
        distances: (N, k) array, distances to those closest neighbors
    """
    N = positions.shape[0]  # number of birds

    k_actual = min(
        k, N - 1
    )  # clamp k neighbor count to at most N-1 (i.e. max = total number of birds - 1)

    tree = cKDTree(positions)  # build the KD-tree from current positions

    distances, indices = tree.query(
        positions, k=k_actual + 1
    )  # return k+1 closest points (including self) in ascending order

    # handle single-bird case, since scipy returns 1D when N=1
    if positions.shape[0] == 1:
        distances = distances.reshape(1, -1)
        indices = indices.reshape(1, -1)

    # strip the self-reference (first column) so now indices[:, 0] is the closest non-self bird
    neighbor_indices = indices[:, 1:]  # shape (N, k)
    neighbor_distances = distances[:, 1:]  # shape (N, k)

    return neighbor_indices, neighbor_distances


def find_metric_neighbors(positions, radius):
    """
    Find all neighbors within a fixed radius for every bird.

    Args:
        positions: (N, 3) array, bird positions in 3D space (meters)
        radius: float, interaction radius in meters

    Returns:
        neighbor_lists: list of N arrays, each containing the indices of the neighbors within the radius
    """
    tree = cKDTree(positions)

    neighbor_lists = tree.query_ball_point(
        positions, radius
    )  # query_ball_point returns a list (birds) of lists (that bird's neighbors). Variable length per bird

    # remove self from each list
    for i in range(len(neighbor_lists)):
        neighbor_lists[i] = [j for j in neighbor_lists[i] if j != i]

    return neighbor_lists


def compute_blind_angle_mask(positions, velocities, neighbor_indices, blind_angle):
    """
    Compute visibility mask excluding neighbors in the rear blind cone.
    - StarDisplay applies a blind angle for cohesion and alignment (but NOT separation)

    Args:
        positions: (N, 3) array, bird positions in 3D space (meters)
        velocities: (N, 3) array, bird velocities (used to extract headings)
        neighbor_indices: (N, k) array, indices of each bird's k closest neighbors
        blind_angle: float, total angular width of blind cone behind bird (radians)

    Returns:
        mask: (N, k) array, booleans where True = neighbor is visible
    """
    # bird headings
    speeds = np.linalg.norm(velocities, axis=-1, keepdims=True)
    headings = velocities / np.maximum(speeds, 1e-6)  # (N, 3)

    # direction toward each neighbor
    neighbor_pos = positions[neighbor_indices]  # (N, k, 3)
    toward = neighbor_pos - positions[:, np.newaxis, :]  # (N, k, 3)
    toward_dist = np.linalg.norm(toward, axis=-1, keepdims=True)
    toward_unit = toward / np.maximum(toward_dist, 1e-6)  # (N, k, 3)

    # cos(angle) between heading and direction to neighbor
    cos_angle = np.sum(headings[:, np.newaxis, :] * toward_unit, axis=-1)  # (N, k)

    # visible if angle from forward < (π - blind_angle/2)
    cos_threshold = -np.cos(blind_angle / 2.0)
    mask = cos_angle > cos_threshold  # (N, k)

    return mask
