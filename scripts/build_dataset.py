from datasets import Dataset
import json

INPUT = "data/processed/cleaned.json"
OUTPUT = "data/processed/instruct_v1"

def main():
    with open(INPUT) as f:
        data = json.load(f)

    ds = Dataset.from_list(data)
    ds.save_to_disk(OUTPUT)

    print("Dataset created")

if __name__ == "__main__":
    main()