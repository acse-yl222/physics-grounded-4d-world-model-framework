from __future__ import annotations

import argparse


def shard_ranges(start: int, stop: int, shards: int) -> list[tuple[int, int]]:
    """Split a half-open timestep range into near-equal contiguous shards."""

    total = stop - start
    if start < 0 or total < shards or shards < 1:
        raise ValueError("range must contain at least one timestep per shard")
    size, extra = divmod(total, shards)
    ranges = []
    current = start
    for index in range(shards):
        count = size + (index < extra)
        ranges.append((current, count))
        current += count
    return ranges


def main() -> None:
    """Print the start and count assigned to one requested shard index."""

    parser = argparse.ArgumentParser(description="Print one contiguous latent shard range.")
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--stop", type=int, required=True)
    parser.add_argument("--shards", type=int, required=True)
    parser.add_argument("--index", type=int, required=True)
    args = parser.parse_args()
    ranges = shard_ranges(args.start, args.stop, args.shards)
    if args.index < 0 or args.index >= len(ranges):
        raise ValueError("shard index is out of range")
    print(*ranges[args.index])


if __name__ == "__main__":
    main()
