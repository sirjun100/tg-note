"""MCP prompts: workflow templates for project management."""

from .bootstrap import ensure_project_management, get_pm_path
from .tools import mcp


def _read(path: str) -> str:
    pm = get_pm_path()
    p = pm / path
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


@mcp.prompt
def create_user_story(
    description: str,
    acceptance_criteria: str = "",
    dependencies: str = "",
) -> str:
    """Create a user story. Use the create_user_story tool with title, description, acceptance_criteria, priority, story_points. Save to backlog/user-stories/ and add to product backlog."""
    process = _read("processes/backlog-management-process.md")[:2500]
    return f"""Create a user story with this description: {description}
{f'Acceptance criteria: {acceptance_criteria}' if acceptance_criteria else ''}
{f'Dependencies: {dependencies}' if dependencies else ''}

Use the create_user_story tool to create the file and add to product backlog. Provide: title (from description), description, acceptance_criteria, priority (Critical/High/Medium/Low), story_points (Fibonacci: 1,2,3,5,8,13).

Process excerpt:
{process}"""


@mcp.prompt
def create_defect(
    description: str,
    steps_to_reproduce: str = "",
    priority: str = "Medium",
) -> str:
    """Create a defect report. Use the create_defect tool with title, description, steps_to_reproduce, expected_behavior, actual_behavior, priority. Save to backlog/defects/ and add to product backlog."""
    return f"""Create a defect report: {description}
Steps to reproduce: {steps_to_reproduce or 'TBD'}
Priority: {priority}

Use the create_defect tool to create the file and add to product backlog. Provide: title, description, steps_to_reproduce, expected_behavior, actual_behavior, priority, story_points."""


@mcp.prompt
def run_documentation_code_consistency_check() -> str:
    """Run Documentation-Code Consistency Check before commit. Compare code with project-management/ docs. Code is source of truth. Present report and wait for human decisions."""
    process = _read("processes/doc-code-consistency-process.md")
    return f"""Generate a Documentation-Code Consistency Check report. Compare code with project-management/ docs.
Code is the source of truth. Present the report and wait for human decisions on what to update.

Process:
{process[:2000]}"""


@mcp.prompt
def generate_release_notes(commit_count: int = 20) -> str:
    """Generate release notes draft. Run generate_release_notes_draft tool, then format output for RELEASE_NOTES.md."""
    process = _read("processes/release-notes-process.md")[:1500]
    return f"""Generate release notes. Run the generate_release_notes_draft tool with commit_count={commit_count}, then help format the output for RELEASE_NOTES.md.

Process excerpt:
{process}"""


@mcp.prompt
def refine_backlog_item(item_id: str) -> str:
    """Refine a backlog item (US-XXX or DEF-XXX) against Definition of Ready. Check acceptance criteria, dependencies, story points, no open questions."""
    dor = _read("criteria/definition-of-ready.md")
    return f"""Review {item_id} and refine it. Check Definition of Ready:
- Acceptance criteria specific and testable
- Dependencies identified
- Story points estimated (Fibonacci)
- No open clarifying questions
- Priority assigned

Definition of Ready:
{dor}"""


@mcp.prompt
def start_sprint_planning(sprint_number: int, velocity: int = 8) -> str:
    """Start sprint planning. Run backlog_metrics, review product backlog, check Definition of Ready, sort by dependencies, suggest items to select."""
    process = _read("processes/sprint-planning-process.md")
    return f"""Start sprint planning for Sprint {sprint_number}. Team velocity: {velocity} points.
1. Run backlog_metrics tool
2. Read pm://product-backlog resource
3. Check items meet Definition of Ready (pm://criteria/definition-of-ready)
4. Sort by dependencies, suggest items to select
5. Create sprint document from template

Process:
{process[:3000]}"""


@mcp.prompt
def run_sprint_retrospective(sprint_number: int) -> str:
    """Run sprint retrospective. Run backlog_metrics first, then guide through 8 steps. Use retrospective template."""
    process = _read("processes/sprint-retrospective-process.md")
    return f"""Run sprint retrospective for Sprint {sprint_number}.
1. Run backlog_metrics tool first
2. Follow the retrospective process (8 steps)
3. Use retrospective template to capture output
4. Add output to sprint document

Process:
{process[:2500]}"""


@mcp.prompt
def identify_technical_debt(description: str) -> str:
    """Identify and capture technical debt. Use create_technical_debt tool to create TD-XXX and add to backlog."""
    process = _read("processes/technical-debt-identification-process.md")[:1500]
    return f"""Identify technical debt: {description}

Use the create_technical_debt tool to create a TD-XXX item and add to product backlog. Provide: title, description, impact, proposed_solution, priority, story_points.

Process excerpt:
{process}"""
