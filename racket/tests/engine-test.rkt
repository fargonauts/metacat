#lang racket/base
;; Item 04: the structure of racket/engine.rkt (one module including the
;; ported files; see docs/porting-notes.md).  The model's behaviour is
;; checked against the original by coderack-diff-test.rkt and
;; slipnet-diff-test.rkt.
(require rackunit
         racket/port
         racket/runtime-path)

(define-runtime-path engine-path "../engine.rkt")

;; Loading the engine prints nothing: engine-lang.rkt discards module-level
;; expression values such as the 'done of each define-codelet-procedure*.
(define load-output
  (with-output-to-string
    (lambda ()
      (parameterize ([current-namespace (make-base-namespace)])
        (dynamic-require engine-path #f)))))
(check-equal? load-output "")

(define (engine name) (dynamic-require engine-path name))

;; set-global! sets the listed globals, and only those
(check-equal? (engine '*temperature*) 0)
((engine 'set-global!) '*temperature* 42)
(check-equal? (engine '*temperature*) 42)
((engine 'set-global!) '*temperature* 0)
(check-exn #rx"not a settable engine global" (lambda () ((engine 'set-global!) 'urgency-name 1)))

;; codelet types are module-level variables and top-level values
(check-equal? (length (engine '*codelet-types*)) 27)
(check-eq? (engine 'breaker) (list-ref (engine '*codelet-types*) 26))
(check-eq? ((dynamic-require (build-path engine-path 'up "compat.rkt") 'top-level-value) 'breaker)
           (engine 'breaker))

;; item 05: slipnodes are module-level variables and top-level values, and
;; so are slipnet links, under the names the link macros give them
(define top-level-value (dynamic-require (build-path engine-path 'up "compat.rkt") 'top-level-value))
(check-equal? (length (engine '*slipnet-nodes*)) 59)
(check-eq? (engine 'plato-a) (car (engine '*slipnet-nodes*)))
(check-eq? (top-level-value 'plato-bond-facet) (engine 'plato-bond-facet))
(check-eq? (top-level-value 'a-b-link)
           (car ((dynamic-require (build-path engine-path 'up "utilities.rkt") 'tell)
                 (engine 'plato-a) 'get-lateral-links)))

;; names from files not ported yet raise when called
(check-exn #rx"not ported yet" (lambda () ((engine 'temp-adjusted-probability) 0.5)))

;; the engine never requires racket/gui (CLAUDE.md, TASK.md): loading it
;; into a fresh namespace declares no racket/gui or racket/draw module
(parameterize ([current-namespace (make-base-empty-namespace)])
  (dynamic-require engine-path #f)
  (check-false (module-declared? 'racket/gui/base #f))
  (check-false (module-declared? 'racket/gui #f))
  (check-false (module-declared? 'racket/draw #f)))
