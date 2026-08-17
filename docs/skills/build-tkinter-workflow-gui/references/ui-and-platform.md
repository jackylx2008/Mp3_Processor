# UI, preview, and platform patterns

Read this reference for layout changes, log styling, image previews, window sizing, or Windows/macOS icons.

## Contents

- Compact layout
- Shared actions and state
- Colored logs
- Image preview
- Application icons
- Platform pitfalls

## Compact layout

Use one spacing scale rather than arbitrary values:

```text
outer margin: 8–12 px
group padding: 8–12 px
form row padding: 3–5 px
group gap: 6–10 px
notebook-to-log gap: 4–8 px
```

When whitespace is unexpectedly large, inspect all ancestors. A child can be compact while a weighted parent grid row absorbs the remaining height. Keep form rows unweighted unless a preview or editor intentionally expands.

At the target geometry, call `update_idletasks()` and inspect `winfo_width()`, `winfo_height()`, and sibling coordinates. Do not rely only on requested sizes.

## Shared actions and state

Give each page the same action order: Preview, Start, Cancel. During a task:

- Disable all Start buttons, not only the active page.
- Enable Cancel.
- Keep captured parameters immutable even if form controls remain editable.
- Disable configuration reload.
- Change status immediately to cancelling after a cancel request.

## Colored logs

Use a fixed-width font at a readable size. For a dark panel, start with:

```text
background  #171923
foreground  #f1f1f0
timestamp   #808080
logger      #57c7ff
DEBUG       #9aedfe
INFO        #5af78e
WARNING     #f3f99d
ERROR       #ff5f56
CRITICAL    #ff6ac1
```

Parse the project log formatter into timestamp, level, logger, and message. Color warnings/errors across the message; keep normal informational messages light for readability.

## Image preview

Use `StringVar.trace_add("write", ...)` plus `after(...)` debounce. Resolve relative paths against the stable project root.

Preview algorithm:

1. Check that the path is a file.
2. Open it inside a context manager.
3. Apply `ImageOps.exif_transpose`.
4. Convert to RGBA.
5. Call `thumbnail((max_width, max_height), Image.Resampling.LANCZOS)`.
6. Create `ImageTk.PhotoImage(..., master=widget)`.
7. Assign it to the label and retain it on the page object.
8. Display filename and original pixel dimensions.

Catch `OSError` and `UnidentifiedImageError`. Clear both the image and retained reference on failure.

## Application icons

Start from a high-resolution square master with generous safe margins and readable shapes. For unbundled macOS execution, use real alpha transparency outside rounded corners; a full opaque square will remain square.

Generate and validate:

- PNG: 512×512 RGBA; verify all corner alpha values are zero and center alpha is opaque.
- ICO: include 16, 24, 32, 48, 64, 128, and 256 sizes.
- ICNS: include macOS standard and Retina sizes up to 1024.

Keep a reference to the Tk `PhotoImage` after calling `root.iconphoto`.

### Windows

Before constructing `Tk`, call `SetCurrentProcessExplicitAppUserModelID` through `ctypes.windll.shell32` when the process otherwise appears as Python. After root creation, call `iconbitmap(default=path_to_ico)` and keep `iconphoto` as a fallback.

### macOS

Tk behavior changes by version. Do not use a custom `wm iconbitmap` as an application image on Tk/Aqua; it can create a document proxy or missing-resource question-mark icon in the title bar.

For development execution outside an `.app`, load the PNG with `NSImage` and set `NSApplication.applicationIconImage` through PyObjC when already available or the built-in Objective-C runtime through `ctypes`. Do not add PyObjC solely for this if a small guarded bridge suffices.

For distribution, prefer a real `.app` bundle with the ICNS declared in `Info.plist`. The native macOS title bar normally has no application icon; put branding in the content area if the product explicitly needs visible in-window branding.

## Platform pitfalls

- `iconphoto` may be ignored by older Tk/Aqua builds even when it succeeds without error.
- An image showing a checkerboard may have the pattern baked into RGB rather than real alpha. Inspect mode, alpha extrema, and corner pixels.
- Test the active project interpreter, not whichever system Python appears first on `PATH`.
- Keep platform-specific code behind `sys.platform` checks and catch platform API failures without preventing GUI startup.
- Distinguish runtime script behavior from packaged executable behavior in handoff notes.
