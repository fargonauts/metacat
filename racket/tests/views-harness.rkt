#lang racket/base
;; Item 13: runs of the engine with the views attached (racket/gui/views.rkt),
;; for racket/tests/workspace-view-test.rkt.  Use one fresh engine
;; (namespace) per call, as for golden-harness.rkt.
;;
;; Part of the Racket port of Metacat (GPL v2 or later, like Metacat itself).
;;
;;   (views-run strings seed cap keep?) -> (values trace stdout): a golden
;;     run with the Workspace window attached; stdout ends with a line
;;     "Workspace view: N items" (the window's display list).
;;   (views-partial-trace) -> the trace up to the error, after views-run raised.
;;   (render-scene name) -> a bitmap of the Workspace window at one point of
;;     a golden run (scenes below).
;;   racket racket/tests/views-harness.rkt NAME OUT.png renders a scene by hand.
(require racket/class
         racket/port
         "../compat.rkt"
         "../utilities.rkt"
         "../engine.rkt"
         "../headless.rkt"
         "../gui/views.rkt")

(provide views-run views-partial-trace render-scene scenes golden-runs)

(define (views-run strings seed cap keep?)
  (define trace (open-output-string))
  (define stdout (open-output-string))
  (define window #f)
  (parameterize ([current-output-port stdout])
    (run-problem strings seed cap keep? trace
                 #:views (lambda () (set! window (attach-workspace-view!)))))
  (values (get-output-string trace)
          (string-append (get-output-string stdout)
                         (format "Workspace view: ~a items\n"
                                 (length (send (tell window 'get-vp) get-items))))))

(define (views-partial-trace) (partial-trace))

;; name, problem, seed, codelet cap, what to show at the end of the run:
;;   window: the Workspace window as the run left it (at the cap, or at the
;;     first answer, drawn by draw-current-answer)
;;   snag-event: the last snag event's Workspace view, as the Temporal
;;     Trace shows it ("Event N: Snag")
;;   answer-description: the first answer's description in the Episodic
;;     Memory (memory.ss's display-workspace)
(define scenes
  '((mrrjjj-513 (abc abd mrrjjj) 1 513 window)
    (mrrjjj-answer (abc abd mrrjjj) 1 10000 window)
    (xyz-snag-event (abc abd xyz) 3852097033 800 snag-event)
    (xyz-answer (abc abd xyz) 3852097033 10000 window)
    (xyz-answer-description (abc abd xyz) 3852097033 10000 answer-description)
    (xyd-justify (abc abd xyz xyd) 1760747975 10000 window)))

(define (render-scene name)
  (define scene (or (assq name scenes) (error 'render-scene "no scene ~a" name)))
  (define window #f)
  (parameterize ([current-output-port (open-output-nowhere)])
    (run-problem (list-ref scene 1) (list-ref scene 2) (list-ref scene 3) #f
                 #:views (lambda () (set! window (attach-workspace-view!)))))
  (case (list-ref scene 4)
    [(window) (void)]
    [(snag-event)
     ;; the event's display (trace.ss) clears the window, then draws its
     ;; Workspace view; the rest of display is for the other panels
     (tell window 'clear)
     (tell (tell *trace* 'get-last-event 'snag) 'display-workspace)]
    [(answer-description) (tell (car (tell *memory* 'get-answers)) 'display-workspace)])
  (window->bitmap window))

(module+ main
  (define args (current-command-line-arguments))
  (send (render-scene (string->symbol (vector-ref args 0))) save-file (vector-ref args 1) 'png))
