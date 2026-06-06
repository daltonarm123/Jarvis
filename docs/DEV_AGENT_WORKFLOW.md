# DevAgent Code Review & Patch Workflow

This document describes how to use the `DevAgent` code-review and patch workflow, and the supporting CLI commands.

Commands

- `review file <path>`
  - Ask `DevAgent` to review a file. The agent will request a review from the configured LLM and return a human summary plus a JSON suggestions block with `patches`.

- `fix file <path>`
  - Same as review but attempts to auto-apply `simple: true` patches when `ALLOW_DEV_AUTO_APPLY=true`.

- `/apply_patch <path-to-json>`
  - Apply patches from a JSON file (format produced by `DevAgent`). By default only patches with `simple=true` are applied; to allow non-simple patches set `ALLOW_DEV_APPLY=true`.

Environment flags

- `ALLOW_DEV_AUTO_APPLY` (default: `false`) — when `true`, `DevAgent` will write patches marked `simple: true` to disk during a `fix file` command.
- `ALLOW_DEV_APPLY` (default: `false`) — when `true`, `/apply_patch` will also write non-simple patches.

JSON patch format

DevAgent expects the LLM to return a JSON object inside a single JSON code block. Example:

```
{
  "summary": "Fix minor typo and simplify import",
  "patches": [
    {
      "path": "src/jarvis/some_module.py",
      "content": "<new file content>",
      "simple": true,
      "rationale": "Removes unused import and fixes edge case"
    }
  ]
}
```

Safety

- All file writes are limited to paths under the repository root.
- Non-simple patches require an explicit environment opt-in to apply.

Developer notes

- Tests are provided in `tests/test_dev_workflow.py`.
- The `AppAgent` can scaffold starter mobile apps; enable `ALLOW_APP_AUTO_APPLY` to write generated scaffolds to `apps/<name>/`.
