#lang racket/base
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
;; Ported to Racket, 2026.

;; Entry point: `racket racket/main.rkt` will open the racket/gui window.
;; Item 00 stub: the GUI (racket/gui/) does not exist yet. racket/gui is
;; never required at module level here, so this module loads headless.

(provide metacat-version main)

(define metacat-version "1.2")

(define (main . args)
  (printf "Metacat ~a (Racket port): the GUI is not implemented yet.~%" metacat-version))

(module+ main
  (main))
