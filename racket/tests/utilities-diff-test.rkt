#lang racket/base
;; Item 03: differential checks of compat.rkt and utilities.rkt against the
;; original.  tests/diff/utilities-battery.scm is evaluated twice: by Chez
;; Scheme 10 with chez_scheme/original/ loaded (chez_scheme/oracle/diff-eval.ss),
;; and here, in a namespace made of racket/base + compat.rkt + utilities.rkt.
;; Every line of output (one per test form) must be identical.
(require rackunit
         racket/list
         racket/port
         racket/runtime-path
         racket/string
         racket/system)

(define-runtime-path repo "../..")
(define-runtime-path compat "../compat.rkt")
(define-runtime-path utilities "../utilities.rkt")
(define battery (build-path repo "tests" "diff" "utilities-battery.scm"))
(define diff-eval (build-path repo "chez_scheme" "oracle" "diff-eval.ss"))

(define (chez-output)
  (define scheme (or (find-executable-path "scheme") (find-executable-path "chezscheme")))
  (unless scheme (error 'utilities-diff-test "Chez Scheme not found"))
  (define out (open-output-string))
  (define ok?
    (parameterize ([current-output-port out]
                   [current-directory repo])
      (system* scheme "--script" diff-eval battery)))
  (unless ok? (error 'utilities-diff-test "diff-eval.ss failed:\n~a" (get-output-string out)))
  (get-output-string out))

(define (racket-output)
  (define ns (make-base-empty-namespace))
  (define result (open-output-string))
  (parameterize ([current-namespace ns])
    (namespace-require 'racket/base)
    (namespace-require compat)
    (namespace-require utilities)
    (namespace-set-variable-value!
     'b:capture
     (lambda (thunk)
       (let ([o (open-output-string)])
         (parameterize ([current-output-port o]) (thunk))
         (get-output-string o))))
    (call-with-input-file battery
      (lambda (in)
        (let loop ()
          (define form (read in))
          (unless (eof-object? form)
            (if (and (pair? form) (eq? (car form) 'test))
                (let* ([name (cadr form)]
                       [text (with-handlers ([(lambda (e) #t) (lambda (e) "ERROR")])
                               ((eval 'b:canon) (eval (caddr form))))])
                  (fprintf result "~a => ~a\n" name text))
                (eval form))
            (loop))))))
  (get-output-string result))

;; tests are separated at lines starting "name => "; values may span lines
(define (split-tests text)
  (let loop ([lines (string-split text "\n" #:trim? #f)] [acc '()])
    (cond
      [(null? lines) (reverse acc)]
      [(and (pair? acc) (not (regexp-match? #rx"^[^ ]+ => " (car lines))))
       (loop (cdr lines) (cons (string-append (car acc) "\n" (car lines)) (cdr acc)))]
      [else (loop (cdr lines) (cons (car lines) acc))])))

(define chez (split-tests (chez-output)))
(define rkt (split-tests (racket-output)))

(define test-count
  (with-input-from-file battery
    (lambda ()
      (for/sum ([form (in-port read)])
        (if (and (pair? form) (eq? (car form) 'test)) 1 0)))))

(check-equal? (length (filter (lambda (s) (regexp-match? #rx"^[^ ]+ => " s)) chez))
              test-count
              "Chez printed one result per test")
(check-equal? (length rkt) (length chez) "same number of results")
(for ([c (in-list chez)] [r (in-list rkt)])
  (define name (car (string-split c " => ")))
  (check-equal? r c (format "battery test ~a" name)))
