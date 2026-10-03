# Run times: the Python port against the oracle (loop0002 item 11)

Produced by `python3 python/oracle/bench_runs.py docs/python-run-times.md` (its output is
the table below) on 2026-10-03, on the 32-core Linux machine, with Python 3.12.13 and
Chez Scheme 10.0.0. It runs every run of `tests/problems.txt` once as a process:
`python3 -m metacat ...` (from `python/`, bytecode cached) and
`scheme --script chez_scheme/oracle/run.ss ...` with the same arguments, 8 processes at a
time, and checks that both print the same output. Times are wall-clock seconds per
process, summed over a problem's seeds, startup included. The per-codelet columns
subtract the startup median from each run.

Reading the table:
- The oracle compiles the 44 original files at every start (about 0.7 s). Python loads
  its cached bytecode and builds the Slipnet in about 0.05 s, so on short runs the Python
  process finishes first.
- Per codelet, Python is about **9× slower** than Chez over all runs (1.23 vs 0.13 ms),
  well inside the 20–100× that TASK.md expected. Long runs cost more per codelet in both,
  since the Workspace and the Memory grow: the halt problem `eqe qeq abbba aaabaaa`
  (34,601 codelets over three seeds) takes 56 s in Python against 7.4 s in Chez.
- No speed-up has been made yet; that is item 12. The 109 goldens take about 35 s in the
  test suite, run 32 at a time in forks (test_golden.py).
- For comparison, docs/run-times.md has the Racket port: about 0.2 ms per codelet.

Startup (load, set up a problem, run 1 codelet), median of 5: Chez 0.71 s, Python 0.05 s.

| Problem | Runs | Codelets | Chez s | Python s | Python / Chez | Chez ms/codelet | Python ms/codelet |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `abc abd mrrjjj mrrjjjj` | 3 | 8321 | 3.62 | 12.34 | 3.40 | 0.18 | 1.47 |
| `xqc xqd mrrjjj mrrkkk` | 3 | 4537 | 3.13 | 5.45 | 1.74 | 0.22 | 1.17 |
| `rst rsu xyz uyz` | 3 | 10699 | 3.57 | 12.05 | 3.37 | 0.13 | 1.11 |
| `abc abd xyz dyz` | 3 | 10157 | 3.07 | 10.65 | 3.47 | 0.09 | 1.04 |
| `xqc xqd mrrjjj mrrjjjj` | 3 | 18448 | 5.14 | 29.11 | 5.67 | 0.16 | 1.57 |
| `eqe qeq abbbc aaabccc` | 3 | 17939 | 5.26 | 30.80 | 5.85 | 0.17 | 1.71 |
| `abc abd xyz` | 4 | 7474 | 3.31 | 6.46 | 1.95 | 0.06 | 0.84 |
| `eqe qeq abbbc` | 3 | 7578 | 2.56 | 5.74 | 2.25 | 0.06 | 0.74 |
| `abc abd xyz xyd` | 3 | 2867 | 2.58 | 3.27 | 1.27 | 0.16 | 1.09 |
| `abc abd xyz wyz` | 3 | 2873 | 2.63 | 3.52 | 1.34 | 0.17 | 1.18 |
| `rst rsu xyz xyu` | 3 | 2049 | 2.52 | 2.29 | 0.91 | 0.19 | 1.05 |
| `rst rsu xyz wyz` | 3 | 3235 | 2.58 | 4.30 | 1.67 | 0.14 | 1.29 |
| `abc abd mrrjjj mrrkkk` | 3 | 3647 | 2.71 | 4.59 | 1.69 | 0.16 | 1.22 |
| `eqe qeq abbba baaab` | 3 | 13404 | 3.53 | 16.08 | 4.55 | 0.10 | 1.19 |
| `eqe qeq abbba aaabaaa` | 3 | 34601 | 7.38 | 55.95 | 7.59 | 0.15 | 1.61 |
| `eeqee qeeq xxixx` | 3 | 7181 | 2.90 | 8.00 | 2.76 | 0.11 | 1.09 |
| `aabc aabd ijkk ijll` | 3 | 4327 | 2.69 | 6.43 | 2.39 | 0.13 | 1.46 |
| `aabc aabd ijkk hjkk` | 3 | 10273 | 4.04 | 17.77 | 4.40 | 0.19 | 1.72 |
| `abc cba mrrjjj mmmrrj` | 3 | 13341 | 4.06 | 20.26 | 5.00 | 0.14 | 1.51 |
| `abc abd ijk abd` | 3 | 5234 | 2.80 | 4.88 | 1.74 | 0.13 | 0.91 |
| `abc aabbcc kkjjii` | 3 | 4500 | 2.62 | 4.60 | 1.75 | 0.11 | 0.99 |
| `a b z` | 3 | 3000 | 2.52 | 0.98 | 0.39 | 0.13 | 0.28 |
| `abc abd glz` | 3 | 5400 | 2.27 | 4.73 | 2.08 | 0.03 | 0.85 |
| `eqe qeq bxxxb xbbbx` | 3 | 7053 | 2.98 | 5.77 | 1.94 | 0.12 | 0.80 |
| `eqe qeq bxxxb bbbxbbb` | 3 | 14901 | 3.63 | 18.17 | 5.00 | 0.10 | 1.21 |
| `abc abd mrrjjj` | 3 | 3643 | 2.49 | 3.71 | 1.49 | 0.10 | 0.98 |
| `abc abd ijk` | 3 | 1840 | 2.27 | 1.55 | 0.68 | 0.07 | 0.77 |
| `abc abd iijjkk` | 3 | 6471 | 2.68 | 6.17 | 2.30 | 0.08 | 0.93 |
| `abc abd kji` | 3 | 1973 | 2.35 | 1.95 | 0.83 | 0.11 | 0.92 |
| `abc abd kkjjii` | 3 | 4121 | 2.78 | 3.91 | 1.41 | 0.16 | 0.92 |
| `rst rsu xyz` | 3 | 4648 | 2.50 | 4.18 | 1.67 | 0.08 | 0.87 |
| `xqc xqd mrrjjj` | 3 | 1857 | 2.34 | 1.69 | 0.72 | 0.11 | 0.84 |
| `eqe qeq abbba` | 3 | 4893 | 2.61 | 3.64 | 1.40 | 0.10 | 0.72 |
| `apc abc opc` | 3 | 2439 | 2.16 | 1.88 | 0.87 | 0.06 | 0.72 |
| `abc ccbbaa ijk` | 3 | 5959 | 2.83 | 5.47 | 1.93 | 0.12 | 0.90 |
| `abc aabbdd ijkl` | 3 | 11974 | 3.24 | 11.22 | 3.47 | 0.09 | 0.93 |
| **all** | 109 | 272857 | 112.34 | 339.56 | 3.02 | 0.13 | 1.23 |
