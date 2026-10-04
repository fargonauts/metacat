# racket/gui-tests/: tests that open windows

These two tests need a display. One drives the real control panel through its widgets;
the other builds the standalone program and runs it. They run only on a **virtual**
display (Xvfb). [`../info.rkt`](../info.rkt) lists this folder in `test-omit-paths`, so
a plain `raco test racket/` skips it, and
[`tests/run-tests.sh`](../../tests/run-tests.sh) runs it separately under `xvfb-run`.
The display-free tests are in [`../tests/`](../tests/README.md).

## Running

```bash
env -u WAYLAND_DISPLAY GDK_BACKEND=x11 xvfb-run -a -s "-screen 0 1920x1200x24" \
  raco test racket/gui-tests/*.rkt
```

This is the command `tests/run-tests.sh` uses. Unsetting `WAYLAND_DISPLAY` and forcing
GTK's X11 backend matter: when `WAYLAND_DISPLAY` is set, GTK ignores Xvfb and opens the
windows **on your real screen**. Both tests refuse to start if `WAYLAND_DISPLAY` is set.
(How this was found is in `docs/anomalies_and_quirks.md` and in PROGRESS.md, iteration
16.)

Requirements: `xvfb-run` (Xvfb), `xwininfo` (x11-utils) for `dist-test.rkt`, and
optionally `bwrap` (bubblewrap).

## The tests

| File | What it checks | Time |
| --- | --- | --- |
| `control-panel-test.rkt` | The control panel ([`../gui/gui.rkt`](../gui/gui.rkt)), driven through its own widgets | about 9 s with its first 105 checks; it has had 211 since the Demos checks were added |
| `dist-test.rkt` | The standalone program built by [`make-dist.sh`](../../make-dist.sh) | about 10 s (it includes a 70 MB build in a temporary directory) |

Times are from [`PROGRESS.md`](../../ralph_loops/loop0001/PROGRESS.md) (iterations 16
and 17).

### control-panel-test.rkt

It calls `(setup)`, as `racket racket/main.rkt` does, then works the widgets as a user
would: it types into the command line and sends Enter, clicks Step, Go, Stop and Reset,
moves the speed slider, picks menu items, fills in dialogs and clicks on the Workspace
canvas. Runs made this way must be the golden runs: each one ends at the golden trace's
codelet count with the golden's random-generator state. Its sections:

- **the windows as `setup` made them**: every window is an on-screen frame, the EEG and
  logo are hidden, and no window overlaps the control panel;
- **invalid input** turns the label red and restores it;
- **the speed slider** at Fast gives the original's speed settings;
- **a full run** (`abc abd ijk`, seed 1): Enter initializes the problem and stops at
  codelet 0, Go runs it to the golden's end; printed output and commentary are checked;
- **Save commentary to file**;
- **step mode**, with the step interval set through the Options dialog;
- **a breakpoint**, set through its dialog; then a click on the Workspace resumes the run
  (the original's handler calls `go`);
- **Stop in the middle of a run, then Go**; then **Reset** and a run again (Run 7);
- **the Windows menu** hides and shows a window;
- **self-watching off and on** (the theme windows follow);
- **resizing** the Workspace frame resizes the Workspace;
- **the Demos menu**: every item, submenus included, in gui.ss's order, loads its
  demos.ss problem and seed and is the only item checked.

At the end it hides every window and stops the refresh timer, so the process can exit.

### dist-test.rkt

It runs `make-dist.sh` into a temporary directory, then runs the program from another
empty directory with a minimal environment (only the display variables). When `bwrap` is
installed, the program runs in a sandbox in which the Racket installation
(`/usr/share/racket`, `/usr/lib/x86_64-linux-gnu/racket`), `/home` (and so this
repository) and `/tmp` are empty. This shows the distribution needs none of them.

- The build has `bin/metacat`, `LICENSE`, `README.md` and the original's help text.
- `metacat abc abd xyz --seed 3852097033 --max-codelets 10000 --trace FILE` exits 0,
  prints what `racket/cli.rkt` prints (`Answers: (wyz)`), and writes
  `tests/golden/abc-abd-xyz_3852097033.jsonl` byte for byte.
- `metacat abc abd xyz` without a seed answers.
- Bad arguments exit with status 2 and print the usage.
- `metacat` with no arguments opens the control panel and the other windows (listed with
  `xwininfo`), stays up and writes nothing to stderr. The test then stops it.

Only Linux was built and tested; the sandbox paths are Linux-specific.
