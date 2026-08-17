# Verification and delivery

Read this reference before handing off any Tkinter workflow GUI change.

## Automated checks

Run the project's own environment and commands. At minimum:

```text
unit/integration tests
lint or static checks
compile/import check
git diff --check
```

Add tests for logic that does not require a display:

- Cancellation token state and exception.
- Structured progress event delivery.
- Task runner started/progress/completed ordering.
- Cooperative cancellation terminal state.
- UI configuration contains every workflow.
- Icon files have expected formats, dimensions, embedded sizes, and alpha corners.
- Parameter parsers reject empty paths, invalid numbers, empty extension sets, and invalid crop rectangles.

## GUI smoke test

Create a short-lived root using the real project interpreter:

1. Create `Tk` and withdraw it when visual inspection is unnecessary.
2. Construct the application with its default configuration.
3. Call `update_idletasks()`.
4. Assert the expected notebook page count and names.
5. Select every page once.
6. Exercise image preview with a controlled image.
7. Confirm the application icon loads and preserves alpha where relevant.
8. Destroy the app and remove custom logging handlers.

Do not leave a main loop running in automated tests. On systems where creating a window needs GUI permission, request it and keep the window hidden or short-lived.

## Platform verification

### Windows

- Confirm the ICO contains multiple sizes.
- Run from the intended interpreter or packaged executable.
- Inspect title bar, taskbar, Alt-Tab, and dialogs.
- Confirm AppUserModelID prevents grouping under Python when required.

### macOS

- Fully terminate old Python processes before retesting; Dock state belongs to the process.
- Inspect Dock and Command-Tab separately from the title bar.
- Confirm the native title bar has no broken question-mark proxy icon.
- Verify transparent corners in the actual Tk-loaded photo.
- When packaged, inspect the `.app` bundle and `Info.plist` ICNS declaration.

### All platforms

- Start each workflow with no input or a tiny controlled sample.
- Confirm the UI remains responsive during scanning and processing.
- Confirm a second task cannot start.
- Cancel during a multi-item task and verify no next item starts.
- Close during a task and verify shutdown waits for a safe boundary.
- Confirm logs continue to the file and remain bounded in the UI.
- Reload configuration only while idle.

## Layout review

At the default geometry and minimum size, inspect:

- No horizontal clipping or overlapping labels.
- Paths remain usable and Browse buttons visible.
- Notebook and log panel have a small intentional gap.
- Form groups do not gain unexplained blank space.
- Preview maintains aspect ratio and does not expand the window.
- Log font is readable and severity colors remain legible.
- High-DPI scaling does not truncate controls.

## Delivery notes

State what was actually run. Do not imply Windows validation from a macOS-only session or vice versa. Separate:

- Automated cross-platform logic checks.
- Asset format validation.
- Hidden-window smoke testing.
- Manual visual testing on each operating system.

Report the launch command, primary entry/config files, safety semantics, known warnings, current Git branch, and commit/push status.
