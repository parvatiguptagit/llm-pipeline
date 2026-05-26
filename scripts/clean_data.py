import json

INPUT = "data/processed/functions.json"
OUTPUT = "data/processed/cleaned.json"

def make_soft_query(func_name):
    return (
        func_name.replace("_", " ")
        .replace("get", "retrieve")
        .replace("calc", "calculate")
        .strip()
        + " function"
    )

def main():
    with open(INPUT) as f:
        data = json.load(f)

    seen = set()
    cleaned = []

    for item in data:
        code = item["code"]

        if code in seen:
            continue
        seen.add(code)

        func_name = item["query"]

        cleaned.append({
            "hard_query": func_name,
            "soft_query": make_soft_query(func_name),
            "code": code,
            "instruction": f"Write a function for {make_soft_query(func_name)}"
        })

    with open(OUTPUT, "w") as f:
        json.dump(cleaned, f, indent=2)

    print(f"Enhanced dataset: {len(cleaned)} samples")

if __name__ == "__main__":
    main()