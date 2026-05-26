import os

import sys

import datetime



def run(step, command):

    print(f"\n== {step} ==")

    code = os.system(command)

    if code != 0:

        raise RuntimeError(f"Failed at {step}")



def main():

    py = f"\"{sys.executable}\""

    run("Export Labels", f"{py} scripts/export_labels.py")

    run("Convert Labels", f"{py} scripts/convert_labels.py")

    run("Nomic Pseudo-Label (semi-supervised)", f"{py} scripts/auto_label.py")

    run("Merge Dataset", f"{py} scripts/merge.py")

    # Save fine-tuned Nomic to a unique directory to avoid Windows file-lock issues
    # when overwriting an already memory-mapped model directory.
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    model_dir = os.path.join("models", f"nomic-retrieval-run-{ts}")
    model_dir_env = f"set \"NOMIC_MODEL_DIR={model_dir}\" && "

    run("Train Nomic Embed", f"{model_dir_env}{py} scripts/train_nomic.py")

    run(
        "Push Predictions to Label Studio",
        f"{model_dir_env}{py} scripts/push_predictions.py",
    )



if __name__ == "__main__":

    main()

