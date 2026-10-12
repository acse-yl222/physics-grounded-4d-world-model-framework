"""Validate selected lossless city publication bundles and original byte identities."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

from build_city_publication import digest


def check(root):
    catalog = json.loads((root / "resources.json").read_text())
    count = 0
    for resource in catalog["resources"]:
        if resource["format"] != "city_presentation_gzip_v1":
            continue
        prefix = f"project/{resource['scene_id']}/previews/{resource['version']}/"
        for asset in resource["assets"]:
            path = (root / asset["path"]).resolve()
            if not asset["path"].startswith(prefix) or not path.is_relative_to(root):
                raise ValueError("Resource escapes its ownership/version")
            if path.stat().st_size != asset["bytes"] or digest(path) != asset["sha256"]:
                raise ValueError("Resource checksum differs")
            count += 1
        base = (root / resource["entry"]).parent
        source = base / "provenance/source_manifest.json"
        if digest(source) != resource["provenance"]["source_manifest_sha256"]:
            raise ValueError("Source manifest checksum differs")
        model = json.loads((root / resource["model_manifest"]).read_text())
        transport = json.loads((root / resource["transport"]).read_text())
        for packed, folder in [
            (model, base / "model"),
            *((a, base / "physics") for a in transport["npy"].values()),
        ]:
            restored, total = hashlib.sha256(), 0
            for part in packed["parts"]:
                if part["offset"] != total:
                    raise ValueError("Compressed chunks must be contiguous")
                path = (folder / part["file"]).resolve()
                if not path.is_relative_to(base.resolve()):
                    raise ValueError("Chunk escapes resource")
                if (
                    digest(path) != part["sha256"]
                    or path.stat().st_size != part["compressed_bytes"]
                ):
                    raise ValueError("Compressed chunk differs")
                decoded = gzip.decompress(path.read_bytes())
                if len(decoded) != part["bytes"]:
                    raise ValueError("Decoded chunk size differs")
                if (
                    packed is model
                    and total == 0
                    and struct.unpack("<4sII", decoded[:12]) != (b"glTF", 2, packed["total_bytes"])
                ):
                    raise ValueError("Invalid decoded GLB")
                restored.update(decoded)
                total += len(decoded)
            if total != packed["total_bytes"] or restored.hexdigest() != packed["sha256"]:
                raise ValueError("Decoded asset differs from original bytes")
    print(
        f"VALID: {count} files; compressed checksums and complete decoded GLB/NPY SHA-256 verified"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resource_checkout", type=Path)
    check(parser.parse_args().resource_checkout.resolve())
