---
name: build-tkinter-workflow-gui
description: Design, implement, refactor, or review a compact cross-platform Python desktop GUI built with Tkinter and ttk for multiple long-running workflows. Use when Codex needs to unify several CLI or batch-processing flows behind tabs; add YAML-driven forms, background execution, structured progress, cancellation, colored logs, file/image pickers, image previews, destructive-action confirmation, or native Windows/macOS application icons; or diagnose a Tkinter interface that freezes, has excessive spacing, stale configuration, unsafe thread updates, broken previews, or incorrect taskbar/Dock icons.
---

# Build Tkinter Workflow GUI

Build a thin, testable GUI layer around existing workflow services. Keep processing logic independent of Tk so CLI, tests, and future interfaces can reuse it.

## Route the task

1. Inspect the repository before editing:
   - Find entry points, workflow/service functions, configuration loaders, logging setup, result models, dependencies, and tests.
   - Check for project instructions and existing GUI frameworks. Extend an established framework instead of introducing Tkinter alongside it.
   - Check the active Python environment for `tkinter`, Pillow, and external executables.
2. Determine the requested scope:
   - For a new multi-workflow UI, follow the full workflow below.
   - For concurrency, progress, logging, or cancellation work, read [references/architecture.md](references/architecture.md).
   - For spacing, previews, icons, or platform behavior, read [references/ui-and-platform.md](references/ui-and-platform.md).
   - Before delivery, read [references/verification.md](references/verification.md).

## Establish boundaries

Preserve this dependency direction:

```text
GUI widgets → task runner → workflow/service layer → domain modules
```

Apply these rules:

- Keep file traversal, media processing, network calls, and domain decisions out of widget callbacks.
- Let the GUI collect and validate values, build a request, start a task, and render events/results.
- Run only one destructive or resource-heavy task at a time unless the product explicitly requires concurrency.
- Keep Tk widget access on the main thread. Move slow work to a worker and communicate through a queue.
- Cancel cooperatively at safe boundaries. Never interrupt a write in a way that knowingly leaves corrupt output.
- Confirm in-place or destructive operations immediately before execution.
- Resolve paths with `pathlib`; never hardcode user directories, drive letters, or path separators.

## Build the execution contract first

Before constructing tabs, give every workflow a consistent contract:

- Accept all values editable in the UI as explicit runtime options.
- Accept a progress callback that receives structured events rather than formatted log text.
- Accept a thread-safe cancellation token.
- Return one result type containing discovered, succeeded, skipped, failed, outputs, and errors.
- Check cancellation before each file and, where practical, between sub-operations such as exported segments.

Do not parse logs to calculate progress. Logs explain; events drive controls.

## Design UI configuration

Use a UI-oriented configuration file when CLI configuration does not map cleanly to forms. Organize it into:

```yaml
app:       # title, log level, external executables
ui:        # geometry, retained log lines, optional appearance
workflows: # initial form values keyed by workflow name
```

Treat loaded values as initial state. Do not silently write changed form values back to YAML. Provide an explicit save action only when persistence is part of the request.

Resolve relative business paths against a documented stable root. Keep machine-specific values in environment variables or ignored local files.

## Build a compact shell

Create one root window with:

- A `ttk.Notebook` containing one page per workflow and, when needed, a peer configuration page.
- A shared lower log panel.
- A single progress bar and status row.
- Reusable path fields, validation helpers, action buttons, and running-state controls.

Prefer grid layouts with deliberate weights. Use small, consistent padding and verify actual geometry; nested weighted rows commonly create large accidental gaps.

For each workflow page:

1. Group related values with `ttk.LabelFrame`.
2. Keep paths full-width and place browse buttons beside them.
3. Use checkbuttons for booleans and readonly comboboxes for constrained values.
4. Offer parameter preview when users need confidence before a batch run.
5. Provide Start and Cancel actions with mutually correct enabled states.
6. Make preview-only mode the default for in-place metadata or cover writes.

## Connect background execution

Use a worker thread plus `queue.Queue`:

- Worker: execute the service and enqueue started, progress, completed, cancelled, failed, and log messages.
- Main thread: poll with `root.after(...)`, update widgets, and show dialogs.
- Close handler: request cancellation and wait for a safe stop before destroying the root.
- Task state: disable every Start button during a run and reject configuration reloads.

Keep the queue messages structured. Do not pass widgets into the worker.

## Make feedback useful

Show these states explicitly: ready, scanning, running, cancelling, completed, failed.

Progress must include total, current index, current object, and a summary. Route the existing Python logger into the GUI with a custom `logging.Handler`; retain file logging.

For a terminal-style dark log panel, tag timestamp, logger, level, and message segments separately. Use conventional colors: DEBUG cyan, INFO green, WARNING yellow, ERROR red, CRITICAL magenta, logger blue, timestamp gray.

## Handle previews and icons deliberately

For image selection, render a proportional preview with Pillow. Debounce path-variable changes, use EXIF orientation, constrain the preview size, show filename and source dimensions, and retain the `ImageTk.PhotoImage` reference.

Generate platform icon assets from one square RGBA master:

- PNG for Tk and general fallback.
- Multi-resolution ICO for Windows.
- ICNS for a packaged macOS application.

Do not assume icon behavior is identical across Tk versions. On Windows, use the ICO and set an AppUserModelID before creating the root when taskbar identity matters. On macOS, avoid `wm iconbitmap` for an application image; it can create a broken document/proxy icon. Use an application bundle with ICNS or set `NSApplication.applicationIconImage` through AppKit. Keep transparent rounded corners if running outside a packaged `.app`.

## Verify and deliver

Run repository tests, lint/static checks, compilation, and `git diff --check`. Then perform a short GUI smoke test that constructs the root, initializes every tab, loads configuration, exercises previews/icons, calls `update_idletasks()`, and closes automatically.

Test with small controlled input before real batch processing. Report:

- Files and entry command.
- Supported pages and safety behavior.
- Test results and any environment warnings.
- Which platforms were actually run versus validated only by assets/code.
- Whether changes are committed or pushed.
