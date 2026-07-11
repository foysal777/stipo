import subprocess

try:
    res = subprocess.check_output(["git", "ls-files", "app/migrations/"], text=True)
    with open("git_tracked.txt", "w") as f:
        f.write(res)
except Exception as e:
    with open("git_tracked.txt", "w") as f:
        f.write(f"Error: {e}")
