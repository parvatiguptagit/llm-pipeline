import os
from git import Repo

REPO_URL = "https://github.com/Significant-Gravitas/AutoGPT"
CLONE_DIR = "data/raw/repo"

def main():
    if os.path.exists(CLONE_DIR):
        print("Updating repo...")
        repo = Repo(CLONE_DIR)
        repo.remotes.origin.fetch(depth=1)
        repo.git.reset("--hard", "origin/HEAD")
    else:
        print("Cloning repo...")
        Repo.clone_from(REPO_URL, CLONE_DIR, depth=1)

    print("Repo ready")

if __name__ == "__main__":
    main()