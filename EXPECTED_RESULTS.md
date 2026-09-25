# Expected results

What each command prints when the artifact is intact. Numbers refer to the current PDFs
in `paper/`.

## `bash scripts/verify.sh` (2 s)

```
PASS: 65 manifest entries
PASS: package hygiene, local-path and token checks
...
29/29 claims match the manuscript.
RESULT: PASS -- artifact results are consistent with the paper.
...
camera-ready: 117 claims, 117 pass, 0 fail, 0 deviations, 0 timing (info)
extended: 122 claims, 122 pass, 0 fail, 0 deviations, 0 timing (info)
239 claims: 239 pass, 0 fail, 0 documented deviations, 0 timing values (info only)
RESULT: PASS
PASS: camera-ready PDF has 10 pages
PASS: artifact verification complete
```

On the committed results every claim of both papers passes.

## `bash scripts/run-smoke.sh` (21 s)

```
[1/4] unit tests
...
OK
[2/4] core experiments into a temporary folder (about 20 s), then the claim checks on them
camera-ready: 117 claims, 115 pass, 0 fail, 0 deviations, 2 timing (info)
extended: 122 claims, 121 pass, 0 fail, 0 deviations, 1 timing (info)
239 claims: 236 pass, 0 fail, 0 documented deviations, 3 timing values (info only)
RESULT: PASS
[3/4] regenerated core results against the committed ones
0 known differences, 0 unexpected differences (timing keys skipped)
[4/4] camera-ready and extended claims against the committed results
camera-ready: 117 claims, 117 pass, 0 fail, 0 deviations, 0 timing (info)
extended: 122 claims, 122 pass, 0 fail, 0 deviations, 0 timing (info)
239 claims: 239 pass, 0 fail, 0 documented deviations, 0 timing values (info only)
RESULT: PASS
```

Step 3 shows that the seeded core experiments reproduce `core_results.json` bit for bit
apart from the timings. In step 2 the rerun timings replace the committed ones. Timing
claims (cost per action, R^2, microsecond scale) are then printed as INFO when they
differ from the paper, and the split between pass and timing lines depends on the host
and its load. On a busy machine the R^2 of the rerun can drop well below 0.987.
`deon/check_results.py` then prints one FAIL for the timing fit, and `check-claims.py`
adds a NOTE that it treats this line as INFO.

## `bash scripts/run-full.sh` (35 s)

The last lines are:

```
camera-ready: 117 claims, 115 pass, 0 fail, 0 deviations, 2 timing (info)
extended: 122 claims, 121 pass, 0 fail, 0 deviations, 1 timing (info)
239 claims: 236 pass, 0 fail, 0 documented deviations, 3 timing values (info only)
RESULT: PASS
[7/7] regenerated results against the committed ones
== core_results.json
== stress_results.json

0 known differences, 0 unexpected differences (timing keys skipped)
NOTE: AgentDojo not installed. The committed snapshot deon/results/agentdojo_results.json is used.
Output folder: ...
```

The split between pass and timing lines depends on the host. Apart from the timing
keys, the rerun reproduces both `core_results.json` and `stress_results.json` bit for
bit.

Matplotlib may print `'created' timestamp seems very low` and
`findfont: Failed to find font weight bold for cmr10, now using 400.` while it builds
`fig_results.pdf`. Both messages are harmless.

Figures. The figures in `$DEON_OUT/figures` match camera-ready Fig. 3 and extended
Figs. 3 to 7 when rendered (checked visually).

## `python3 scripts/make-tables.py`

Prints camera-ready Table 1 (extended Table 3) with the rows gemma2:2b 100/100/100/0,
llama3.2:3b 97/100/100/0, qwen2.5-coder:7b 100/100/87/0, and 100/100/100/0 for the
other three models. It then prints extended Table 4 (Deon 37.5% utility and 0.0% ASR,
undefended 50.0% and 11.8%), Table 5 and Table 9.

## Optional runs

- Ollama ladder: one `llm_summary_<model>.json` per model. Deon's attack success
  (`asr_policyshield`) is 0.0 for every model by construction. The other rates vary from
  run to run.
- AgentDojo: `agentdojo_results.json` with the same structure as the committed file.
  Deon's attack success is 0.0 by construction. Utilities and the other defences' rates
  vary from run to run.
