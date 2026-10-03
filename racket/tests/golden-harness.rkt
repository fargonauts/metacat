#lang racket/base
;; Item 10: a full run of the port, traced in the golden format.
;;
;; Part of the Racket port of Metacat (GPL v2 or later, like Metacat itself).
;;
;; (golden-trace strings seed cap keep-going?) runs a problem with the engine
;; and returns its JSON-lines trace as a string, as chez_scheme/oracle/run.ss
;; --trace writes it for tests/golden/ (docs/trace-format.md).  It is the
;; Racket counterpart of three pieces of the oracle:
;;   - prelude.ss's headless windows (install-headless-windows!), with the
;;     Commentary window as commentary-graphics.ss's make-comment-window
;;     drawing on a recording text window;
;;   - trace.ss's instrumentation (install-trace!): the same wrappers, set
;;     with the engine's set-global! instead of set!;
;;   - run.ss's driver around a copy of the original run.ss's init-mcat,
;;     run-mcat and update-everything (run.ss is item 11's to port: these
;;     copies are then replaced by the engine's own).
;; Every wrapper only reads model state, so the run is the engine's own.

(require racket/flonum racket/port
         (only-in racket/math nan? infinite?)
         racket/string
         "../compat.rkt"
         "../utilities.rkt"
         "../engine.rkt")

(provide golden-trace golden-partial-trace golden-runs golden-file-name)

;;;---------------------------------------------------------------------------
;;; JSON output (oracle trace.ss, json-*)

(define out #f)                         ; the trace's string port

(define (json-string s p)
  (write-char #\" p)
  (for ([c (in-string s)])
    (cond
      [(char=? c #\") (write-string "\\\"" p)]
      [(char=? c #\\) (write-string "\\\\" p)]
      [(char=? c #\newline) (write-string "\\n" p)]
      [(char=? c #\tab) (write-string "\\t" p)]
      [(char<? c #\space)
       (write-string (string-append "\\u" (string-pad (number->string (char->integer c) 16)))
                     p)]
      [else (write-char c p)]))
  (write-char #\" p))

(define (string-pad s)
  (string-append (make-string (max 0 (- 4 (string-length s))) #\0) s))

(define (json-number x p)
  (cond
    [(and (exact? x) (integer? x)) (write-string (number->string x) p)]
    [(exact? x) (json-string (number->string x) p)]
    [(and (flonum? x) (not (nan? x)) (not (infinite? x)))
     ;; Chez marks subnormals with a precision suffix, 5e-324|1
     (write-string (car (string-split (number->string x) "|" #:trim? #f)) p)]
    [else (json-string (number->string x) p)]))

(define (json-object . pairs) (cons '$object pairs))

(define (json-write v p)
  (cond
    [(eq? v #t) (write-string "true" p)]
    [(eq? v #f) (write-string "false" p)]
    [(eq? v 'null) (write-string "null" p)]
    [(null? v) (write-string "[]" p)]
    [(string? v) (json-string v p)]
    [(symbol? v) (json-string (symbol->string v) p)]
    [(number? v) (json-number v p)]
    [(and (pair? v) (eq? (car v) '$object))
     (write-char #\{ p)
     (for ([pair (in-list (cdr v))] [i (in-naturals)])
       (unless (zero? i) (write-char #\, p))
       (json-string (symbol->string (car pair)) p)
       (write-char #\: p)
       (json-write (cdr pair) p))
     (write-char #\} p)]
    [(list? v)
     (write-char #\[ p)
     (for ([x (in-list v)] [i (in-naturals)])
       (unless (zero? i) (write-char #\, p))
       (json-write x p))
     (write-char #\] p)]
    [else (error 'trace "cannot write ~s as JSON" v)]))

;; One event: {"t":<codelet count>,"ev":<type>, fields...}
(define (emit ev . fields)
  (when out
    (json-write (apply json-object (cons 't *codelet-count*) (cons 'ev ev) fields) out)
    (write-char #\newline out)))

;;;---------------------------------------------------------------------------
;;; Names of model objects (trace.ss's $name, $string-of, $structure-fields)

(define ($name x)
  (cond
    [(not x) 'null]
    [(symbol? x) x]
    [(string? x) x]
    [(number? x) x]
    [(procedure? x)
     (case (tell x 'object-type)
       [(slipnode) (tell x 'get-short-name)]
       [(letter group) (or (tell x 'ascii-name) 'null)]
       [(workspace-string) (tell x 'generic-name)]
       [(concept-mapping) (tell x 'print-name)]
       [else (format "<~a>" (tell x 'object-type))])]
    [else (format "~a" x)]))

(define ($string-of obj) (tell (tell obj 'get-string) 'generic-name))

(define ($structure-fields s)
  (case (tell s 'object-type)
    [(bond)
     (list (cons 'string ($string-of s))
           (cons 'from ($name (tell s 'get-from-object)))
           (cons 'to ($name (tell s 'get-to-object)))
           (cons 'category ($name (tell s 'get-bond-category)))
           (cons 'direction ($name (tell s 'get-direction)))
           (cons 'facet ($name (tell s 'get-bond-facet))))]
    [(group)
     (list (cons 'string ($string-of s))
           (cons 'name ($name s))
           (cons 'category ($name (tell s 'get-group-category)))
           (cons 'direction ($name (tell s 'get-direction)))
           (cons 'facet ($name (tell s 'get-bond-facet)))
           (cons 'objects (map $name (tell s 'get-constituent-objects))))]
    [(bridge)
     (list (cons 'type (tell s 'get-bridge-type))
           (cons 'object1 ($name (tell s 'get-object1)))
           (cons 'object2 ($name (tell s 'get-object2)))
           (cons 'mappings (map $name (tell s 'get-all-concept-mappings))))]
    [(description)
     (let ([object (tell s 'get-object)])
       (list (cons 'string ($string-of object))
             (cons 'object ($name object))
             (cons 'type ($name (tell s 'get-description-type)))
             (cons 'descriptor ($name (tell s 'get-descriptor)))))]
    [(rule)
     (list (cons 'type (tell s 'get-rule-type))
           (cons 'english (tell s 'get-english-transcription)))]
    [else (list (cons 'object ($name s)))]))

(define (emit-structure ev kind s . extra)
  (apply emit ev (cons 'kind kind) (append ($structure-fields s) extra)))

;;;---------------------------------------------------------------------------
;;; Headless windows (prelude.ss, install-headless-windows!)

(define (make-null-window name messages)
  (lambda (self . msg)
    (if (memq (car msg) messages)
        'done
        (error 'headless-window "~s received unexpected message ~s" name msg))))

;; commentary-graphics.ss's comment window (its model part: the eliza and
;; non-eliza paragraphs) on a recording text window that emits each
;; paragraph drawn
(define (make-headless-comment-window)
  (let ([eliza-paragraphs '()]
        [non-eliza-paragraphs '()])
    (lambda msg
      (let ([self (car msg)])
        (record-case (cdr msg)
          (object-type () 'comment-window)
          (new-problem (initial-sym modified-sym target-sym answer-sym)
            (tell self 'add-comment
              (if %justify-mode%
                (list
                  (format "Let's see... \"~a\" changes to \"~a\", and"
                          initial-sym modified-sym)
                  (format " \"~a\" changes to \"~a\".  Hmm..."
                          target-sym answer-sym))
                (list
                  (format "Okay, if \"~a\" changes to \"~a\", what"
                          initial-sym modified-sym)
                  (format " does \"~a\" change to?  Hmm..." target-sym)))
              (if %justify-mode%
                (list
                  (format "Beginning justify run:  \"~a\" changes to \"~a\", and"
                          initial-sym modified-sym)
                  (format " \"~a\" changes to \"~a\"..."
                          target-sym answer-sym))
                (list
                  (format "Beginning run:  If \"~a\" changes to \"~a\", what"
                          initial-sym modified-sym)
                  (format " does \"~a\" change to?" target-sym))))
            'done)
          (add-comment (lines1 lines2)
            (let ([paragraph1 (apply string-append lines1)]
                  [paragraph2 (apply string-append lines2)])
              (set! eliza-paragraphs (cons 1 (cons paragraph1 eliza-paragraphs)))
              (set! non-eliza-paragraphs (cons 1 (cons paragraph2 non-eliza-paragraphs)))
              (emit 'comment (cons 'text (if %eliza-mode% paragraph1 paragraph2)))
              'done))
          (clear ()
            (set! eliza-paragraphs '())
            (set! non-eliza-paragraphs '())
            'done)
          (initialize () (tell self 'clear) 'done)
          (else (error 'headless-window "comment window received unexpected message ~s"
                       msg)))))))

(define (install-headless-windows!)
  (set-global! '%workspace-graphics% #f)
  (set-global! '%slipnet-graphics% #f)
  (set-global! '%coderack-graphics% #f)
  (set-global! '*workspace-window* (make-null-window 'workspace '(garbage-collect caching-on flush)))
  (set-global! '*slipnet-window* (make-null-window 'slipnet '(clear)))
  (set-global! '*coderack-window* (make-null-window 'coderack '(clear)))
  (set-global! '*themespace-window*
               (make-null-window 'themespace
                                 '(erase-all-themes update-thematic-pressure update-graphics
                                   set-theme-graphics-parameters-and-draw garbage-collect)))
  (set-global! '*top-themes-window* (make-null-window 'top-themes '()))
  (set-global! '*bottom-themes-window* (make-null-window 'bottom-themes '()))
  (set-global! '*vertical-themes-window* (make-null-window 'vertical-themes '()))
  (set-global! '*memory-window*
               ;; add-memory-icon gives each answer or snag description its
               ;; icon drawing procedures (memory-graphics.ss), which memory.ss
               ;; calls even when nothing is displayed; here they draw nothing
               (let ([null-window (make-null-window 'memory '(draw))])
                 (lambda (self . msg)
                   (case (car msg)
                     [(add-memory-icon)
                      (tell (cadr msg) 'set-graphics-info (lambda (activation) 'no-icon) 'no-icon)
                      'done]
                     [else (apply null-window self msg)]))))
  ;; the Trace window records the Temporal Trace's events (trace.ss)
  (set-global! '*trace-window*
               (let ([window (make-null-window 'trace '(initialize add-event))])
                 (lambda (self . msg)
                   (when (eq? (car msg) 'add-event)
                     (let ([event (cadr msg)])
                       (emit 'event
                             (cons 'type (tell event 'get-type))
                             (cons 'number (tell event 'get-event-number))
                             (cons 'name (tell event 'print-name))
                             (cons 'time (tell event 'get-time))
                             (cons 'temperature (tell event 'get-temperature)))))
                   (apply window self msg))))
  (set-global! '*temperature-window* (make-null-window 'temperature '(initialize update-graphics)))
  (set-global! '*EEG-window* (make-null-window 'EEG '(initialize)))
  ;; eeg-graphics.ss's EEG object (not ported yet): a headless run only
  ;; initializes it (the Workspace's initialize); recording is gated by
  ;; %workspace-graphics%, and the model never reads it
  (set-global! '*EEG* (make-null-window 'EEG-object '(initialize)))
  (let ([coderack-graphics (make-null-window 'coderack-graphics '(set-last-codelet-type))])
    (for-each
      (lambda (type)
        (tell type 'set-graphics-parameters coderack-graphics #f #f #f #f #f #f #f #f))
      *codelet-types*))
  (set-global! '*control-panel*
               (lambda (self . msg)
                 (case (car msg)
                   ;; as in gui.ss with the verbose checkbox off
                   [(set-verbose-step-mode) (set-global! '%verbose% (cadr msg)) 'done]
                   [else (error 'headless-window "control panel received unexpected message ~s"
                                msg)])))
  (set-global! '*comment-window* (make-headless-comment-window)))

;;;---------------------------------------------------------------------------
;;; The trace's wrappers (trace.ss, install-trace!), installed once around
;;; the engine's own procedures and objects

(define last-themes #f)
(define answers '())
(define stop-run #f)

(define originals #f)

(define (install-trace!)
  (unless originals
    (set! originals
          (list *coderack* build-bond break-bond build-group break-group build-bridge
                break-bridge build-description *workspace* update-temperature
                update-slipnet-activations abstract-answer-description)))
  (define-values (coderack o-build-bond o-break-bond o-build-group o-break-group
                  o-build-bridge o-break-bridge o-build-description workspace
                  o-update-temperature o-update-slipnet-activations
                  o-abstract-answer-description)
    (apply values originals))
  ;; Codelets: the coderack hands out the next codelet in step-mcat.
  (set-global! '*coderack*
               (lambda msg
                 (let ([result (apply coderack coderack (cdr msg))])
                   (when (eq? (cadr msg) 'choose-codelet)
                     (emit 'codelet
                           (cons 'type (tell result 'get-codelet-type-name))
                           (cons 'urgency (tell result 'get-relative-urgency))
                           (cons 'posted (tell result 'get-time-stamp))
                           (cons 'rng (random-seed))))
                   result)))
  ;; Structures built and broken (emitted on entry, before the change).
  (set-global! 'build-bond (lambda (bond) (emit-structure 'build 'bond bond) (o-build-bond bond)))
  (set-global! 'break-bond (lambda (bond) (emit-structure 'break 'bond bond) (o-break-bond bond)))
  (set-global! 'build-group
               (lambda (group flipped?)
                 (emit-structure 'build 'group group (cons 'flipped flipped?))
                 (o-build-group group flipped?)))
  (set-global! 'break-group
               (lambda (group) (emit-structure 'break 'group group) (o-break-group group)))
  (set-global! 'build-bridge
               (lambda (orientation bridge)
                 (emit-structure 'build 'bridge bridge)
                 (o-build-bridge orientation bridge)))
  (set-global! 'break-bridge
               (lambda (bridge) (emit-structure 'break 'bridge bridge) (o-break-bridge bridge)))
  (set-global! 'build-description
               (lambda (d) (emit-structure 'build 'description d) (o-build-description d)))
  ;; Rules are built through the workspace's add-rule.
  (set-global! '*workspace*
               (lambda msg
                 (when (eq? (cadr msg) 'add-rule)
                   (emit-structure 'build 'rule (caddr msg)))
                 (apply workspace workspace (cdr msg))))
  ;; Temperature, after each update.
  (set-global! 'update-temperature
               (lambda ()
                 (o-update-temperature)
                 (emit 'temperature
                       (cons 'value *temperature*)
                       (cons 'clamped *temperature-clamped?*))))
  ;; Slipnet activations and Themespace state, after each slipnet update.
  (set-global! 'update-slipnet-activations
               (lambda ()
                 (o-update-slipnet-activations)
                 (emit 'slipnet
                       (cons 'activations (map (lambda (n) (tell n 'get-activation))
                                               *slipnet-nodes*))
                       (cons 'rng (random-seed)))
                 ;; themes only when different from the last themes event
                 (let* ([state (tell *themespace* 'get-complete-state)]
                        [fields
                         (list (cons 'active (cadr state))
                               (cons 'themes
                                     (map (lambda (info)
                                            (list (car info) ($name (cadr info))
                                                  ($name (caddr info))
                                                  (cadddr info) (car (cddddr info))))
                                          (caddr state))))])
                   (unless (equal? fields last-themes)
                     (set! last-themes fields)
                     (apply emit 'themes fields)))))
  ;; Answers: report-new-answer calls abstract-answer-description once per
  ;; answer (run.ss collects them for the summary).
  (set-global! 'abstract-answer-description
               (lambda (answer-event)
                 (let ([answer (tell (tell answer-event 'get-answer-string) 'print-name)])
                   (set! answers (append answers (list answer)))
                   (emit 'answer
                         (cons 'answer answer)
                         (cons 'quality (tell answer-event 'get-quality))
                         (cons 'temperature *temperature*)))
                 (o-abstract-answer-description answer-event)))
  ;; The original halting on a message an object does not understand: run.ss
  ;; prints it and ends the run.
  (set-report-error-and-halt!
   (lambda (message object)
     (emit 'halt
           (cons 'message (cadr message))
           (cons 'object (tell object 'object-type)))
     (stop-run 'halt))))

;;;---------------------------------------------------------------------------
;;; run.ss (the original's), copied: item 11 ports it into the engine.
;;; Globals are set with set-global!; the driver's break ends the run.

(define %initial-slipnode-clamp-cycles% 50)
(define %garbage-collect-cycles% 100)
(define *initial-slipnode-unclamp-time* 0)
(define *break-time* #f)
(define keep-going? #f)

;; run.ss's break, as chez_scheme/oracle/run.ss's headless-break: the run
;; ends, or with keep-going continues as (go) would
(define (break)
  (if (and keep-going? (not (and *break-time* (= *break-time* *codelet-count*))))
      'ignore
      (stop-run (if (and *break-time* (= *break-time* *codelet-count*)) 'cap 'suspend))))

(define (suspend) (break))

(define (run-mcat)
  (let loop ()
    (step-mcat)
    (when (= *codelet-count* *initial-slipnode-unclamp-time*)
      (say "Unclamping initially-clamped slipnodes...")
      (for-each (lambda (node) (tell node 'unfreeze)) *initially-clamped-slipnodes*))
    (when (tell *coderack* 'empty?)
      (post-initial-codelets)
      (clamp-initial-slipnodes))
    (when (= 0 (modulo *codelet-count* %update-cycle-length%))
      (update-everything))
    (when (and *break-time* (= *break-time* *codelet-count*))
      (update-all-graphics)
      (break))
    (when (= 0 (modulo *codelet-count* %garbage-collect-cycles%))
      (tell *themespace-window* 'garbage-collect)
      (tell *workspace-window* 'garbage-collect))
    (loop)))

(define (step-mcat)
  (let ([codelet (tell *coderack* 'choose-codelet)])
    (tell codelet 'run)
    (set-global! '*codelet-count* (+ 1 *codelet-count*))
    'done))

(define (init-mcat initial-sym modified-sym target-sym answer-sym seed)
  (set-global! '*display-mode?* #f)
  ;; step-mode-off
  (tell *control-panel* 'set-verbose-step-mode #f)
  (random-seed seed)
  (set-global! '*this-run*
               (if %justify-mode%
                   (list initial-sym modified-sym target-sym answer-sym seed)
                   (list initial-sym modified-sym target-sym seed)))
  (tell *coderack* 'initialize)
  (set-global! '*codelet-count* 0)
  (set! *initial-slipnode-unclamp-time* 0)
  (set-global! '*temperature* 100)
  (set-global! '*temperature-clamped?* #f)
  (for-each (lambda (node) (tell node 'reset)) *slipnet-nodes*)
  (tell *temperature-window* 'initialize)
  (tell *temperature-window* 'update-graphics 100)
  (tell *EEG-window* 'initialize)
  (tell *slipnet-window* 'clear)
  (tell *coderack-window* 'clear)
  (tell *comment-window* 'clear)
  (tell *trace* 'initialize)
  (tell *memory* 'clear-activations)
  (tell *memory* 'unhighlight-all-answers)
  (tell *themespace* 'initialize)
  (init-workspace initial-sym modified-sym target-sym answer-sym)
  (add-string-position-descriptions-to-letters *initial-string*)
  (add-string-position-descriptions-to-letters *modified-string*)
  (add-string-position-descriptions-to-letters *target-string*)
  (when %justify-mode%
    (add-string-position-descriptions-to-letters *answer-string*))
  (when (or (= (tell *initial-string* 'get-length) 1)
            (= (tell *modified-string* 'get-length) 1)
            (= (tell *target-string* 'get-length) 1)
            (and %justify-mode% (= (tell *answer-string* 'get-length) 1)))
    (tell plato-object-category 'set-activation %max-activation%))
  (for-each
    (lambda (obj)
      (for-each (lambda (descriptor) (tell descriptor 'set-activation %max-activation%))
        (tell-all (tell obj 'get-descriptions) 'get-descriptor)))
    (tell *workspace* 'get-objects))
  (update-workspace-values)
  (clamp-initial-slipnodes)
  (post-initial-codelets))

(define (init-workspace initial-sym modified-sym target-sym answer-sym)
  ;; Chez evaluates let's inits last first
  (let* ([answer-string (if %justify-mode% (make-workspace-string 'answer answer-sym) #f)]
         [target-string (make-workspace-string 'target target-sym)]
         [modified-string (make-workspace-string 'modified modified-sym)]
         [initial-string (make-workspace-string 'initial initial-sym)])
    (tell *workspace* 'initialize initial-string modified-string target-string answer-string)
    (set-global! '*initial-string* initial-string)
    (set-global! '*modified-string* modified-string)
    (set-global! '*target-string* target-string)
    (set-global! '*answer-string* answer-string)
    (set-global! '*top-strings* (list *initial-string* *modified-string*))
    (set-global! '*bottom-strings* (list *target-string* *answer-string*))
    (set-global! '*vertical-strings* (list *initial-string* *target-string*))
    (set-global! '*non-answer-strings* (list *initial-string* *modified-string* *target-string*))
    (set-global! '*all-strings*
                 (list *initial-string* *modified-string* *target-string* *answer-string*))
    (tell *comment-window* 'new-problem initial-sym modified-sym target-sym answer-sym)))

(define (clamp-initial-slipnodes)
  (for-each (lambda (node) (tell node 'clamp %max-activation%)) *initially-clamped-slipnodes*)
  (set! *initial-slipnode-unclamp-time*
        (+ *codelet-count* (* %initial-slipnode-clamp-cycles% %update-cycle-length%))))

(define (post-initial-codelets)
  (for ([i (in-range (* 2 (length (tell *workspace* 'get-objects))))])
    (tell *coderack* 'add-deferred-codelet
      (tell bottom-up-bond-scout 'make-codelet %very-low-urgency%))
    (tell *coderack* 'add-deferred-codelet
      (tell bottom-up-bridge-scout 'make-codelet %very-low-urgency%)))
  (tell *coderack* 'post-deferred-codelets))

(define (add-string-position-descriptions-to-letters string)
  (let* ([string-length (tell string 'get-length)]
         [leftmost-letter (tell string 'get-letter 0)])
    (if (= string-length 1)
        (tell leftmost-letter 'new-description plato-string-position-category plato-single)
        (let ([rightmost-letter (tell string 'get-letter (sub1 string-length))])
          (tell leftmost-letter 'new-description plato-string-position-category plato-leftmost)
          (tell rightmost-letter 'new-description plato-string-position-category plato-rightmost)
          (when (odd? string-length)
            (let ([middle-letter (tell string 'get-letter (scheme-truncate (/ string-length 2)))])
              (tell middle-letter 'new-description
                plato-string-position-category plato-middle)))))))

(define (update-everything)
  (tell *workspace* 'check-if-rules-possible)
  (update-workspace-values)
  (when (tell *trace* 'within-snag-period?)
    (let ([progress-achieved (tell *trace* 'progress-since-last-snag)])
      (stochastic-if* (% progress-achieved)
        (tell *trace* 'undo-snag-condition))))
  (when (tell *trace* 'clamp-period-expired?)
    (tell *trace* 'undo-last-clamp))
  (tell *workspace* 'spread-activation-to-themespace)
  (tell *themespace* 'spread-activation)
  (update-slipnet-activations)
  (update-temperature)
  (add-bottom-up-codelets)
  (add-top-down-codelets)
  (tell *coderack* 'post-deferred-codelets)
  (update-all-graphics))

(define (update-workspace-values)
  (for-each (lambda (structure) (tell structure 'update-strength))
    (tell *workspace* 'get-structures))
  (let ([objects (tell *workspace* 'get-objects)])
    (for-each (lambda (object) (tell object 'update-raw-importance)) objects)
    (tell *initial-string* 'update-all-relative-importances)
    (tell *modified-string* 'update-all-relative-importances)
    (tell *target-string* 'update-all-relative-importances)
    (when %justify-mode%
      (tell *answer-string* 'update-all-relative-importances))
    (for-each (lambda (object) (tell object 'update-object-values)) objects))
  (tell *initial-string* 'update-average-intra-string-unhappiness)
  (tell *modified-string* 'update-average-intra-string-unhappiness)
  (tell *target-string* 'update-average-intra-string-unhappiness)
  (when %justify-mode%
    (tell *answer-string* 'update-average-intra-string-unhappiness))
  (tell *workspace* 'update-average-unhappiness-values))

;; the graphics switches are off
(define (update-all-graphics) 'done)

;;;---------------------------------------------------------------------------
;;; The driver (chez_scheme/oracle/run.ss)

(define installed? #f)

;; the trace up to the error, after golden-trace raised
(define partial-trace #f)
(define (golden-partial-trace) partial-trace)

;; strings: 3 or 4 symbols; returns the trace as a string
(define (golden-trace strings seed cap keep?)
  (unless installed?
    (install-headless-windows!)
    (install-trace!)
    (set-global! 'suspend suspend)
    (set-global! 'update-everything update-everything)
    (set-global! 'post-initial-codelets post-initial-codelets)
    (set! installed? #t))
  (set! out (open-output-string))
  (set! last-themes #f)
  (set! answers '())
  (set! keep-going? keep?)
  (set! *break-time* #f)
  (define initial (car strings))
  (define modified (cadr strings))
  (define target (caddr strings))
  (define answer (if (= (length strings) 4) (cadddr strings) #f))
  (emit 'start
        (cons 'format 1)
        (cons 'problem (append strings (if (= (length strings) 3) '(null) '())))
        (cons 'seed seed)
        (cons 'max_codelets (or cap 'null))
        (cons 'keep_going keep?)
        (cons 'slipnodes (map $name *slipnet-nodes*)))
  (set-global! '%justify-mode% (and answer #t))
  (define reason
    (let/ec k
      (set! stop-run k)
      (parameterize ([current-output-port (open-output-nowhere)])
        ;; a Racket error (the original's Chez errors) ends the run; the
        ;; trace so far is kept for golden-partial-trace
        (with-handlers ([exn:fail? (lambda (e)
                                     (set! partial-trace (get-output-string out))
                                     (set! out #f)
                                     (raise e))])
          (init-mcat initial modified target answer seed)
          (set! *break-time* cap)
          (run-mcat)))))
  (emit 'end
        (cons 'reason reason)
        (cons 'temperature *temperature*)
        (cons 'answers answers)
        (cons 'rng (random-seed)))
  (begin0 (get-output-string out)
          (set! out #f)))

;;;---------------------------------------------------------------------------
;;; tests/problems.txt (chez_scheme/oracle/make-golden.ss's reading of it)

(define (golden-file-name strings seed)
  (format "~a_~a.jsonl" (string-join (map symbol->string strings) "-") seed))

;; every run: (list file-name strings seed cap keep-going?)
(define (golden-runs problems-file)
  (apply append
    (for/list ([line (in-list (call-with-input-file problems-file
                                (lambda (in) (for/list ([l (in-lines in)]) l))))]
               #:unless (null? (string-split (regexp-replace #rx"#.*$" line ""))))
      (define fields (map string-split (string-split (regexp-replace #rx"#.*$" line "")
                                                     "|" #:trim? #f)))
      (define strings (map string->symbol (car fields)))
      (define seeds (map string->number (cadr fields)))
      (define cap (string->number (car (caddr fields))))
      (define keep? (and (= (length fields) 4) (equal? (cadddr fields) '("keep-going"))))
      (for/list ([seed (in-list seeds)])
        (list (golden-file-name strings seed) strings seed cap keep?)))))
