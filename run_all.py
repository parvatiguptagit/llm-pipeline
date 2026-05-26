import argparse
import os
import subprocess
import sys


def run_step(step_name: str, script_name: str, env: dict) -> None:
    print(f"\n=== {step_name} ===")
    cmd = [sys.executable, script_name]
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Failed at {step_name}")


def build_env(mode: str) -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    env.setdefault("LABEL_STUDIO_URL", "https://beta-label.kantham.ai")
    env.setdefault("RECREATE_LABEL_PROJECT", "0")
    env.setdefault("PUSH_PREDICTIONS", "1")

    if mode == "fast":
        env.setdefault("MAX_AUTO_SAMPLES", "500")
        env.setdefault("MAX_TRAIN_SAMPLES", "200")
        env.setdefault("TRAIN_EPOCHS", "1")
        env.setdefault("TRAIN_BATCH_SIZE", "8")
        env.setdefault("MAX_UPLOAD_SAMPLES", "200")
        env.setdefault("MAX_PREDICTIONS", "100")
        env.setdefault("NOMIC_BATCH_SIZE", "32")
    else:
        env.setdefault("MAX_AUTO_SAMPLES", "100000")
        env.setdefault("MAX_TRAIN_SAMPLES", "50000")
        env.setdefault("TRAIN_EPOCHS", "2")
        env.setdefault("TRAIN_BATCH_SIZE", "16")
        env.setdefault("MAX_UPLOAD_SAMPLES", "500")
        env.setdefault("MAX_PREDICTIONS", "2000")
        env.setdefault("NOMIC_BATCH_SIZE", "64")

    return env


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot: data prep + Label Studio upload + Nomic supervised/semi train."
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "full"],
        default="fast",
        help="fast: quick local run, full: larger semi-supervised scale",
    )
    parser.add_argument(
        "--skip-step1",
        action="store_true",
        help="Skip dataset prep + upload, run training pipeline only",
    )
    args = parser.parse_args()

    env = build_env(args.mode)

    if not args.skip_step1:
        run_step("Step 1: Data + Upload pipeline", "pipeline.py", env)

    run_step("Step 2: Nomic supervised + semi-supervised training", "training_pipeline.py", env)
    print("\nFull pipeline completed (one shot).")


if __name__ == "__main__":
    main()
