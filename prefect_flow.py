import subprocess
import sys

from prefect import flow, task


@task(name="Data + Upload Pipeline")
def run_pipeline():
    result = subprocess.run([sys.executable, "pipeline.py"])
    if result.returncode != 0:
        raise RuntimeError("pipeline.py failed")


@task(name="Confidence Routing")
def run_confidence_router():
    result = subprocess.run([sys.executable, "confidence_router.py"])
    if result.returncode != 0:
        raise RuntimeError("confidence_router.py failed")


@task(name="Dataset Validation")
def validate_dataset():
    result = subprocess.run([sys.executable, "dataset_validator.py"])
    if result.returncode != 0:
        raise RuntimeError("dataset_validator.py failed")


@task(name="Nomic Training")
def train_model():
    result = subprocess.run([sys.executable, "training_pipeline.py"])
    if result.returncode != 0:
        raise RuntimeError("training_pipeline.py failed")


@task(name="Model Evaluation")
def evaluate_model():
    result = subprocess.run([sys.executable, "evaluate_model.py"])
    if result.returncode != 0:
        raise RuntimeError("evaluate_model.py failed — model did not pass quality gate")


@task(name="Build Vector Database")
def build_vector_db():
    result = subprocess.run([sys.executable, "build_vector_db.py"])
    if result.returncode != 0:
        raise RuntimeError("build_vector_db.py failed")


@flow(name="Continuous Learning Pipeline")
def continuous_learning_flow():
    run_pipeline()
    run_confidence_router()
    validate_dataset()
    train_model()
    evaluate_model()
    build_vector_db()


if __name__ == "__main__":
    continuous_learning_flow()
