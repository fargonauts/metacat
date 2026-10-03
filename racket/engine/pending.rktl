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


