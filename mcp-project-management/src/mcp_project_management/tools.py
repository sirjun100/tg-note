"""MCP tools: script wrappers and file-writing tools."""

import os
import re
import subprocess
from datetime import date
from pathlib import Path

from fastmcp import FastMCP

from .bootstrap import ensure_project_management, get_pm_path, get_project_root

mcp = FastMCP(name="Project Management", version="0.1.0")


def _run_script(script_name: str, *args: str, cwd: Path | None = None) -> str:
    """Run a project-management script and return stdout+stderr."""
    root = cwd or get_project_root()
    pm = get_pm_path()
    script = pm / "scripts" / script_name

    if not script.exists():
        ensure_project_management()
        script = pm / "scripts" / script_name
        if not script.exists():
            return f"Error: Script not found: {script}"

    # Pass PROJECT_ROOT so git-based scripts work when MCP cwd differs from project root
    env = {**os.environ, "PROJECT_ROOT": str(root.resolve())}

    try:
        result = subprocess.run(
            [str(script), *args],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = result.stdout or ""
        err = result.stderr or ""
        if result.returncode != 0 and err:
            out = f"{out}\n--- stderr ---\n{err}" if out else err
        if result.returncode != 0:
            out = f"{out}\n(exit code: {result.returncode})"
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Script timed out after 120 seconds"
    except Exception as e:
        return f"Error running script: {e}"


# --- Script tools ---


@mcp.tool
def validate_backlog(
    backlog_dir: str = "project-management/backlog",
) -> str:
    """Validates backlog structure, naming conventions (US-XXX, DEF-XXX), and cross-references."""
    return _run_script("validate-backlog.sh", backlog_dir)


@mcp.tool
def backlog_metrics(
    stats: bool = False,
    backlog_dir: str = "project-management/backlog",
    sprints_dir: str = "project-management/sprints",
) -> str:
    """Computes backlog health: items by status, aging, velocity, story points. Use stats=True for product-backlog.md stats block."""
    args = []
    if stats:
        args.append("--stats")
    args.extend([backlog_dir, sprints_dir])
    return _run_script("backlog-metrics.sh", *args)


@mcp.tool
def check_links(
    scan_dir: str = "project-management",
    base_dir: str = ".",
) -> str:
    """Checks for broken markdown links in project-management files."""
    return _run_script("check-links.sh", scan_dir, base_dir)


@mcp.tool
def generate_release_notes_draft(
    commit_count: int = 20,
    auto: bool = False,
    dry_run: bool = False,
) -> str:
    """Generates release notes draft from recent commits. Use auto=True to append to RELEASE_NOTES.md, dry_run=True to preview."""
    args = []
    if auto:
        args.append("--auto")
    elif dry_run:
        args.append("--dry-run")
    args.append(str(commit_count))
    return _run_script("generate-release-notes-draft.sh", *args)


@mcp.tool
def validate_backlog_integrity(
    backlog_dir: str = "project-management/backlog",
) -> str:
    """Checks backlog integrity: orphan refs, missing files, duplicate IDs, Fibonacci story points."""
    return _run_script("validate-backlog-integrity.sh", backlog_dir)


@mcp.tool
def visualize_dependencies(
    backlog_dir: str = "project-management/backlog",
) -> str:
    """Generates Mermaid flowchart of dependencies between user stories and defects."""
    return _run_script("visualize-dependencies.sh", backlog_dir)


@mcp.tool
def lint_project_management() -> str:
    """Runs full lint: backlog validation, links, forbidden terminology, newline-at-EOF."""
    return _run_script("lint-project-management.sh")


@mcp.tool
def prepare_gap_check() -> str:
    """Lists changed files and reminds about Documentation-Code Consistency Check before commit."""
    return _run_script("prepare-gap-check.sh")


# --- File-writing helpers ---


def _slug(text: str) -> str:
    """Create filename slug from title."""
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s[:50] if s else "item"


def _next_id(prefix: str, pm: Path) -> str:
    """Get next ID (US-001, DEF-001, TD-001)."""
    if prefix == "US":
        dir_path = pm / "backlog" / "user-stories"
    elif prefix == "DEF":
        dir_path = pm / "backlog" / "defects"
    elif prefix == "TD":
        dir_path = pm / "backlog" / "technical-debt"
    else:
        return f"{prefix}-001"

    if not dir_path.exists():
        return f"{prefix}-001"

    max_n = 0
    for f in dir_path.glob(f"{prefix}-*.md"):
        m = re.search(rf"{prefix}-(\d+)", f.name)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"{prefix}-{max_n + 1:03d}"


def _priority_emoji(priority: str) -> str:
    p = priority.lower()
    if "critical" in p:
        return "🔴"
    if "high" in p:
        return "🟠"
    if "medium" in p:
        return "🟡"
    return "🟢"


def _add_backlog_row(
    pm: Path,
    section: str,
    row: str,
) -> None:
    """Insert a row into the product backlog table."""
    pb = pm / "backlog" / "product-backlog.md"
    if not pb.exists():
        return
    content = pb.read_text(encoding="utf-8")
    today = date.today().isoformat()

    # Find the section table and insert before the closing |
    # Pattern: ## User Stories ... | ID | ... | \n|----|... then we insert before next ##
    section_header = f"## {section}"
    if section_header not in content:
        return

    # Find the table body (after header row |----|----|...)
    parts = content.split(section_header, 1)
    if len(parts) < 2:
        return
    after_header = parts[1]
    # Table ends at next ## or ---
    table_end = re.search(r"\n(## |---)", after_header)
    if table_end:
        table_content = after_header[: table_end.start()]
    else:
        table_content = after_header

    # Check if table has only header row (no data rows)
    lines = table_content.strip().split("\n")
    # Header is | ID | Title | ... ; separator is |----|----| ; data rows follow
    # Insert our row after the separator line
    new_row = row + "\n"
    for i, line in enumerate(lines):
        if re.match(r"^\|[-:\s|]+\|", line):  # separator row
            lines.insert(i + 1, row)
            break
    else:
        lines.append(row)

    new_table = "\n".join(lines) + "\n"
    if table_end:
        rest = after_header[table_end.start() :]
    else:
        rest = ""
    # Preserve blank line between section header and table
    new_after = "\n\n" + new_table + rest
    new_content = parts[0] + section_header + new_after
    new_content = re.sub(
        r"\*\*Last Updated\*\*: \d{4}-\d{2}-\d{2}",
        f"**Last Updated**: {today}",
        new_content,
        count=1,
    )
    pb.write_text(new_content, encoding="utf-8")


# --- File-writing tools ---


@mcp.tool
def create_user_story(
    title: str,
    description: str,
    acceptance_criteria: str = "",
    priority: str = "Medium",
    story_points: int = 2,
    user_story_format: str = "",
    dependencies: str = "",
) -> str:
    """Create a user story file and add it to the product backlog. Returns the created file path."""
    ensure_project_management()
    pm = get_pm_path()
    root = get_project_root()

    item_id = _next_id("US", pm)
    slug = _slug(title)
    filename = f"{item_id}-{slug}.md"
    filepath = pm / "backlog" / "user-stories" / filename

    template_path = pm / "templates" / "user-story-template.md"
    if not template_path.exists():
        from importlib.resources import files

        data = files("mcp_project_management") / "data"
        tpl = (data / "user-story-template.md").read_text(encoding="utf-8")
    else:
        tpl = template_path.read_text(encoding="utf-8")

    today = date.today().isoformat()
    emoji = _priority_emoji(priority)

    content = tpl.replace("[ID]", item_id)
    content = content.replace("[Story Title]", title)
    content = content.replace("[X]", str(story_points))
    content = content.replace("[YYYY-MM-DD]", today)
    content = content.replace("🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low", f"{emoji} {priority}")
    content = content.replace(
        "[Clear description of the user story. Explain what needs to be built and why.]",
        description,
    )
    if user_story_format:
        content = content.replace(
            'As a [user type: e.g., "registered user", "admin", "mobile app user"], \nI want [functionality: e.g., "to filter search results by date"], \nso that [benefit: e.g., "I can quickly find recent items"].',
            user_story_format,
        )
    if acceptance_criteria:
        ac_lines = "\n".join(f"- [ ] {c.strip()}" for c in acceptance_criteria.split("\n") if c.strip())
        content = content.replace(
            "- [ ] Criterion 1 (specific, testable)\n- [ ] Criterion 2 (specific, testable)\n- [ ] Criterion 3 (specific, testable)",
            ac_lines or "- [ ] (to be defined)",
        )
    if dependencies:
        dep_lines = "\n".join(f"- {d.strip()}" for d in dependencies.split("\n") if d.strip())
        content = content.replace(
            "- [Dependency 1 - what must be completed first]\n- [Dependency 2 - what must be completed first]",
            dep_lines,
        )

    content = content.replace("(user-stories/US-001-story-name.md)", f"user-stories/{filename}")
    filepath.write_text(content, encoding="utf-8")

    rel_link = f"user-stories/{filename}"
    row = f"| [{item_id}]({rel_link}) | {title[:50]} | {emoji} {priority} | {story_points} | ⭕ | - | {today} | {today} |"
    _add_backlog_row(pm, "User Stories", row)

    return f"Created {filepath.relative_to(root)} and added to product backlog."


@mcp.tool
def create_defect(
    title: str,
    description: str,
    steps_to_reproduce: str = "",
    expected_behavior: str = "",
    actual_behavior: str = "",
    priority: str = "Medium",
    story_points: int = 2,
) -> str:
    """Create a defect file and add it to the product backlog. Returns the created file path."""
    ensure_project_management()
    pm = get_pm_path()
    root = get_project_root()

    item_id = _next_id("DEF", pm)
    slug = _slug(title)
    filename = f"{item_id}-{slug}.md"
    filepath = pm / "backlog" / "defects" / filename

    template_path = pm / "templates" / "defect-template.md"
    if not template_path.exists():
        from importlib.resources import files

        data = files("mcp_project_management") / "data"
        tpl = (data / "defect-template.md").read_text(encoding="utf-8")
    else:
        tpl = template_path.read_text(encoding="utf-8")

    today = date.today().isoformat()
    emoji = _priority_emoji(priority)

    content = tpl.replace("[ID]", item_id)
    content = content.replace("[Defect Description]", title)
    content = content.replace("[X]", str(story_points))
    content = content.replace("[YYYY-MM-DD]", today)
    content = content.replace("🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low", f"{emoji} {priority}")
    content = content.replace(
        "[Clear, concise description of the defect. One or two sentences summarizing the issue.]",
        description,
    )
    if steps_to_reproduce:
        steps_lines = "\n".join(f"{i+1}. {s.strip()}" for i, s in enumerate(steps_to_reproduce.split("\n")) if s.strip())
        content = content.replace(
            "1. [Step 1 - specific action: e.g., \"Navigate to Settings > Profile\"]\n2. [Step 2 - specific action: e.g., \"Enter email: 'user+test@example.com'\"]\n3. [Step 3 - specific action: e.g., \"Click 'Save' button\"]\n4. [Observed behavior - what happens: e.g., \"Error message appears: 'Invalid email format'\"]",
            steps_lines or "1. (to be documented)",
        )
    if expected_behavior:
        content = content.replace("[What should happen when following the steps above.]", expected_behavior)
    if actual_behavior:
        content = content.replace("[What actually happens when following the steps above. Include error messages, crashes, incorrect behavior, etc.]", actual_behavior)

    content = content.replace("(defects/DEF-001-defect-description.md)", f"defects/{filename}")
    filepath.write_text(content, encoding="utf-8")

    rel_link = f"defects/{filename}"
    row = f"| [{item_id}]({rel_link}) | {title[:50]} | {emoji} {priority} | {story_points} | ⭕ | - | {today} | {today} |"
    _add_backlog_row(pm, "Defects", row)

    return f"Created {filepath.relative_to(root)} and added to product backlog."


@mcp.tool
def create_technical_debt(
    title: str,
    description: str,
    impact: str = "",
    proposed_solution: str = "",
    priority: str = "Medium",
    story_points: int = 2,
) -> str:
    """Create a technical debt item and add it to the product backlog."""
    ensure_project_management()
    pm = get_pm_path()
    root = get_project_root()

    item_id = _next_id("TD", pm)
    slug = _slug(title)
    filename = f"{item_id}-{slug}.md"
    filepath = pm / "backlog" / "technical-debt" / filename

    template_path = pm / "templates" / "technical-debt-template.md"
    if not template_path.exists():
        from importlib.resources import files

        data = files("mcp_project_management") / "data"
        tpl = (data / "technical-debt-template.md").read_text(encoding="utf-8")
    else:
        tpl = template_path.read_text(encoding="utf-8")

    today = date.today().isoformat()
    emoji = _priority_emoji(priority)

    content = tpl.replace("[ID]", item_id)
    content = content.replace("[Short Description]", title)
    content = content.replace("[X]", str(story_points))
    content = content.replace("[YYYY-MM-DD]", today)
    content = content.replace("🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low", f"{emoji} {priority}")
    content = content.replace(
        "[What technical debt exists? What needs to be improved or refactored?]",
        description,
    )
    if impact:
        content = content.replace("[Why does this matter? What risks or costs does it impose?]", impact)
    if proposed_solution:
        content = content.replace("[How will this be addressed? High-level approach.]", proposed_solution)

    content = content.replace("(technical-debt/TD-001-description.md)", f"technical-debt/{filename}")
    filepath.write_text(content, encoding="utf-8")

    rel_link = f"technical-debt/{filename}"
    row = f"| [{item_id}]({rel_link}) | {title[:50]} | {emoji} {priority} | {story_points} | ⭕ | - | {today} | {today} |"
    _add_backlog_row(pm, "Technical Debt", row)

    return f"Created {filepath.relative_to(root)} and added to product backlog."
