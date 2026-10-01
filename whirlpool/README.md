# whirlpool: agent evaluation

`cases/` holds anonymised sample cases with the answer we expect. `run_evals.py` sends each case through sombrero and scores:

- rejection code decoded correctly
- right policy clause cited
- every quote found in its source (checker pass rate)
- strength verdict matches the expected one

Run before every demo build. Target: 10 cases by week 1, 20 by week 2.
