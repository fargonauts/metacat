;; Part of the Racket port of Metacat (GPL v2 or later, like Metacat itself).
;;
;; Stand-ins for names that the ported files refer to but that are defined
;; in files not ported yet.  Each item that ports a file deletes its names
;; here; a name left here and also defined by the port is a duplicate
;; definition, which Racket rejects at compile time.  Procedures raise an
;; error when called; variables hold #f, as setup.ss's globals do before
;; (setup).
;;
;; Nothing here runs at load time: in the original these names are
;; referenced only inside procedure bodies by the files ported so far.

(define-syntax-rule (pending-procedures name ...)
  (begin
    (define (name . args) (error 'name "not ported yet")) ...))

(define-syntax-rule (pending-variables name ...)
  (begin (define name #f) ...))
;; run.ss
(pending-variables *display-mode?* *step-mode?* %step-cycles%)
;; workspace.ss
(pending-variables *workspace* %proposed% %evaluated% %built%)
;; workspace-structures.ss
(pending-procedures make-workspace-structure)
;; groups.ss
(pending-procedures contains?)
;; formulas.ss
(pending-procedures temp-adjusted-probability)
;; slipnet.ss
(pending-variables *top-down-slipnodes* plato-bond-category plato-bond-facet)
(pending-procedures fully-active?)
;; themes.ss
(pending-variables *themespace*)
;; trace.ss
(pending-variables *trace*)
;; memory.ss
(pending-variables *memory*)

;; Graphics (the GUI items)
;; constants.ss, graphics part
(pending-variables %coderack-background-color% %current-codelet-color%
                   %extremely-low-urgency-color% %very-low-urgency-color%
                   %low-urgency-color% %medium-urgency-color% %high-urgency-color%
                   %very-high-urgency-color% %extremely-high-urgency-color%)
;; general-graphics.ss
(pending-procedures solid-box)
;; coderack-graphics.ss
(pending-variables %coderack-codelet-count-font%)
;; gui.ss
(pending-variables %num-of-flashes% %flash-pause% %snag-pause%
                   %codelet-highlight-pause% %text-scroll-pause%)
