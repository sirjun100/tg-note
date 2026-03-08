"""Bootstrap project-management/ structure when missing."""

import shutil
from datetime import date
from pathlib import Path

from importlib.resources import files as pkg_files


def get_project_root() -> Path:
    """Project root from PROJECT_ROOT env or cwd."""
    import os

    root = os.environ.get("PROJECT_ROOT")
    if root:
        return Path(root).resolve()
    return Path.cwd()


def get_pm_path() -> Path:
    """Project-management path (relative to project root)."""
    import os

    rel = os.environ.get("PM_PATH", "project-management")
    return get_project_root() / rel


def ensure_project_management() -> str:
    """
    Create project-management/ structure if it doesn't exist.
    Copies bundled templates and scripts.
    Returns status message.
    """
    root = get_project_root()
    pm = get_pm_path()

    if pm.exists() and (pm / "backlog" / "product-backlog.md").exists():
        return f"project-management/ already exists at {pm}"

    data = pkg_files("mcp_project_management") / "data"

    dirs = [
        pm / "backlog" / "user-stories",
        pm / "backlog" / "defects",
        pm / "backlog" / "technical-debt",
        pm / "backlog" / "retrospective-improvements",
        pm / "processes",
        pm / "templates",
        pm / "criteria",
        pm / "sprints",
        pm / "architecture-decision-records",
        pm / "scripts",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Copy templates
    templates = [
        ("user-story-template.md", "templates"),
        ("defect-template.md", "templates"),
        ("technical-debt-template.md", "templates"),
        ("product-backlog-template.md", "templates"),
    ]
    for name, subdir in templates:
        src = data / name
        if src.exists():
            shutil.copy2(src, pm / subdir / name)

    # Create initial product-backlog.md (empty tables)
    initial = data / "product-backlog-initial.md"
    if initial.exists():
        content = initial.read_text(encoding="utf-8")
        content = content.replace("YYYY-MM-DD", date.today().isoformat())
        (pm / "backlog" / "product-backlog.md").write_text(content, encoding="utf-8")

    # Copy INDEX, README, glossary
    for name in ("index.md", "README.md", "glossary.md"):
        src = data / name
        if src.exists():
            dest_name = "INDEX.md" if name == "index.md" else name
            shutil.copy2(src, pm / dest_name)

    # Copy processes and criteria
    for subdir in ("processes", "criteria"):
        src_dir = data / subdir
        if src_dir.exists():
            for f in src_dir.iterdir():
                if f.suffix == ".md":
                    shutil.copy2(f, pm / subdir / f.name)

    # Copy scripts
    scripts_dir = data / "scripts"
    if scripts_dir.exists():
        for f in scripts_dir.iterdir():
            if f.suffix == ".sh":
                dest = pm / "scripts" / f.name
                shutil.copy2(f, dest)
                dest.chmod(0o755)

    return f"Created project-management/ at {pm} with templates and scripts."
