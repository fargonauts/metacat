# The Qt GUI: inventory and design (loop0003, item 00)

The Qt GUI (`python/metacat/qt/`, `python3 -m metacat.qt`) puts all of Metacat in one
window: a menu bar, a control strip, and every graphics panel as a pane in a fixed
arrangement of nested `QSplitter`s. The panels' drawing code is reused unchanged: each
panel sends the original's Tk canvas commands to a canvas object, and the Qt GUI supplies a
canvas that runs those commands on a `QGraphicsScene`. The engine is frozen, and watching
must never change a run.

This document has two parts:

1. **The inventory** of today's tkinter GUI. It was generated from the live GUI under Xvfb
   by `python/tests/tk_gui_inventory.py` and committed as
   `python/tests/data/tk-gui-inventory.json`. The tables below summarise that JSON.
   `python/tests/test_tk_gui_inventory.py` checks the inventory against `gui.py`'s source.
2. **The single-window design**: the layout, the splitter tree, the View menu and
   `QSettings`, the resize policy, the threading bridge and the canvas backend.

```bash
env -u WAYLAND_DISPLAY xvfb-run -a -s "-screen 0 1920x1200x24" \
    python3 python/tests/tk_gui_inventory.py python/tests/data/tk-gui-inventory.json
```

---

## Part 1. The inventory of the tkinter GUI

These values were captured on a 1920×1200 Xvfb screen at scale 1 (`python3 -m metacat.gui`).
The screen height matters: `select-control-panel-fonts` uses 14/12/10-point fonts on
screens taller than 1024 pixels and 12/10/8-point fonts on smaller ones, so a 1366×768
laptop gets the small set.

### 1.1 The graphics windows

There are eleven graphics windows plus the Logo. Each is a Tk `Toplevel` with one `Canvas`
(`hosts.TkHost`). They are made by `app.setup` in setup.ss's order and placed by
`app.arrange_windows`. The table gives the canvas size in pixels: the toplevel adds the
scrollbars, and SWL's 2-pixel border is counted in the aspect ratios.

| Window (title) | Drawn by (`metacat/gui/…`) | Default canvas | Scrolling | Aspect ratio (Tk `wm aspect`) | At start | Left click | Right click and shift-left click |
|---|---|---|---|---|---|---|---|
| Workspace | `workspace_graphics.py` (`WorkspaceWindow`) | 800×600 | none | 401:301 | shown | `workspace_window_press_handler`: when running, set `*interrupt?*` (stop at the next codelet); in theme-edit mode, raise the dialog; in display mode, restore the current state; otherwise `go` (continue the run) | — |
| Slipnet | `slipnet_graphics.py` | 650×309 | none | 652:311 | shown | — | — |
| Coderack | `coderack_graphics.py` | 230×598 | none | 29:75 | shown | — | — |
| Temperature | `temperature_graphics.py` | 70×175 | none | 24:59 | shown | — | — |
| Temporal Trace | `trace_graphics.py` | 1000×69 (virtual length `*virtual-trace-length*`) | horizontal | — | shown | `trace_window_press_handler`: when not running, select or unselect the event under the mouse and display the Workspace as it was then; in theme-edit mode, raise the dialog | — |
| Commentary | `commentary_graphics.py` on `general_graphics.ScrollableTextWindow` | 300×600 | vertical | — | shown | — | — |
| Episodic Memory | `memory_graphics.py` | 260×400 | vertical | — | shown | `memory_window_press_handler`: when not running, select or unselect an answer, display it, and compare it with the other highlighted answer (commentary "Let's see..."); in theme-edit mode, raise the dialog | — |
| Top Themes | `theme_graphics.py` (`BridgeThemesWindow`, top-bridge) | 600×140 | none | 301:71 | shown | in theme-edit mode only: pick this theme type, then set the clicked theme to +100 (or clear it) | in theme-edit mode only: the same with −100 |
| Bottom Themes | `theme_graphics.py` (bottom-bridge; editable only in justify mode) | 600×140 | none | 301:71 | shown | as Top Themes | as Top Themes |
| Vertical Themes | `theme_graphics.py` (vertical-bridge) | 160×590 | none | 81:296 | shown | as Top Themes | as Top Themes |
| EEG | `eeg_graphics.py` | 900×120 | horizontal | — | **hidden** | — | — |
| Logo | `fonts.py` (`create_mcat_logo`) | 110×80 | — | not resizable | **hidden** | — | — |

Every graphics window is resizable after `enable-resizing`, with a minimum size of 10×10.
The windows with `none` scrolling keep their aspect ratio through `wm aspect`. Every
canvas binds `<Button-1>`, `<Shift-Button-1>`, `<Button-3>` and `<Configure>`.
`sgl.Viewport.mouse_press` sends right clicks and shift-left clicks to the right-press
handler, and plain left clicks to the left-press handler. "—" means the handler is
`nop-event-handler`. **No window reacts to a click on the Slipnet or the Coderack.** Clamps
come from the Options menu and the theme-edit dialog, never from a click on those two
panes. Item 07 should test the bindings that exist.

On resize (Tk's `<Configure>`), the host calls `viewport.configure(w+2, h+2)`. Then
`make-resizable`'s handler recomputes the canvas size and pixel scale for the window's
scrolling mode, and it queues the panel's own `resize` method on the resize-listener
thread, which pauses 250 ms and keeps only the latest request. Every panel has a `resize`
method (the Commentary through `ScrollableTextWindow.resize`). Each redraws at the new size
and recomputes its fonts.

The window positions (`arrange_windows`) are in the JSON. They tile three rows: the
control panel with the Temperature under it, the Workspace, the Coderack and the
Commentary; then the Slipnet, the Top and Bottom Themes stacked, the Vertical Themes and
the Memory; then the Temporal Trace and the EEG. Together they need about 1850×1250 pixels.

### 1.2 The control panel

The title is "Metacat Control Panel". The window is not resizable, and closing it quits the
application (`gui._exit`). From top to bottom:

- a 350×5 top border (a canvas);
- **the info label**: "Please enter a problem:", then the current problem as
  ` abc -> abd; xyz -> ?       seed:  3852097033 `. Errors appear here in red for 700 ms:
  "Invalid input!", "No current problem!", and "Error: …" for an error in the engine;
- **the command line**: an `Entry` 40 characters wide. Enter runs the current
  `command_line_action`;
- **the speed controls**: a slider titled "Speed", with "Slow" and "Fast" at its ends,
  then the buttons **Step**, **Go**, **Stop** and **Reset**;
- **the breakpoint label** (red): "Breakpoint set for time step N";
- **the self-watching warning** (red): "Warning: Self-watching is disabled", shown only
  while self-watching is off.

**What the buttons and Enter do** (gui.ss's actions):

| Control | Empty command line | A valid problem on the command line | Anything else |
|---|---|---|---|
| Go (and Enter) | step mode off, resume the current problem | `init-new-problem` (init, park it with `quiet-break`; the next Go runs it) | "Invalid input!" |
| Step | step mode on, resume | `init-new-problem` in step mode | "Invalid input!" |
| Reset | `reset-current-problem` (re-init with the same seed) | `init-new-problem` | "Invalid input!" |
| Stop | sets `*interrupt?*`; the run breaks after the current codelet | | |

A problem is three or four letter strings and an optional seed. With no seed, the GUI
calls `randomize` and shows the new seed. Resuming with no current problem shows "No
current problem!".

**States** (`states` in the JSON). The panel has three modes, set by messages from the
engine and the dialogs:

| | initial (no problem yet) | input mode | run mode | disabled mode (a dialog is open) | self-watching off (in input mode) |
|---|---|---|---|---|---|
| command line | enabled, empty | enabled, empty, black on azure, left-justified | disabled, shows "running..." in green on black, centred, bold italic | disabled (look unchanged) | enabled |
| Enter | Go | Go | nothing | nothing | Go |
| Step / Go / Reset | **disabled** | enabled | disabled | disabled | enabled |
| Stop | disabled | disabled | enabled | disabled | disabled |
| speed slider | enabled | enabled | enabled | enabled | enabled |
| Demos, Options, Clear Memory | enabled | enabled | disabled | disabled | enabled; Options > Clamp theme pattern, Clamp codelet pattern and Undo last clamp are disabled |
| Help, Windows | enabled | enabled | enabled | enabled | enabled; the three Themes windows are hidden |

In the initial state, Step, Go and Reset are disabled (gui.ss creates them with
`enabled: #f`), so only Enter or a demo starts the first problem. This is the original's
behaviour.

**The speed slider** goes from 0 to 100 and starts at 50, with a length of 80 pixels.
`speed-slider-action` sets the engine's display pauses:

| value | flashes | flash pause (ms) | snag pause (ms) | text scroll pause (ms) |
|---:|---:|---:|---:|---:|
| 0 | 5 | 100 | 5000 | 20 |
| 25 | 4 | 75 | 3750 | 20 |
| 50 | 2 | 50 | 2500 | 20 |
| 75 | 2 | 25 | 1250 | 20 |
| 99 | 2 | 10 | 250 | 20 |
| 100 | 1 | 1 | 1 | 1 |

The codelet highlight pause stays at 100 ms.

### 1.3 The menus

The menu bar is attached to the control panel, in order: **Help** (a command, not a
cascade), **Demos**, **Windows**, **Options**, a disabled blank spacer, and **Clear Memory**
(a command, which turns red when active). On macOS the original moved Help and Clear Memory
into Options. The JSON lists every item with its kind, label, state, colours, font and
action, and the problem of every demo.

- **Help** opens the Help window (see 1.4).
- **Demos**, through `init-new-problem` with a fixed problem and seed. The item clicked is
  highlighted (white background) until the next problem:
  - Run 1 to Run 8 (Marshall's dissertation runs, e.g. "Run 7:  abc -> abd; xyz -> ?" =
    `abc abd xyz 3852097033`);
  - *Answer comparison and reminding*: abc / xyd, abc / wyz, abc / dyz, rst / xyu,
    rst / wyz, rst / uyz, abc / mrrkkk, abc / mrrjjjj, xqc / mrrkkk, xqc / mrrjjjj,
    eqe / baaab, eqe / aaabaaa, eqe / qeeeq, eqe / aaabccc;
  - *Implausible rules*: Figure 5.4 (top), Figure 5.4 (bottom), Figure 5.5 (top),
    Figure 5.5 (bottom);
  - *Poor thematic characterizations*: Figure 5.7, Figure 5.8, Figure 5.10, Figure 5.11;
  - *Other sample runs*: "abc -> cba; mrrjjj -> mmmrrj", "abc -> abd; ijk -> abd",
    "abc -> aabbcc; kkjjii -> ?", "a -> b; z -> ?", "abc -> abd; glz -> ?".
- **Windows**: one item per window controller, titled "Hide X" when the window is shown and
  "Show X" when hidden, in the on or off colour. They cover Workspace, Slipnet, Coderack,
  Temperature, Temporal Trace, Commentary, Episodic Memory, Top Themes, Bottom Themes,
  Vertical Themes, EEG and Logo. Then a separator, **Show all windows** and **Hide all
  windows**.
- **Options**:
  - Set breakpoint… (an input dialog), Clear breakpoint, Step mode interval… (an input
    dialog);
  - check items, all on at start except Verbose mode: Eliza mode, Slipnet graphics,
    Coderack graphics, Show codelet counts, Show last codelet type, Self-watching mode,
    Verbose mode;
  - Clamp theme pattern (the theme-edit dialog); Clamp codelet pattern ▸ Top-down,
    Bottom-up, Rule, Bridge and Group codelet pattern (each needs a current problem: it
    adds a manual clamp event and activates it); Undo last clamp;
  - Commentary font face ▸ serif, serif italic, serif bold, serif bold italic,
    sans-serif …, fancy … (12 items in three groups, each drawn in its own font; the
    current one is highlighted); Commentary font size ▸ tiny 8, small 10, medium 12,
    large 18, larger 24, huge 34;
  - Save commentary to file… (a file dialog).
- **Clear Memory** opens a confirmation dialog.

### 1.4 The dialogs

| Opened by | Title | What it is | Buttons, keys | While open |
|---|---|---|---|---|
| Help | Help | a resizable window with a word-wrapping, read-only `Text` and a scrollbar, holding `help.txt` (102 lines, "Version 1.0: December 2003" first) in Courier | close only | only one; Help again raises it |
| Options > Set breakpoint | Input | "Enter new breakpoint:", an entry pre-filled with the current breakpoint and selected; not resizable; at +20+80 from the control panel | Enter: empty closes; a non-number or a number below 1 shows "Invalid input!" in red for 700 ms; otherwise set `*break-time*`, show the breakpoint label, close | only one |
| Options > Step mode interval | Input | "Enter new step interval:", pre-filled with `%step-cycles%`; at +80+80 | as above, setting `%step-cycles%` | only one |
| Clear Memory | Confirm | "Really delete all answers / from the Episodic Memory?" in red bold, centred; at +20+70 | **Yes** clears the memory and closes; **Cancel** closes | control panel disabled; back to input mode on close |
| Options > Clamp theme pattern | Confirm | yellow, with seven lines of instructions ("To clamp a theme-pattern, click on one or more theme windows…"); at +10+20 | **Clamp Themes** clamps the edited theme types; **Cancel** restores them | control panel disabled; theme-edit mode on (theme windows get the edit colour and accept clicks; clicks on the Workspace, Trace and Memory raise this dialog) |
| Options > Save commentary to file | Save Commentary to File | the platform save dialog (`tkinter.filedialog`) | — | writes the Commentary's lines; a number n stands for n blank lines |
| (errors) | — | not a dialog: the info label in red for 700 ms | — | — |

Closing a dialog from the window manager runs its destroy handler, which behaves like
Cancel.

### 1.5 Keyboard and mouse bindings

The application binds only these (every other key is Tk's default widget behaviour, such as
Tab traversal and editing keys in entries):

| Where | Binding | Does |
|---|---|---|
| control panel command line | `<Return>` | the current command-line action (Go in input mode, nothing otherwise) |
| the two Input dialogs | `<Return>` | validate and apply (see 1.4) |
| every graphics canvas | `<Button-1>`, `<Shift-Button-1>`, `<Button-3>` | the viewport's press handlers (1.1) |
| every graphics canvas | `<Configure>` | the resize protocol (1.1) |

There are no menu accelerators and no global shortcuts.

### 1.6 The control panel's messages

The engine and the panels talk to `*control-panel*` with `tell`. The Qt control panel must
answer the same messages:

- **From the engine thread** (they change widgets, so they must be marshalled to the GUI
  thread): `switch-to-input-mode`, `switch-to-run-mode`, `display-breakpoint-message`,
  `clear-breakpoint-message`, `set-verbose-step-mode`, `engine-error`;
- **queries** (answered from Python state, without touching widgets): `verbose-mode?`,
  `toggle-verbose-mode`, `problem-exists?`, `get-current-problem`,
  `get-command-line-string`, `ready-to-edit?`;
- **from the GUI thread** (menus, dialogs and press handlers): `init-new-problem`,
  `run-new-problem` (demos.ss and `sugar.py` call it too), `resume-current-problem`,
  `reset-current-problem`, `display`, `display-error`, `theme-edit-mode-on`,
  `theme-edit-mode-off`, `edit-theme-type`, `raise-theme-edit-dialog`, `clear-memory`,
  `hide-window`, `raise`, `get-relative-position`, `get-widgets`.

---

## Part 2. The single-window design

### 2.1 The default layout

The window is a `QMainWindow`. At the top are a menu bar and a one-line control strip (a
toolbar-like widget that can't be moved). Below them, the central widget is the splitter
tree. Panes sit in rows. Each row has a fixed-aspect group, whose widths follow from the
row's height, and one pane that takes the rest of the width (the Commentary in the top row,
the Episodic Memory in the middle row). The Vertical Themes goes in the top row: it is tall
and narrow (160×590), like the Coderack, so a tall row gives it the scale of the other
panels. Its two siblings stay together in the middle row.

**1920×1080** (a maximised window, about 1920×1010 of client area; panes 1920×≈930):

```
+--------------------------------------------------------------------------------------------------+
| Help  Demos  View  Options  Memory                                                                |
| Problem: [abc abd xyz 3852097033_________] [Step][Go][Stop][Reset]  Slow [====|====] Fast         |
|  abc -> abd; xyz -> ?   seed: 3852097033      Breakpoint set for time step 500   (warning)        |
+------+-------------------------------------------+------------+--------+-------------------------+
| Temp |                                           |            |        |                         |
| 110  |              Workspace                    |  Coderack  | Vert.  |      Commentary         |
|      |              746 x 560 (4:3)              |  216 x 560 | Themes |      ~670 x 560         |
|      |                                           |            | 153    |                         |
|      |                                           |            |        |                         |
|      |                                           |            |        |                         |
+------+------------------+------------------------+--------+---+--------+-------------------------+
|                         |        Top Themes  602 x 142        |                                  |
|   Slipnet  608 x 290    +-------------------------------------+     Episodic Memory              |
|                         |       Bottom Themes  602 x 142      |       ~700 x 290                 |
+-------------------------+-------------------------------------+----------------------------------+
|  Temporal Trace  1920 x 78  (horizontal scroll)                                                   |
+--------------------------------------------------------------------------------------------------+
   (EEG: below the Trace when shown from the View menu; hidden by default, as today)
```

**1366×768** (client area about 1366×700; panes 1366×≈620; the small control-panel fonts):

```
+------------------------------------------------------------------------------------+
| Help  Demos  View  Options  Memory                                                 |
| [abc abd xyz 3852097033____] [Step][Go][Stop][Reset] Slow[==|==]Fast  abc->abd; .. |
+-----+------------------------------+---------+------+------------------------------+
|Temp |                              |         |Vert. |                              |
| 70  |    Workspace  496 x 372      |Coderack |Themes|     Commentary  ~530 x 372   |
|     |                              |144 x 372| 102  |                              |
|     |                              |         |      |                              |
+-----+---------+--------------------+---------+--+---+------------------------------+
|  Slipnet      |   Top Themes     382 x 90       |   Episodic Memory  ~580 x 186    |
|  390 x 186    +---------------------------------+                                  |
|               |   Bottom Themes  382 x 90       |                                  |
+---------------+---------------------------------+----------------------------------+
| Temporal Trace  1366 x 60                                                          |
+------------------------------------------------------------------------------------+
```

At 1366×768 the control strip puts the problem display on the same line, after the slider,
and elides it if needed. The breakpoint label and the self-watching warning become part of
the status shown there: a red suffix, with the full text in the tooltip.

### 2.2 The splitter tree

```
central: QSplitter(Vertical)                      "rows"      default 60% / 31% / 9%
├── QSplitter(Horizontal)                         "top"
│     Temperature | Workspace | Coderack | Vertical Themes | Commentary
├── QSplitter(Horizontal)                         "middle"
│     Slipnet | QSplitter(Vertical) "themes" [Top Themes / Bottom Themes] | Episodic Memory
└── QSplitter(Vertical)                           "bottom"
      Temporal Trace | EEG (hidden by default)
```

**Default proportions**, computed rather than hard-coded, for whatever size the window has:

1. Split the pane height H (after the handles) into rows of 0.60·H, 0.31·H and 0.09·H. The
   Trace gets at least 50 px.
2. In each row, a fixed-aspect pane gets the width its aspect ratio gives at the row's
   height: Workspace 401:301, Coderack 29:75, Vertical Themes 81:296, Slipnet 652:311, and
   the themes column 301:71 at half the middle row's height. The Temperature gets
   `max(60, 0.06·W)`, because its 24:59 aspect ratio would take too much width at full row
   height (it is letterboxed; see 2.4).
3. The Commentary and the Memory take the rest of their row, at least 200 px. If the rest
   is smaller, all fixed-aspect panes in that row shrink in proportion.
4. The splitters' stretch factors are 0 for the fixed-aspect panes and 1 for the
   Commentary, the Memory and the Trace. When the window grows, the text-like panes take the
   extra space, and the user can drag it elsewhere.

The minimum window size is 1024×600. Minimum pane sizes: 40×40 for each graphics pane and
120 px wide for the Commentary and the Memory. `setChildrenCollapsible(False)` means a drag
can't collapse a pane to zero by accident. Hiding a pane is a View-menu action.

### 2.3 Hiding, showing, saving and resetting

- **View menu** (it replaces Windows): one checkable action per pane, in the Windows menu's
  order: Workspace, Slipnet, Coderack, Temperature, Temporal Trace, Commentary, Episodic
  Memory, Top Themes, Bottom Themes, Vertical Themes, EEG. Then a separator, **Show all
  panes**, **Hide all panes**, a separator, and **Reset layout**. The Logo becomes the
  window icon and Help > About Metacat, not a pane. A checkmark replaces the original's
  "Hide X"/"Show X" titles and on/off colours (a divergence, to be recorded in
  `docs/divergences.md`). Item 06's parity test maps "Hide X"/"Show X" to the action "X"
  and its checked state.
- **Hiding** a pane calls `widget.hide()`. A `QSplitter` gives a hidden child's space to its
  siblings, so the gap closes. When every child of a nested splitter is hidden (for example
  both Themes panes), the splitter hides itself too, and it shows again with its first
  visible child. The engine keeps drawing on a hidden pane's scene, as it keeps drawing on
  a withdrawn Tk window. The view just doesn't paint. **Self-watching off** hides the three
  Themes panes through the same window-controller protocol (`tell(controller, "hide")`), as
  the original hides their windows. The View actions reflect it.
- **Saving.** `QSettings("fargonauts", "metacat-qt")` stores:
  - `layout/version` (an integer, bumped whenever the tree changes, so that an old state
    is ignored);
  - `layout/rows`, `layout/top`, `layout/middle`, `layout/themes` and `layout/bottom`:
    each splitter's `saveState()`;
  - `window/geometry` (`saveGeometry()`);
  - `view/hidden`, the list of hidden pane names.

  The settings are saved on close and 500 ms after the last `splitterMoved` (a single-shot
  timer). They are restored at start-up if the version matches, otherwise the defaults of
  2.2 are used. Tests point `QSettings` at a temporary INI file (`QSettings(path,
  QSettings.IniFormat)`), so they never touch the owner's configuration.
- **View > Reset layout** removes the `layout/*` and `view/hidden` keys, shows the default
  panes (all except the EEG, and except the Themes panes when self-watching is off) and
  recomputes the default sizes of 2.2 for the current window size.

### 2.4 Resize policy per panel

In one window, panes change size all the time. Each Qt pane keeps the original's resize
protocol rather than scaling a picture. The pane's `resizeEvent` does what `TkHost`'s
`<Configure>` does: it calls `viewport.configure(w+2, h+2)` with the canvas size it gives
the panel. `make-resizable`'s handler and the resize-listener thread (250 ms, latest
request wins) are reused unchanged from `general_graphics.py`, so a drag causes one redraw,
not one per pixel. Tk's `wm aspect` has no equivalent for a pane, so the host itself keeps
the aspect ratio for the windows with `none` scrolling. It gives the panel the largest
rectangle of that ratio inside the pane, centred, and fills the margins with the panel's
background colour (letterboxing).

| Pane | Scrolling | Policy |
|---|---|---|
| Workspace | none | original `resize` (fonts and redraw), letterboxed 401:301 |
| Slipnet | none | original `resize`, letterboxed 652:311 |
| Coderack | none | original `resize`, letterboxed 29:75 |
| Temperature | none | original `resize`, letterboxed 24:59, top-aligned (the pane is wider than the thermometer) |
| Top / Bottom / Vertical Themes | none | original `resize`, letterboxed 301:71, 301:71, 81:296 |
| Temporal Trace | horizontal | original `resize`: the canvas is `height × aspect` wide; a horizontal scrollbar when it is wider than the pane |
| EEG | horizontal | as the Trace |
| Commentary | vertical | original `resize` (`ScrollableTextWindow`: the text reflows to the new width); vertical scrollbar |
| Episodic Memory | vertical | original `resize`: the icons are re-laid out; vertical scrollbar |

A pane narrower or shorter than 3 px (hidden, or being collapsed) sends no configure event.
The original's handler ignores such sizes anyway. If the original's protocol turns out to
be too slow for live dragging (item 04 measures it), the fallback for that panel is to
scale the view (`QGraphicsView.fitInView`, keeping the aspect ratio) while dragging and to
run the protocol once on release. That choice would be recorded per panel here.

Resizing redraws only pictures. Fonts and layout feed only the drawing, never the model, so
a run with resizes gives the same trace. Item 04's test checks this with resizes
interleaved.

### 2.5 The threading bridge

The threads are those of the tkinter GUI, with Qt's GUI thread in place of Tk's main thread:

- **The GUI thread** runs `QApplication.exec()` and owns every widget and every
  `QGraphicsScene`.
- **The engine thread** is `metacat.gui.app.EngineThread`, reused as is: the REPL thread.
  Thunks arrive through `gui.thread_break`, and `run.toplevel` parks the run in that
  thread so that Go resumes it, even inside a codelet. `app.py` imports tkinter only inside
  functions, so the Qt GUI can import it.
- **The resize-listener thread** (`general_graphics.start_resize_listener`) runs the
  panels' `resize` methods. For the bridge, it is just another non-GUI thread.

**Canvas commands.** The engine and the resize listener draw by calling `canvas.tcl(*args)`.
The Qt canvas (2.6) keeps a pure-Python display list, guarded by a lock, and updates it
synchronously in the calling thread: it allocates item ids as Tk does, and applies tags,
`move`, `delete`, `raise`, `itemconfigure` and `scale`. It also appends the operation to a
journal. The GUI thread drains the journals of all canvases on a **50 ms `QTimer`** (as
racket/gui does) and applies them to the `QGraphicsScene`s in one batch per refresh. If a
journal holds more operations than the scene has items (at the slider's fast end, where
whole panels are redrawn between refreshes), the GUI thread rebuilds that scene from the
display list instead of replaying the journal. So a fast run costs at most one scene
rebuild per panel per 50 ms.

**Queries.** Some calls need an answer: `bbox` (text measurement on fonts.ss's hidden
canvas, used for layout by the Workspace, the Commentary and others), `canvasx` and
`canvasy` (the mouse handlers), and the scrollbar queries of `make-resizable`. These are
answered **from the display list and font metrics in the calling thread**, without a round
trip:

- text extents come from `QFontMetricsF` on the mapped `QFont` (item 03). Qt 6 dropped
  `QFontDatabase.supportsThreadedFontRendering` (PySide6 6.11 has no such attribute). A
  check on 2026-10-04 with `QT_QPA_PLATFORM=offscreen` gave the same
  `horizontalAdvance("Bond builders")` (85.578125 px for 14 px Helvetica) in the GUI thread
  and in eight worker threads. Item 03 repeats that check as a test, also under xcb.
  Results are cached per (font, string);
- if the platform can't measure off the GUI thread, measurement falls back to a blocking
  call: the engine thread posts a request with a queued signal and waits on a
  `threading.Event` that the GUI thread sets. A blocking call is never made from the GUI
  thread itself: the canvas checks `threading.get_ident()` and answers directly there;
- `canvasx` and `canvasy` read the view's scroll offset, which the GUI thread copies into
  the canvas whenever the view scrolls. Both are only called from the press handlers, which
  run on the GUI thread anyway.

**The control panel.** Messages from the engine that change widgets (1.6) are posted to the
GUI thread with a queued signal and return at once. That is safe, because no caller uses
their value. Queries answer from Python attributes, which the GUI thread updates. Mouse
presses and menu actions run their handlers on the GUI thread, as Tk ran them on its main
thread. Those handlers only send thunks to the engine thread (`thread_break`) or act while
the run is parked (`*running?*` false). For example, the Memory press handler draws a
remembered answer. Their drawing goes straight to the display list and the journal.

**Deadlock rules.** The GUI thread never waits for the engine thread or the resize
listener. It never joins them and never takes a lock that is held across a wait. The
display-list lock is held only for one operation, and never while waiting. A worker blocks
only on the GUI thread, which always runs its event loop. At quit, a flag makes any
pending blocking query return at once, and the engine thread is a daemon. Item 05 tests 50
rapid Go/Stop toggles.

**Display pauses.** The engine's flashes and pauses (`p_flash_pause` and the others) sleep
in the engine thread. A flash shorter than the 50 ms refresh may not show, as in the Racket
port. When the engine parks (an answer, Stop, a breakpoint), the bridge flushes at once,
so the final picture is always complete.

### 2.6 The canvas backend

`qt/canvas.py` has `QtCanvas`, an object with the panel canvas interface: `tcl(*args)`,
`get_background_color()` and `set_background_color_bang(color)`. It has two layers:

1. **The display list** (no Qt, testable without a display): an ordered list of items. Each
   item has an id, a kind (`line`, `rectangle`, `oval`, `arc`, `polygon` or `text`), its
   coordinates, its options (`-fill -outline -width -dash -arrow -smooth -start -extent
   -style -anchor -justify -font -text -state`) and its tags. It implements Tk's semantics
   for the commands the panels send: `create`, `delete`, `move`, `raise`, `itemconfigure`
   (`-state`, `-tags`), `scale`, `bbox`, `canvasx` and `canvasy`. Tag searches work on an
   id, a tag or `all`. Stacking is creation order, and `raise` moves items to the top. The
   exact list of commands and options is item 01's inventory, taken from the code and every
   stream in `python/fixtures/sgl-tcl/` (`create` of lines, rectangles, ovals, arcs,
   polygons and text; `delete`, `move`, `raise`, `itemconfigure`, `scale`, `bbox`, and
   `canvasx`/`canvasy` from the viewport). Item 02's tests replay those streams into this
   layer and into a real tkinter Canvas, and compare normalised display lists and `bbox`
   answers.
2. **The scene** (GUI thread only): one `QGraphicsItem` per display-list item, with z
   values from a counter that follows the stacking order:
   - `QGraphicsRectItem` and `QGraphicsEllipseItem` for rectangles and ovals;
   - `QGraphicsPathItem` for arcs (pieslice, chord, arc) and for smooth lines (Tk's
     quadratic B-splines);
   - `QGraphicsPolygonItem` for polygons;
   - a plain path or line item for lines, with arrowheads;
   - `QGraphicsSimpleTextItem` for text, offset by its anchor and justified line by line.

   Pens use Tk's pixel widths, with flat caps for lines and miter joins for rectangles, and
   no antialiasing by default (Tk's look; a View option can turn it on). Hidden items
   (`-state hidden`) are `setVisible(False)`. Colours come through `colors.py`'s
   `#rrggbb` words, and fonts through the mapping of item 03.

**The inventory (item 01).** `python/tests/data/tk-canvas-commands.json`, made by
`python/tests/tk_canvas_inventory.py` from the code (every `tcl_eval`, `swl_tcl_eval` and
`.tcl` call, read with `ast`), the `sgl-tcl` fixtures and recording canvases in run7 and a
justify run, and checked by `test_tk_canvas_inventory.py`. The whole list:

| Command | Options | Sent by |
|---|---|---|
| `create rectangle` | `-outline -fill -width -dash -state -tags` | code, fixtures, runs |
| `create line` | `-fill -width -dash -tags` | code, fixtures, runs |
| `create oval` | `-outline -fill -width -dash -tags` | code, fixtures, runs |
| `create arc` | `-style -outline -fill -width -dash -start -extent -tags` | code, fixtures, runs |
| `create polygon` | `-outline -fill -width -dash -tags` | code, fixtures, runs |
| `create text` | `-text -anchor -font -fill -tags` | code, fixtures, runs |
| `delete`, `move`, `itemconfigure` (`-state`, `-tags`), `bbox` | | code, fixtures, runs |
| `raise` (`raise TAG all`), `scale` (`scale TAG 0 0 XF YF`) | | code, fixtures (no panel in a run) |
| `canvasx`, `canvasy` | | code (the mouse handlers) |

Values: `-anchor` is `s` (drawn text) or `nw` (measured text); `-style` is `arc` or
`pieslice`; `-state` is `hidden` or `normal`; `-dash` is `""`, `"- "` or `". "`. Tags are
always one word (never a list). `bbox` targets an id, `delete` `all` or a tag,
`itemconfigure` and `move` `all` or a tag. Besides `tcl`, panels call only
`get_background_color` and `set_background_color_bang`. Not in the list, so the Qt canvas
needs none of them: `-arrow`, `-smooth`, `-justify`, `lower`, `coords`, `find`, `gettags`,
`addtag`, window items.

**As built (item 02).** `qt/displaylist.py` is layer 1, with no Qt: `DisplayList.tcl` takes
Tcl words, holds one `RLock` per command, and also answers `find all`, `type`, `coords`,
`itemcget` and `gettags`, which the tests read the display list through. Text extents come
from a measurer (`text_width`, `linespace`, `ascent`). `qt/fonts.py`'s `QtMetrics` measures
with the `QFont` the scene draws with (a first mapping; item 03 completes it). Instead of a
journal, the display list records a set of dirty ids and a "restacked" flag. So `sync()`
(`qt/canvas.py`, GUI thread) costs one update per changed item, however many commands
changed it, and nothing for items that were created and deleted between two syncs. Each
item is a `TkItem` (one `QGraphicsItem` class that paints its kind as X11 does), with z
equal to its stacking position. The background colour is applied at the next `sync()`.
Tk's bbox rules were checked against Tk 8.6.13 on 192 items
(`docs/anomalies_and_quirks.md`, "Tk 8.6.13's bounding boxes, measured"). Colour words
are read as Tk 8.6 reads them.

**The pane** (`qt/hosts.py`): a `QtHost` stands for `hosts.TkHost`, with the same methods
(`make_canvas`, `set_scroll_region_bang`, `get_scrollbar`, `set_vertical_view`,
`show_window`/`hide_window`, `set_title_bang`, …). Its widget is a `QGraphicsView` over
the canvas's scene, in the pane chosen by the window's title, with scrollbars as the
scrolling mode asks. The scene's coordinates are Tk canvas coordinates, one pixel per unit:
the resize protocol redraws, and the view does not scale. `hosts.set_window_host_maker
(qt_host_maker(main_window))` makes `make-graphics-window` create these panes. Mouse
presses map to SWL's modifiers (`left-button`, `shift`+`left-button`, `right-button`) and
go to `viewport.mouse_press`, as in `TkHost._press`. The Logo's `create_mcat_logo` and
fonts.ss's hidden canvas get Qt versions: a `QtCanvas` without a view for measurement, and
the scrollbar sizes from `QStyle.PM_ScrollBarExtent`.

**Fonts** (item 03): a Tk font word `(face size style…)` maps to a `QFont`. The family comes
from the faces `fonts.load()` picked among `QFontDatabase.families()`, lower-cased as SWL
listed them. A negative size is a pixel size (`setPixelSize`). A positive size is in points
at Tk's fixed 96 dpi, so it becomes pixel size `round(size·96/72)`, independent of the
screen. `bold` maps to `QFont.Bold`, `italic` to italic, and `underline` and `overstrike`
map too. Measurement and drawing use the same `QFont`.

*As built (item 03).* `qt/fontspec.py` (no Qt) reads a font word as Tk 8.6's
ParseFontNameObj does: the list form with any number of style words or style lists (later
weight or slant words win, case-sensitive), the `-family -size -weight -slant -underline
-overstrike` form, `TkDefaultFont` (and the other Tk named fonts) as Helvetica −12, size 0
as Tk's default, and Tk's error messages; the canvas checks `-font` with it. Points become
`(int)(points·96/72 + 0.5)` pixels. `qt/fonts.py` measures widths with
`QFontMetrics.horizontalAdvance` (97% of the reference samples equal Tk's `font measure`)
and takes ascent and descent from the ink of the font's printable Latin-1 glyphs
(`QRawFont.boundingRect`, rounded up), because the tkinter GUI's Tk draws with X core
fonts, whose ascent and descent are such ink extents; Qt's own `ascent()` follows the OS/2
win ascent and is up to 7 pixels taller. `families()` lists Qt's families lower-cased,
without Qt's ` [foundry]` suffix, plus the faces of fonts.ss's preference lists that
fontconfig maps onto a real face rather than its generic fallback. So on this machine
`serif` is `times new roman` (Liberation Serif), `sans-serif` `helvetica` (Nimbus Sans) and
`fancy` `palatino linotype` (P052). `install()` makes `metacat/gui/fonts.py` choose its
faces from that list and measure on a `HiddenCanvas` (a `QtCanvas` that drops its change
records at each `delete`). Colours need nothing new: `displaylist.color_rgb` reads all 752
names of `colors.py` exactly as Tk does (`python/tests/test_qt_fonts.py`, reference
`python/tests/data/tk-fonts-colors.json`).

### 2.7 The control strip and menus (item 06)

- **Control strip**, left to right:
  - the command line (`QLineEdit`; Enter = the current command-line action);
  - Step, Go, Stop and Reset (`QPushButton`s, with gui.ss's colours when active);
  - the speed slider ("Slow" `QSlider` "Fast", 0–100, starting at 50, sending
    `gui.speed_slider_action` on every change);
  - the info label (the problem and seed, or a red error for 700 ms), the red breakpoint
    label, and the red self-watching warning.

  The enabled states follow table 1.2 exactly. `switch-to-run-mode` shows "running..." in
  green on black in the command line, as the original does.
- **Menu bar**:
  - **Demos**, built from the same `DEMO_ITEMS` and `demos.py` functions as gui.py;
  - **View** (2.3);
  - **Options**, the same items in the same order, with checkable actions;
  - **Memory**, holding Clear Memory…, because a bare command in a Qt menu bar is unusual;
  - **Help**, holding Metacat Help… (the same `help.txt` in a read-only `QPlainTextEdit`
    window, Courier) and About Metacat (the logo).

  The Save commentary item stays in Options, where gui.ss has it. In run mode Demos,
  Options and Memory are disabled, as Demos, Options and Clear Memory are today.
- **Dialogs**: the Input dialogs are small modeless `QDialog`s with a `QLineEdit`. Enter
  validates them with the same rules and the 700 ms red "Invalid input!". The confirmations
  are modeless `QDialog`s with the original's texts, colours and button labels (Clear
  Memory: Yes and Cancel; theme clamp: Clamp Themes and Cancel). Their destroy handlers
  behave as in gui.py, so closing one acts like Cancel. The save dialog is
  `QFileDialog.getSaveFileName`, replaceable in tests as `gui.set_file_dialog` is today.
- **Keyboard**: Enter on the command line and in the Input dialogs, as today. Qt's
  defaults add Esc to close a dialog and keyboard navigation of the menus. Any shortcut
  beyond these would be a divergence, to be recorded.

### 2.8 Module plan

```
python/metacat/qt/
  __init__.py        imports nothing from Qt at import time; has_pyside6()
  __main__.py        python3 -m metacat.qt [problem…]: main()
  canvas.py          DisplayList (pure Python) and QtCanvas (journal → QGraphicsScene)
  fonts.py           Tk font words → QFont; measurement; the hidden canvas; families
  hosts.py           QtHost (a pane: QGraphicsView + letterboxing + resize + mouse), qt_host_maker
  mainwindow.py      MainWindow: the splitter tree, View menu, QSettings, reset layout
  controls.py        QtControlPanel (the control panel's messages, 1.6), control strip, menus, dialogs
  engine_bridge.py   the 50 ms flush timer, queued messages, blocking queries, quit
python/tests/test_qt_*.py   skip when PySide6 is missing; QT_QPA_PLATFORM=offscreen
```

### 2.9 Notes for the later items

- Item 07 asks for "clamp clicks on the Slipnet, Coderack, Themes, Trace and Memory panes".
  The inventory shows that only the Workspace, the Trace, the Memory and the three Themes
  windows have press handlers. The Slipnet and the Coderack have none, and clamps come from
  the Options menu and the theme-edit dialog. Item 07 should test what exists: Workspace
  continue/interrupt, Trace and Memory selection, theme clicks in theme-edit mode
  (left = +100, right or shift-left = −100), and the menu clamps.
- The Bottom Themes accept edits only in justify mode (`ready-to-edit?`).
- The control-panel fonts depend on the screen height (taller than 1024 px or not). The Qt
  strip should follow the same rule.
- The inventory's slow test regenerates it under Xvfb and compares it with the committed
  JSON, ignoring the keys that hold fonts, since the faces depend on the machine.
