from pathlib import Path

from south_kensington_jupyter import SouthKensingtonConfig, run_pipeline, save_summary_and_arrays


def main() -> None:
    config = SouthKensingtonConfig(
        geometry_resolution_m=2.0,
        model_resolution_m=8.0,
        timesteppings=20,
        time_levels=(0, 4, 8, 12, 17),
        animation_stride=4,
        output_dir=str(Path("outputs") / "south_kensington_digit_smoke"),
    )
    results = run_pipeline(config)
    saved = save_summary_and_arrays(results)
    print(saved["summary_path"])


if __name__ == "__main__":
    main()
