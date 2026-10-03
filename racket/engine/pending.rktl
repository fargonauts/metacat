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
;; *temperature-clamped?* and *initial-slipnode-unclamp-time* have no
;; definition in the original: init-mcat (run.ss) creates them by set! on
;; the top level (formulas.ss reads the first, run-mcat the second).  Not
;; pending on any item.
(define *temperature-clamped?* #f)
(define *initial-slipnode-unclamp-time* #f)
;; Never defined in the original: bonds.ss's bonds-equal? (itself never
;; called) refers to it.  Under Chez a call would raise "variable
;; same-direction? is not bound"; this raises too.  Not pending on any item.
(define (same-direction? . args)
  (error 'same-direction? "variable same-direction? is not bound"))
;; Never defined in the original: the Temporal Trace's
;; get-complement-codelet-pattern message (trace.ss), never sent, returns
;; it.  Not pending on any item.
(define-syntax complement-codelet-pattern
  (syntax-id-rules ()
    [_ (error 'complement-codelet-pattern
              "variable complement-codelet-pattern is not bound")]))

;; Graphics (the GUI items)
;; trace-graphics.ss: every group event's print name (make-group-event,
;; trace.ss) is made by group-event-pexp-text-string.  An early verbatim
;; copy (pure string code), moved back by the GUI items.
(define group-event-pexp-text-string
  (lambda (group)
    (let* ((bond-facet (tell group 'get-bond-facet))
	   (constituent-objects (tell group 'get-constituent-objects))
	   (descriptors (tell-all constituent-objects 'get-descriptor-for bond-facet))
	   (descriptor-strings
	     (map (lambda (object descriptor)
		    (cond
		      ((platonic-number? descriptor)
		       (format "~a" (platonic-number->number descriptor)))
		      ((letter? object) (tell descriptor 'get-lowercase-name))
		      ((group? object) (tell descriptor 'get-uppercase-name))))
	       constituent-objects
	       descriptors)))
      (apply string-append
	(cons (1st descriptor-strings)
	  (adjacency-map
	    (lambda (x y) (format "-~a" y))
	    descriptor-strings))))))
;; theme-graphics.ss: trace.ss's print-pattern (a debugging printer) names
;; relations with relation-name.  An early verbatim copy (pure), moved back
;; by the GUI items.
(define relation-name
  (lambda (relation)
    (cond
      ((eq? relation #f) "diff")
      ((eq? relation plato-identity) "iden")
      ((eq? relation plato-opposite) "opp")
      ((eq? relation plato-successor) "succ")
      ((eq? relation plato-predecessor) "pred")
      (else #f))))
;; eeg-graphics.ss (the EEG records workspace values for its window)
(pending-variables *EEG*)
;; coderack-graphics.ss
(pending-variables %coderack-codelet-count-font%)
;; gui.ss
(pending-variables %num-of-flashes% %flash-pause% %snag-pause%
                   %codelet-highlight-pause% %text-scroll-pause%)

