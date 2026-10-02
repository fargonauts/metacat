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
;; *temperature-clamped?* has no definition in the original: init-mcat
;; creates it by set! on the top level (formulas.ss reads it).
(pending-variables *temperature-clamped?*)
(define %update-cycle-length% 15)       ; run.ss's constant (slipnode 'reset)
;; Never defined in the original: bonds.ss's bonds-equal? (itself never
;; called) refers to it.  Under Chez a call would raise "variable
;; same-direction? is not bound"; this raises too.  Not pending on any item.
(define (same-direction? . args)
  (error 'same-direction? "variable same-direction? is not bound"))
;; bridges.ss
(pending-procedures bridge-between? equivalent-workspace-objects?
                    rule-describable-bridge?
                    incompatible-horizontal-CMs? incompatible-vertical-CMs?
                    break-bridge)
;; themes.ss
(pending-variables *themespace*)
;; rules.ss
(pending-procedures verbatim-clause?)
;; trace.ss
(pending-variables *trace*)
(pending-procedures monitor-slipnode-activation-change monitor-new-groups
                    full-workspace-object-name)
;; memory.ss
(pending-variables *memory*)

;; Graphics (the GUI items)
;; constants.ss, graphics part
(pending-variables %coderack-background-color% %current-codelet-color%
                   %extremely-low-urgency-color% %very-low-urgency-color%
                   %low-urgency-color% %medium-urgency-color% %high-urgency-color%
                   %very-high-urgency-color% %extremely-high-urgency-color%)
;; general-graphics.ss
(pending-procedures solid-box outline-box arrowhead)
;; group-graphics.ss (group-graphics itself is in engine/group-graphics.rktl)
(pending-procedures make-group-pexp draw-group-grope)
(pending-variables %small-group-arrowhead-length% %group-arrowhead-angle%)
;; workspace-graphics.ss: created by set! in the Workspace window's
;; initialisation, never defined (groups.ss reads them in graphics-gated code)
(pending-variables %group-letter-category-font% %relevant-group-length-font%)
;; bridge-graphics.ss
(pending-procedures bridge-graphics)
;; eeg-graphics.ss (the EEG records workspace values for its window)
(pending-variables *EEG*)
;; coderack-graphics.ss
(pending-variables %coderack-codelet-count-font%)
;; gui.ss
(pending-variables %num-of-flashes% %flash-pause% %snag-pause%
                   %codelet-highlight-pause% %text-scroll-pause%)
