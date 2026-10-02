#lang s-exp "engine-lang.rkt"
;;=============================================================================
;; Copyright (c) 1999, 2003 by James B. Marshall
;;
;; This file is part of Metacat.
;;
;; Metacat is based on Copycat, which was originally written in Common
;; Lisp by Melanie Mitchell.
;;
;; Metacat is free software; you can redistribute it and/or modify it under the
;; terms of the GNU General Public License as published by the Free Software
;; Foundation; either version 2 of the License, or (at your option) any later
;; version.
;;
;; Metacat is distributed in the hope that it will be useful, but WITHOUT ANY
;; WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
;; FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
;; details.
;;=============================================================================
;; Ported to Racket, 2026: the model files of metacat.ss's load order, as one
;; module.

;; The engine.  The original loads its files into one global top level, where
;; every definition can refer to every other and any file can set! any
;; global.  Racket modules cannot be mutually recursive, and a module cannot
;; set! a variable it imports, so the port keeps the original's shape: one
;; module that includes the ported files (racket/engine/*.rktl) in the load
;; order of metacat.ss, after compat.rkt and utilities.rkt (syntactic-sugar.ss
;; and utilities.ss, the first two files loaded).  See docs/porting-notes.md,
;; item 04.
;;
;; Names that model files refer to but whose files are not ported yet are
;; defined, for now, in engine/pending.rktl; each item that ports a file
;; deletes its names there (a name defined twice is a compile error).
;;
;; engine-lang.rkt discards the values of module-level expressions, which
;; Chez's top level drops and racket/base would print.

(require racket/include "compat.rkt" "utilities.rkt")

(provide (all-defined-out) set-global!)

(include "engine/constants.rktl")      ; constants.ss (model constants only)
(include "engine/setup.rktl")          ; setup.ss (without setup, enable-resizing)
(include "engine/coderack.rktl")       ; coderack.ss
(include "engine/descriptions.rktl")   ; descriptions.ss
(include "engine/pending.rktl")        ; stand-ins for the files not ported yet

;; (set-global! 'name value): set! one of the engine's global variables from
;; outside the module (a run's driver, the GUI, the tests).  The original's
;; globals are top-level variables anyone may set!; importers of a Racket
;; module may not, so the ones set from outside are listed here.  Listing a
;; variable here also keeps Racket from treating it as a constant.
(define-syntax-rule (global-setter name ...)
  (lambda (sym value)
    (case sym
      [(name) (set! name value)] ...
      [else (error 'set-global! "not a settable engine global: ~s" sym)])))

(define set-global!
  (global-setter
    ;; setup.ss
    *codelet-count* *temperature*
    *workspace-window* *slipnet-window* *coderack-window* *themespace-window*
    *top-themes-window* *bottom-themes-window* *vertical-themes-window*
    *memory-window* *comment-window* *trace-window* *temperature-window*
    *EEG-window* *control-panel*
    %eliza-mode% %justify-mode% %self-watching-enabled% %verbose%
    %workspace-graphics% %slipnet-graphics% %coderack-graphics%
    %codelet-count-graphics% %highlight-last-codelet% %nice-graphics%
    *repl-thread*
    ;; not ported yet (engine/pending.rktl)
    *workspace* *themespace* *trace* *top-down-slipnodes* *display-mode?*))
