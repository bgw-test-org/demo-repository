"""Build GitHub Actions workflow YAML files from *.template.yml templates.

For each `.github/workflows/*.template.yml`, this script:
  1. Loads the YAML.
  2. Walks every step in every job; if a step has `inject-script: <name>`,
     the key is removed and `run:` is set to the contents of `scripts/<name>`.
  3. Dumps to the corresponding `*.yml` (without `.template`), with a
     "do not edit" header.
"""

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
SCRIPTS = REPO_ROOT / "scripts"

HEADER = (
    "# THIS FILE IS GENERATED. DO NOT EDIT.\n"
    "# Edit the *.template.yml file or the script under scripts/,\n"
    "# then run: uv run python scripts/build_workflows.py\n"
    "\n"
)


def _str_repr(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


yaml.SafeDumper.add_representer(str, _str_repr)


def build(template: Path) -> Path:
    doc = yaml.safe_load(template.read_text())
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            name = step.pop("inject-script", None)
            if name is not None:
                step["run"] = (SCRIPTS / name).read_text()
    out = template.with_name(template.name.removesuffix(".template.yml") + ".yml")
    out.write_text(HEADER + yaml.safe_dump(doc, sort_keys=False, width=80))
    return out


def main() -> int:
    for tpl in sorted(WORKFLOWS.glob("*.template.yml")):
        out = build(tpl)
        print(f"wrote {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
