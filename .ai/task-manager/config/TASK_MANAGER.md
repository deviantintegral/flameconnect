# Task Manager General Information

This document contains important information that is common to all the /task:*
commands for AI assistants.

## Types of Documents

Work orders (abbreviated as WO) are complex prompts for programming,
organizational, or management tasks created by a user. Work orders are
independent of each other and cannot share any context. By definition
different work orders can be worked on independently.

Each work order has plan associated to it. The plan is a comprehensive document
highlighting all the aspects of the work necessary to accomplish the goals from
the work order.

Each plan will be broken into tasks. Each task is a logical unit of work that
has a single purpose, and is solved using a single skill. All tasks exist as
part of a plan. Tasks can have dependencies on other tasks. This happens when a
task cannot be worked on (or completed) before some other task(s) are completed.

## Directory Structure

To find a plan document from its ID use the following command (replace {planId} with the ID, like 06):
```shell
find .ai/task-manager/{plans,archive} -name "plan-[0-9][0-9]*--*.md" -type f -exec grep -l "^id: \?{planId}$" {} \;
```

Plans, and tasks are stored as MarkDown files with a YAML front-matter. They are
all filed under the `.ai/task-manager/` folder at the root of the repository.

Plans are organized as follows:

```
.ai/
  task-manager/
    plans/           # Active plans (work in progress)
      01--authentication-provider/
        plan-01--authentication-provider.md
        tasks/
          01--create-project-structure.md
          02--implement-authorization.md
          03--this-example-task.md
          04--create-tests.md
          05--update-documentation.md
    archive/         # Completed plans (successfully executed)
      05--user-management/
        plan-05--user-management.md
        tasks/
          01--create-user-model.md
          02--implement-crud-operations.md
          03--add-validation.md
```

Note how in the `.ai/task-manager/plans/` folder we have a sub-folder per plan.
Each sub-folder will contain the plan document and has a name following a naming
pattern `[ID]--[plan-short-name]`. Where the ID is auto-incremental. The plan
document has a name following the pattern `plan-[ID]--[plan-short-name].md`.
Finally, all tasks are under a `tasks` sub-folder. Each task has a name
according to the pattern `[incremental-ID]--[task-short-name].md`. IDs for tasks
are auto-incremental within a plan. Each plan starts their tasks' IDs from 01.

## Plan Lifecycle and Archive System

Plans follow a lifecycle that maintains workspace organization:

1. **Active Plans**: When created, plans are placed in the `plans/` directory where they remain while being worked on.

2. **Completed Plans**: Upon successful execution of a blueprint (via `/tasks:execute-blueprint`), the entire plan directory is automatically moved from `plans/` to `archive/`.

3. **Archive Directory**: The `archive/` directory serves as permanent storage for completed work. This separation keeps the active workspace clean while preserving completed plans for reference.

The archive system provides several benefits:
- **Workspace Organization**: Active plans remain easily accessible while completed work doesn't clutter the workspace
- **Historical Reference**: Completed plans and their tasks remain available for future reference or learning
- **Automatic Management**: No manual intervention required - archival happens automatically upon successful completion

## Technology Choices

- python 3.13+
- async-first design using aiohttp
- uv for dependency management
- ruff for linting and formatting
- mypy for strict type checking
- pytest for testing
- mutmut for mutation testing
- textual for the text UI (TUI) mode
- stdlib logging module
- Fully type-annotated codebase enforced by mypy in strict mode.
- Use Python's stdlib logging module. No print() for library code. Follows Home Assistant's logging conventions.
- github actions
- conventional commits (validated by a github workflow)
- googleapis/release-please for release management
- packages are published to pypi.org
- minimal third-party python dependencies. prioritize using dependencies already included in Home Assistant.

## Project Philosophy

- Async-first library design. Home Assistant is fully async, so the core API must be natively async (not sync wrapped in executors).
- A clean API able to be consumed by other systems like Home Assistant.
- Authentication supports both token injection (callers provide an access token or a callable that returns one) for integrations like Home Assistant, and built-in credential handling for CLI/standalone use.
- A command line tool built on the API to make API calls.
- The command line tool should have a text UI mode to display current statuses and execute commands.
- All functions related to managing the fireplace exposed in the app should be available in this library.
- Automated tests with fixtures that do not require live API access.
- A high level of test coverage including mutation testing.
- Respect for the upstream API systems. We should only make the API calls directly needed to meet a user's requests and not spam the remote servers.
- The README should be written for humans, not AIs.
