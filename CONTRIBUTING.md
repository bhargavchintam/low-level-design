# Contributing

Thanks for taking a look. Each design here is small on purpose: one folder, one runnable demo, and a
short README that explains the choices.

## Run the demos

```sh
pip install -r requirements.txt
python3 run_all.py                 # every design
python3 run_all.py my-new-design   # just yours
```

CI runs `python3 run_all.py` on Python 3.12 and Java 17. A pull request is ready when it ends with
`N/N demos passed`.

## Adding a design

1. Make a folder at the repo root named in kebab-case, for example `job-queue/`.
2. Put the demo entry point in it:
   - Python: `main.py`, run as `cd job-queue && python3 main.py`.
   - Java: `Main.java` that starts with `public class Main` and its `main` method, run as
     `cd job-queue && java Main.java`. The single-file launcher runs the first class in the file.

   Extra files are fine (see `atm/` or `vending-machine/`), but `main.py` or `Main.java` must be the
   entry point. `run_all.py` finds the new folder by that file. There is nothing to register.
3. Make the demo runnable as is:
   - no input, no network, no files written;
   - Python standard library plus NumPy only; Java standard library only;
   - the same output on every run: seed any randomness and use a fake clock instead of real time
     where you can (see `dynamic-batcher/` or `circuit-breaker/`);
   - finish in a few seconds.
4. Make the demo print its result, and check it. Walk through one realistic scenario, print what
   happened, then `assert` the key invariants (Java: throw an exception) so a bug fails the run. End
   with one line that says what was checked, for example:

   ```
   self-check passed: every request landed in exactly one batch, FIFO order held, ...
   ```

5. Add a short `README.md` in the folder with these sections:
   - **Problem**: the requirements, in two to four sentences.
   - **Design**: the main classes and what each one owns.
   - **Patterns used**: only the ones that really help, and why.
   - **Trade-offs**: what you chose, what you gave up, and what is out of scope.
   - **How to run**: `cd <folder> && python3 main.py` (or `java Main.java`), and what the demo shows.
6. Add one row to the right table in the root `README.md`: link, language, one-line summary.

## Ideas that would fit

- `prefix-cache`: a radix tree over token IDs so requests with the same prompt prefix share KV pages
  (builds on `kv-cache-pool/`)
- `continuous-batcher`: iteration-level batching that adds and removes sequences at every decode step
  under a KV page budget (`dynamic-batcher/` batches whole requests)
- `gang-scheduler`: all-or-nothing GPU allocation for multi-GPU jobs, with backfill for small jobs
- `checkpoint-manager`: async checkpoint saves, keep the last N, resume from the newest complete one
- `write-ahead-log`: append, group commit and crash-recovery replay (pairs with `lsm-memtable/`)
- `ride-hailing`: match riders to nearby drivers, trip states, and pricing as a strategy

Open an issue first if you want to discuss an idea before writing it.

## Pull requests

- One design per pull request, with a short description of the problem it solves.
- By contributing you agree that your work is released under the [MIT License](LICENSE).
