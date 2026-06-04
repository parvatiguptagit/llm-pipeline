import argparse
import glob
import os
import subprocess
import sys


def run_step(step_name: str, script_name: str, env: dict) -> None:
    print(f"\n=== {step_name} ===")
    cmd = [sys.executable, script_name]
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Failed at {step_name}")


def _find_latest_model(models_dir="models"):
    matches = sorted(glob.glob(os.path.join(models_dir, "nomic-retrieval-run-*")))
    return matches[-1] if matches else None


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
        env.setdefault("TRAIN_BATCH_SIZE", "2")
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
        description=(
            "Continuous learning pipeline: data prep → confidence routing → "
            "validation → training → evaluation → vector DB."
        )
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
        help="Skip dataset prep + upload (pipeline.py), run from training onward",
    )
    parser.add_argument(
        "--skip-routing",
        action="store_true",
        help="Skip confidence routing (confidence_router.py)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip dataset validation (dataset_validator.py)",
    )
    parser.add_argument(
        "--skip-evaluation",
        action="store_true",
        help="Skip model evaluation gate (evaluate_model.py)",
    )
    parser.add_argument(
        "--skip-vectordb",
        action="store_true",
        help="Skip vector database build (build_vector_db.py)",
    )
    args = parser.parse_args()

    env = build_env(args.mode)

    # Phase 1 — data prep and Label Studio upload
    if not args.skip_step1:
        run_step("Step 1: Data + Upload pipeline", "pipeline.py", env)

    # Phase 2 — confidence routing (active learning split)
    if not args.skip_routing:
        run_step("Step 2: Confidence routing", "confidence_router.py", env)

    # Phase 3 — dataset validation (dedup + empty-filter)
    if not args.skip_validation:
        run_step("Step 3: Dataset validation", "dataset_validator.py", env)

    # Phase 4 — Nomic supervised + semi-supervised training
    run_step("Step 4: Nomic supervised + semi-supervised training", "training_pipeline.py", env)

    # After training, point downstream steps at the freshly-built model
    latest_model = _find_latest_model()
    if latest_model:
        env["NOMIC_MODEL_DIR"] = latest_model
        print(f"Using model: {latest_model}")

    # Phase 5 — model evaluation gate
    if not args.skip_evaluation:
        run_step("Step 5: Model evaluation", "evaluate_model.py", env)

    # Phase 6 — build vector database for retrieval
    if not args.skip_vectordb:
        run_step("Step 6: Build vector database", "build_vector_db.py", env)

    print("\nFull continuous learning pipeline completed.")


if __name__ == "__main__":
    main()
