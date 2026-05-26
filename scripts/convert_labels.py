import json

INPUT = "labelstudio_export.json"
OUTPUT = "train.json"


def convert():
    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    dataset = []

    for item in data:
        query = item.get("data", {}).get("query", "")
        code = item.get("data", {}).get("code", "")

        if not item.get("annotations"):
            continue

        result = item["annotations"][0].get("result", [])
        if not result:
            continue
        choices = result[0].get("value", {}).get("choices", [])
        if not choices:
            continue
        label_raw = choices[0]

        label = 1 if label_raw == "Relevant" else 0

        dataset.append(
            {
                "query": query,
                "code": code,
                "label": label,
                "source": "human",
            }
        )

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    print(f"Converted {len(dataset)} human-labeled samples")


if __name__ == "__main__":
    convert()
