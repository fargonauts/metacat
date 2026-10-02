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
;; themes.ss
(pending-variables *themespace*)
;; Called by bridges only with an active theme (none can exist yet):
(pending-procedures check-descriptions conflicts-with-theme? supported-by-theme?)
;; Called on every bridge: early verbatim copies of themes.ss's definitions
;; (pure: no draws, no state), so that bridges can be built and their
;; strength computed before themes.ss is ported (item 10 moves them back).
(define bridge-type->theme-type
  (lambda (theme-type)
    (case theme-type
      (top 'top-bridge)
      (bottom 'bottom-bridge)
      (vertical 'vertical-bridge))))
(define descriptions-affect-themespace?
  (lambda (d1 d2)
    (and (tell d1 'description-type? (tell d2 'get-description-type))
         (not (ignore-descriptions? d1 d2)))))
(define ignore-descriptions?
  (lambda (d1 d2)
    (or (not (tell d1 'relevant?))
        (not (tell d2 'relevant?))
	(and (tell d1 'description-type? plato-object-category)
	     (both-spanning-groups? (tell d1 'get-object) (tell d2 'get-object)))
        (and (tell d1 'description-type? plato-string-position-category)
	     (both-spanning-objects? (tell d1 'get-object) (tell d2 'get-object)))
	(and (eq? (tell d1 'get-descriptor) plato-middle)
	     (eq? (tell d2 'get-descriptor) plato-middle)))))
;; answers.ss's theme phrases compare against themes.ss's abbreviation diff
;; (the "different" relation, which is #f): an early verbatim copy.
(define diff #f)
(define beta 4)
(define bridge-theme-compatibility-sigmoid
  (lambda (x) (sub1 (/ 2 (add1 (exp (* -2 beta x)))))))
;; run.ss: answers.ss calls these when it reports an answer or a snag
(pending-procedures go post-initial-codelets suspend update-everything)
;; justify.ss
(pending-procedures remove-whole/single-concept-mappings compare-rule-clause-lists)
;; trace.ss
(pending-variables *trace*)
(pending-procedures monitor-slipnode-activation-change monitor-new-groups
                    monitor-new-concept-mappings
                    full-workspace-object-name entries
                    monitor-new-rules make-answer-event make-snag-event
                    theme-pattern-entries-equal?)
;; Called by the Workspace's get-real-object (rules.ss, set-translated-rule-
;; information, for every answer): an early verbatim copy of trace.ss's
;; definition (pure: no draws, no state), moved back by item 10.
(define equivalent-workspace-objects?
  (lambda (object1 object2)
    (and (eq? (tell object1 'object-type) (tell object2 'object-type))
         (eq? (tell object1 'which-string) (tell object2 'which-string))
	 (= (tell object1 'get-left-string-pos) (tell object2 'get-left-string-pos))
	 (= (tell object1 'get-right-string-pos) (tell object2 'get-right-string-pos))
	 (if (letter? object1)
	   (same-letter-category? object1 object2)
	   (and (same-group-category? object1 object2)
	        (same-group-direction? object1 object2)
		(= (tell object1 'get-group-length) (tell object2 'get-group-length))
		(andmap equivalent-workspace-objects?
		  (tell object1 'get-constituent-objects)
		  (tell object2 'get-constituent-objects)))))))
;; memory.ss
(pending-variables *memory*)
(pending-procedures abstract-answer-description abstract-snag-description)

;; Graphics (the GUI items)
;; constants.ss, graphics part
(pending-variables %coderack-background-color% %current-codelet-color%
                   %extremely-low-urgency-color% %very-low-urgency-color%
                   %low-urgency-color% %medium-urgency-color% %high-urgency-color%
                   %very-high-urgency-color% %extremely-high-urgency-color%
                   %vertical-slippage-color% %dim-vertical-slippage-color%
                   %coattail-inducing-slippage-color%
                   %dim-coattail-inducing-slippage-color%)
;; general-graphics.ss
(pending-procedures solid-box outline-box arrowhead)
;; Called by make-rule on every rule (transcribe-to-english, rules.ss): an
;; early verbatim copy of general-graphics.ss's definition (pure string
;; code), moved back by the GUI items.
(define find-next-space-position
  (lambda (s i)
    (cond
      ((>= i (string-length s)) (string-length s))
      ((char=? (string-ref s i) #\space) i)
      (else (find-next-space-position s (+ i 1))))))
;; rule-graphics.ss
(pending-procedures initialize-rule-graphics)
;; group-graphics.ss (group-graphics itself is in engine/group-graphics.rktl)
(pending-procedures make-group-pexp draw-group-grope)
(pending-variables %small-group-arrowhead-length% %group-arrowhead-angle%)
;; workspace-graphics.ss: created by set! in the Workspace window's
;; initialisation, never defined (groups.ss reads them in graphics-gated code)
(pending-variables %group-letter-category-font% %relevant-group-length-font%)
;; bridge-graphics.ss
(pending-procedures bridge-graphics draw-bridge-grope new-bridge-label-number
                    make-bridge-pexp)
;; eeg-graphics.ss (the EEG records workspace values for its window)
(pending-variables *EEG*)
;; coderack-graphics.ss
(pending-variables %coderack-codelet-count-font%)
;; gui.ss
(pending-variables %num-of-flashes% %flash-pause% %snag-pause%
                   %codelet-highlight-pause% %text-scroll-pause%)
