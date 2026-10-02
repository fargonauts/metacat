;;; run.ss -- run Metacat 1.2 headless under Chez Scheme 10.
;;;
;;; Part of the Racket port of Metacat (GPL v2 or later, like Metacat itself).
;;;
;;;   scheme --script chez_scheme/oracle/run.ss INITIAL MODIFIED TARGET [ANSWER]
;;;          [--seed N] [--max-codelets K] [--keep-going]
;;;
;;; Loads chez_scheme/original/metacat.ss unmodified through prelude.ss, sets
;;; up the problem with the display off (init-mcat, as the Control Panel's
;;; Run button does), runs it (run-mcat) and prints the commentary as it is
;;; written, each answer found, and a summary.  With ANSWER the run is a
;;; justify run.  Without --seed the seed comes from the clock, as in the
;;; original (randomize).
;;;
;;; The original stops (suspend) when it finds an answer or gives up, and
;;; waits for the user to press Go.  By default the oracle ends the run
;;; there; with --keep-going it continues at once, as if Go were pressed,
;;; until K codelets have run.  --max-codelets K uses the original's own
;;; breakpoint (runtil K): the run stops after codelet K.  Without it there
;;; is no cap.
;;;
;;; "codelet N" on an Answer line is *codelet-count* when the answer is
;;; reported, i.e. the answer was found by codelet N+1 (the count the
;;; original displays, and the "time" quoted in demos.ss).

(define $oracle-directory
  (let ((script (car (command-line))))
    (path-parent
      (if (path-absolute? script)
          script
          (string-append (current-directory) "/" script)))))

(load (string-append $oracle-directory "/prelude.ss"))
($install-error-handler!)

(define usage
  (lambda ()
    (display "usage: run.ss INITIAL MODIFIED TARGET [ANSWER] [--seed N] [--max-codelets K] [--keep-going]\n"
             (current-error-port))
    (exit 2)))

(define parse-positive
  (lambda (s)
    (let ((n (string->number s)))
      (if (and n (exact? n) (integer? n) (> n 0)) n (usage)))))

;; Returns (strings seed max-codelets keep-going?)
(define parse-args
  (lambda (args)
    (let loop ((args args) (strings '()) (seed #f) (max #f) (keep? #f))
      (cond
        ((null? args)
         (if (memv (length strings) '(3 4))
             (list (reverse strings) seed max keep?)
             (usage)))
        ((string=? (car args) "--seed")
         (if (null? (cdr args)) (usage)
             (loop (cddr args) strings (parse-positive (cadr args)) max keep?)))
        ((string=? (car args) "--max-codelets")
         (if (null? (cdr args)) (usage)
             (loop (cddr args) strings seed (parse-positive (cadr args)) keep?)))
        ((string=? (car args) "--keep-going")
         (loop (cdr args) strings seed max #t))
        ((and (> (string-length (car args)) 0)
              (char-alphabetic? (string-ref (car args) 0)))
         (loop (cdr args) (cons (string->symbol (car args)) strings) seed max keep?))
        (else (usage))))))

(define options (parse-args (command-line-arguments)))
(define strings (car options))
(define max-codelets (caddr options))
(define keep-going? (cadddr options))

(load-metacat)
(install-headless-windows!)

(define seed
  (or (cadr options)
      (begin (randomize) (random-seed))))

(unless (valid-number? seed)
  (display "run.ss: the seed must be between 1 and 4294967295\n" (current-error-port))
  (exit 2))

;; Commentary is printed as it is written.
(set! $commentary-hook
  (lambda (paragraph) (printf "Comment: ~a~%" paragraph)))

;; Answers: abstract-answer-description is called once per answer, by
;; report-new-answer, with the answer event (answers.ss).
(define answers '())
(let ((original abstract-answer-description))
  (set! abstract-answer-description
    (lambda (answer-event)
      (let ((answer (tell (tell answer-event 'get-answer-string) 'print-name))
            (quality (tell answer-event 'get-quality)))
        (set! answers (append answers (list answer)))
        (printf "Answer: ~a  quality ~a  codelet ~a  temperature ~a~%"
                answer quality *codelet-count* *temperature*))
      (original answer-event))))

;; break and quiet-break (run.ss) wait for the REPL; here they end the run,
;; or with --keep-going return at once, which is what (go) does.
(define stop-run #f)
(define headless-break
  (lambda ()
    (set! *running?* #f)
    (if (and keep-going?
             (not (and *break-time* (= *break-time* *codelet-count*))))
        (begin (set! *running?* #t) 'ignore)
        (stop-run 'stopped))))
(set! break headless-break)
(set! quiet-break headless-break)

(define initial (car strings))
(define modified (cadr strings))
(define target (caddr strings))
(define answer (if (= (length strings) 4) (cadddr strings) #f))

(set! %justify-mode% (and answer #t))
(printf "Problem: ~a -> ~a; ~a -> ~a  seed ~a~%"
        initial modified target (or answer '?) seed)

(call/cc
  (lambda (k)
    (set! stop-run k)
    (init-mcat initial modified target answer seed)
    (set! *break-time* max-codelets)
    (run-mcat)))

(printf "Codelets: ~a~%" *codelet-count*)
(printf "Temperature: ~a~%" *temperature*)
(printf "Answers: ~a~%" (if (null? answers) "none" answers))
(flush-output-port (current-output-port))
(exit 0)
