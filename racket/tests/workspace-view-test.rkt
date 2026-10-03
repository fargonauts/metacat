#lang racket/base
;; Item 13: the Workspace view (racket/gui/views.rkt: workspace-graphics.ss,
;; general-graphics.ss's windows, with the engine's group-, bridge- and
;; rule-graphics.ss) attached to runs.
;;
;; 1. Watching changes nothing: every golden run of tests/problems.txt, run
;;    with the Workspace window attached (workspace graphics on, as in the
;;    original program), gives a trace identical to tests/golden/, and the
;;    window was drawn into.  The run on which the original crashes crashes
;;    at the same point with the view attached.
;; 2. Pictures: the Workspace window at six points of golden runs
;;    (racket/tests/views-harness.rkt's scenes: mid-run, answers, a snag
;;    event's view, an answer description, a justify run) must equal
;;    racket/tests/snapshots/workspace-<scene>.png pixel for pixel.
;;    METACAT_UPDATE_SNAPSHOTS=1 rewrites them; a mismatch writes
;;    /tmp/workspace-<scene>-actual.png.  By hand:
;;      racket racket/tests/views-harness.rkt SCENE OUT.png
;; 3. views.rkt needs racket/draw but never loads racket/gui.
;;
;; Part of the Racket port of Metacat (GPL v2 or later, like Metacat itself).
(require rackunit
         compiler/cm
         racket/class
         racket/file
         racket/runtime-path
         racket/string
         (only-in racket/draw read-bitmap)
         "golden-pool.rkt")

(define-runtime-path harness "views-harness.rkt")
(define-runtime-path golden-harness "golden-harness.rkt")
(define-runtime-path problems "../../tests/problems.txt")
(define-runtime-path golden-dir "../../tests/golden")
(define-runtime-path snapshot-dir "snapshots")

(module+ test
  (define runs (load-golden-runs harness problems))
  (check-equal? (length runs) 109)
  (define results (run-golden-runs harness 'views-run runs golden-dir))
  (check-equal? (length results) (length runs))
  (define total-items 0)
  (for ([result (sort results string<? #:key car)])
    (define name (car result))
    (cond
      [(not (caddr result)) (fail (format "~a: the run raised with the view attached: ~a"
                                          name (cadr result)))]
      [else
       (define d (first-difference (cadr result) (file->string (build-path golden-dir name))))
       (if d
           (fail (format "~a: with the view attached, traces differ at line ~a\n  golden: ~a\n  port:   ~a"
                         name (car d) (short (caddr d)) (short (cadr d))))
           (check-true #t))
       (define items (regexp-match #rx"Workspace view: ([0-9]+) items\n$" (list-ref result 3)))
       (check-true (and items (> (string->number (cadr items)) 20) #t)
                   (format "~a: the Workspace window was drawn into" name))
       (when items (set! total-items (+ total-items (string->number (cadr items)))))]))
  (check-true (> total-items 10000) "the views drew"))

;; The original's crash (abc ccbbaa ijk, seed 3: golden-test.rkt) happens at
;; the same point with the view attached.
(module+ test
  (define (crash-trace file run-name partial-name)
    (parameterize ([current-namespace (make-base-namespace)])
      ;; through the compilation manager: the harness may not be compiled yet
      (define-values (run partial)
        (parameterize ([current-load/use-compiled
                        (make-compilation-manager-load/use-compiled-handler)])
          (values (dynamic-require file run-name) (dynamic-require file partial-name))))
      (with-handlers ([exn:fail? (lambda (e) (values (exn-message e) (partial)))])
        (run '(abc ccbbaa ijk) 3 10000 #f)
        (values #f #f))))
  (define-values (plain-error plain-trace)
    (crash-trace golden-harness 'golden-run 'golden-partial-trace))
  (define-values (view-error view-trace)
    (crash-trace harness 'views-run 'views-partial-trace))
  (check-true (and view-error (regexp-match? #rx"^caddr: " view-error) #t)
              (format "with the view attached, the port crashes in caddr: ~a" view-error))
  (check-equal? view-error plain-error)
  (check-true (and view-trace (> (length (string-split view-trace "\n")) 1000) #t))
  (check-equal? view-trace plain-trace "the traces up to the crash are the same"))

;; Pictures of the Workspace window
(module+ test
  ;; a fresh engine per scene, sharing this module's racket/draw (and so its
  ;; class system), so that the bitmaps can be read here
  (define (scene-namespace)
    (define ns (make-base-namespace))
    (namespace-attach-module (current-namespace) 'racket/draw ns)
    ns)
  (define scenes
    (parameterize ([current-namespace (scene-namespace)])
      (dynamic-require harness 'scenes)))
  (define (argb bm)
    (define w (send bm get-width))
    (define h (send bm get-height))
    (define bytes (make-bytes (* 4 w h)))
    (send bm get-argb-pixels 0 0 w h bytes)
    (values w h bytes))
  (for ([scene scenes])
    (define name (car scene))
    (define file (build-path snapshot-dir (format "workspace-~a.png" name)))
    (define bm
      (parameterize ([current-namespace (scene-namespace)])
        ((dynamic-require harness 'render-scene) name)))
    (define-values (w h got) (argb bm))
    (check-equal? (list w h) '(800 600) (format "~a: the window's size" name))
    ;; not blank: black text and lines on the white background
    (check-true (for/or ([i (in-range 0 (bytes-length got) 4)])
                  (and (= (bytes-ref got (+ i 1)) 0) (= (bytes-ref got (+ i 2)) 0)
                       (= (bytes-ref got (+ i 3)) 0)))
                (format "~a: something is drawn" name))
    (cond
      [(getenv "METACAT_UPDATE_SNAPSHOTS")
       (send bm save-file file 'png)
       (printf "wrote ~a\n" file)]
      [else
       (define-values (sw sh want) (argb (read-bitmap file)))
       (define same? (and (= sw w) (= sh h) (equal? got want)))
       (unless same?
         (send bm save-file (format "/tmp/workspace-~a-actual.png" name) 'png))
       (check-true same?
                   (format "~a: the rendering differs from ~a (see /tmp/workspace-~a-actual.png)"
                           name file name))])))

;; views.rkt: racket/draw, never racket/gui
(module+ test
  (define-runtime-path views "../gui/views.rkt")
  (parameterize ([current-namespace (make-base-namespace)])
    (dynamic-require views #f)
    (define declared? (lambda (m) (module-declared? m #f)))
    (check-true (declared? 'racket/draw))
    (check-false (declared? 'racket/gui/base) "views.rkt does not load racket/gui")))
