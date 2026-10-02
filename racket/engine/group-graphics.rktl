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
;; Ported to Racket, 2026: included by racket/engine.rkt (see docs/porting-notes.md,
;; items 04 and 07).  Changes are marked port:.
;;=============================================================================

;; port: only group-graphics, for now.  groups.ss calls it ungated (in
;; group-builder, (group-graphics 'erase proposed-group) when it consolidates
;; sameness groups), so a headless run needs it; it only sends messages to
;; *workspace-window*.  The rest of group-graphics.ss (the pexp builders, the
;; constants) comes with the Workspace panel.

(define group-graphics
  (lambda (op group)
    (let ((proposal-level (tell group 'get-proposal-level)))
      (tell *workspace-window* 'caching-on)
      (case op
	(flash
	  (if (tell group 'drawn?)
	    (tell *workspace-window* 'flash (tell group 'get-graphics-pexp))
	    (let ((drawn-group (tell group 'get-drawn-coincident-group)))
	      (if* (and (exists? drawn-group)
		        (= proposal-level (tell drawn-group 'get-proposal-level)))
		(tell *workspace-window* 'flash (tell drawn-group 'get-graphics-pexp))))))
	(set-pexp-and-draw
	  (tell group 'set-graphics-pexp (make-group-pexp group proposal-level))
	  (let ((drawn-group (tell group 'get-drawn-coincident-group)))
	    (if* (not (exists? drawn-group))
	      (tell *workspace-window* 'draw-group group))))
	(erase
	  (if* (tell group 'drawn?)
	    (tell *workspace-window* 'erase-group group)
	    ;; Repair damage to any overlapping groups:
	    (for* each g in (tell group 'get-drawn-overlapping-groups) do
	      (tell *workspace-window* 'draw-group g))
	    (let ((pending-group (tell group 'get-highest-level-coincident-group)))
	      (if* (exists? pending-group)
		(tell *workspace-window* 'draw-group pending-group)))))
	(update-level
	  (let ((new-pexp (make-group-pexp group proposal-level)))
	    (if (tell group 'drawn?)
	      (begin
		(tell *workspace-window* 'erase (tell group 'get-graphics-pexp))
		(tell group 'set-graphics-pexp new-pexp)
		(tell *workspace-window* 'draw-group group))
	      (begin
		(tell group 'set-graphics-pexp new-pexp)
		(let ((drawn-group (tell group 'get-drawn-coincident-group)))
		  (cond
		    ((not (exists? drawn-group))
		     (tell *workspace-window* 'draw-group group))
		    ((> proposal-level (tell drawn-group 'get-proposal-level))
		     (tell *workspace-window* 'erase-group drawn-group)
		     (tell *workspace-window* 'draw-group group)))))))))
      (tell *workspace-window* 'flush)
      'done)))
