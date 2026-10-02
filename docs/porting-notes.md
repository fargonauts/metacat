# Porting notes

Every place where the Racket port renames, restructures or modernises the
original (because Racket forces it), and every iteration-order or RNG subtlety
found while porting. One entry per change: original file and definition, what
the port does instead, and why.

## Layout
- The port lives in `racket/` (engine modules directly in the folder, GUI in
  `racket/gui/`). `racket/main.rkt` is the GUI entry point and `racket/cli.rkt`
  the headless one. Chez-isms are collected in `racket/compat.rkt`.
