import subprocess
import sys

def run(step, cmd):
    print(f"\n== {step} ==")
    result = subprocess.run(cmd, shell=True)

    if result.returncode != 0:
        raise Exception(f"Failed at {step}")

def main():
    py = f"\"{sys.executable}\""
    run("Repo Sync", f"{py} scripts/repo_sync.py")
    run("Extract Functions", f"{py} scripts/extract_functions.py")
    run("Clean Data", f"{py} scripts/clean_data.py")
    run("Build Dataset", f"{py} scripts/build_dataset.py")

    # 🔥 DVC versioning step
    run("DVC Track", f"{py} -m dvc add data/processed/instruct_v1")

    run("Upload to Label Studio", f"{py} scripts/upload_labelstudio.py")

    print("\nFULL PIPELINE COMPLETE")

if __name__ == "__main__":
    main()