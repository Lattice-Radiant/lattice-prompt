"""Create an arch2code project of the integrated flow from the bundle's project template.

    python templates/new_project.py <directory> [--name <project>] [--submodule]

Copies templates/project into <directory> (which must not exist or must be empty), replaces
@PROJECT@ with the project name (default: the directory's basename, made a valid identifier),
and initialises a Git repository. --submodule adds cortex-a2c as the arch2code/ submodule so the
project pins its generator version; without it the project builds with the bundle's arch2code
through bin/a2c-make (A2C_ROOT). The bundle launchers bin/new-project(.cmd) call this.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "project")
A2C_URL = "https://github.com/Lattice-Radiant/cortex-a2c.git"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="create a project from the lattice-prompt template")
    ap.add_argument("directory")
    ap.add_argument("--name", default=None, help="project name (default: the directory name)")
    ap.add_argument("--submodule", action="store_true", help="add cortex-a2c as the arch2code/ submodule")
    ap.add_argument("--no-git", action="store_true", help="do not initialise a Git repository")
    args = ap.parse_args(argv)
    dest = os.path.abspath(args.directory)
    if os.path.exists(dest) and os.listdir(dest):
        print(f"{dest} exists and is not empty", file=sys.stderr)
        return 1
    name = args.name or os.path.basename(dest)
    name = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not re.match(r"^[A-Za-z_]", name):
        name = "p_" + name
    shutil.copytree(TEMPLATE, dest, dirs_exist_ok=True)
    for root, _, files in os.walk(dest):
        for f in files:
            p = os.path.join(root, f)
            try:
                text = open(p, encoding="utf-8").read()
            except UnicodeDecodeError:
                continue
            if "@PROJECT@" in text:
                with open(p, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(text.replace("@PROJECT@", name))
    print(f"created {dest} (project {name})")
    if args.no_git:
        return 0
    if shutil.which("git") is None:
        print("git not found: repository not initialised", file=sys.stderr)
        return 0
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    if args.submodule:
        subprocess.run(["git", "submodule", "add", A2C_URL, "arch2code"], cwd=dest, check=True)
        print("arch2code added as a submodule; commit to pin it")
    print("next: bin/a2c-make agents-setup in the project, copy .mcp.json.example to .mcp.json, open it in Claude Code")
    return 0


if __name__ == "__main__":
    sys.exit(main())
