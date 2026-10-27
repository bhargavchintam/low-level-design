# low-level-design

[![checks](https://github.com/bhargavchintam/low-level-design/actions/workflows/checks.yml/badge.svg)](https://github.com/bhargavchintam/low-level-design/actions/workflows/checks.yml)
![python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![java](https://img.shields.io/badge/java-17-ED8B00?logo=openjdk&logoColor=white)
[![license](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)

Object-oriented / low-level design problems, each in its own folder with the code and a short README
(problem, the classes, the pattern used, how to run). Java and Python, mixed.

<p align="center">
  <img src="docs/media/demo.gif" alt="The kv-cache-pool and dynamic-batcher demos print their results and pass their self-checks, then run_all.py runs all 48 demos and every one passes" width="860">
</p>

## Run a demo

Each design has a small demo `main` you can run:

```sh
cd parking-lot && java Main.java      # Java 17 or newer, no separate compile step
cd rate-limiter && python3 main.py
```

To run every demo at once, from the repo root:

```sh
pip install -r requirements.txt                  # numpy, used by 11 of the Python demos
python3 run_all.py                               # one PASS or FAIL row per design
python3 run_all.py kv-cache-pool dynamic-batcher # only the designs you name
```

`run_all.py` exits with status 1 if any demo fails. It compiles and runs the Java demos when `javac`
is installed, and skips them when it is not. CI runs it on every push to `main` and on pull requests,
with Python 3.12 and Java 17.

## Designs

48 designs in five groups:
[ML and AI infrastructure](#ml-and-ai-infrastructure) ·
[ML building blocks](#ml-building-blocks) ·
[Systems and concurrency](#systems-and-concurrency) ·
[Data structures and storage](#data-structures-and-storage) ·
[Classic object-oriented interview problems](#classic-object-oriented-interview-problems)

### ML and AI infrastructure

| Design | Language | Summary |
|---|---|---|
| [kv-cache-pool](kv-cache-pool/) | Python | Paged KV cache memory, as in vLLM's PagedAttention: sequences grow page by page from a shared pool, and LRU eviction skips sequences that are still generating. |
| [dynamic-batcher](dynamic-batcher/) | Python | Flushes a batch when it reaches the max size or the oldest request hits the max wait. A fake clock makes every batch boundary exact and testable. |
| [inference-server](inference-server/) | Python | Client threads send requests; one worker groups them into batches and runs one forward pass per batch, within a wait budget. |
| [gpu-memory-allocator](gpu-memory-allocator/) | Python | Device memory allocator with two strategies, best-fit free list and buddy system, compared on fragmentation as blocks are freed. |
| [gpu-quota-manager](gpu-quota-manager/) | Python | Multi-tenant GPU scheduler with weighted fair shares. It takes back only GPUs above a tenant's fair share and reports Jain's fairness index. |
| [llm-rate-limiter](llm-rate-limiter/) | Python | Limits requests per minute and tokens per minute at the same time, with two token buckets per client. |
| [model-router](model-router/) | Python | Canary and weighted traffic splits across model versions, with fallback to the next backend when one fails. |
| [model-registry](model-registry/) | Python | MLflow-style model versions and stages (None, Staging, Production, Archived). Illegal moves are rejected and only one version is in Production. |
| [experiment-tracker](experiment-tracker/) | Python | MLflow-style runs with params and metric series. A context manager marks each run finished or failed, and runs can be compared by a metric. |
| [feature-store-client](feature-store-client/) | Python | Online lookup of the latest feature values with staleness flags, and point-in-time-correct historical lookup for training data. |
| [streaming-feature-aggregator](streaming-feature-aggregator/) | Python | Count, sum and average per entity over a sliding time window, updated as events arrive and age out. |
| [ab-test-assignment](ab-test-assignment/) | Python | Hash-based experiment bucketing: the same user always gets the same variant, splits follow the weights, and no assignment table is stored. |
| [embedding-cache](embedding-cache/) | Python | LRU cache that computes an embedding on a miss and tracks hit rate on a Zipfian query stream. |
| [vector-store](vector-store/) | Python | Top-k vector search with an exact brute-force index and an IVF (k-means) index, with IVF measured by recall@k. |
| [prompt-template-engine](prompt-template-engine/) | Python | Prompt templates with named variables and partial binding, rendered as plain text, a few-shot prompt or chat messages. |

### ML building blocks

| Design | Language | Summary |
|---|---|---|
| [tokenizer](tokenizer/) | Python | Byte-level BPE tokenizer. It learns merges from a corpus, and encode then decode gives back any text exactly, even text it never saw. |
| [mini-autograd](mini-autograd/) | Python | Reverse-mode autodiff over scalars (`+`, `*`, `**`, `relu`, `tanh`), checked against finite differences. |
| [tensor-ndarray](tensor-ndarray/) | Python | A flat buffer with shape and strides: reshape, transpose, broadcasting and 2-D matmul, checked against NumPy. |
| [compute-graph-executor](compute-graph-executor/) | Python | Runs a target node's ancestors in topological order with a shared cache, so a shared node is computed only once. |
| [kernel-dispatcher](kernel-dispatcher/) | Python | Picks a kernel by (op, dtype, backend), falls back to a generic kernel, and raises an error when no kernel exists. |
| [data-loader](data-loader/) | Python | PyTorch-style Dataset and DataLoader with batching, shuffling every epoch, transforms and `drop_last`. |
| [ml-pipeline](ml-pipeline/) | Python | sklearn-style pipeline (imputer, scaler, one-hot encoder, k-NN) that learns its statistics from training data only. |

### Systems and concurrency

| Design | Language | Summary |
|---|---|---|
| [thread-pool](thread-pool/) | Python | Fixed worker threads on a shared queue. `submit` returns a future that gives back the result or raises the task's error. |
| [object-pool](object-pool/) | Python | Thread-safe pool of reusable objects with a size cap. Objects are reset on release, and a context manager makes sure each one is returned. |
| [priority-scheduler](priority-scheduler/) | Python | Priority job queue with aging, so low-priority jobs cannot starve. Uses lazy deletion on a heap. |
| [circuit-breaker](circuit-breaker/) | Python | Closed, open and half-open states that stop calls to a failing service and test when it has recovered. |
| [rate-limiter](rate-limiter/) | Python | Token bucket, fixed window and sliding window log limiters behind one interface. |
| [consistent-hash-ring](consistent-hash-ring/) | Python | Hash ring with virtual nodes. Adding a node moves only about 1/N of the keys. |
| [metrics-aggregator](metrics-aggregator/) | Python | Streaming count, mean and standard deviation (Welford), plus p50 and p99 from an exact or a reservoir-sampling sketch. |
| [logging-framework](logging-framework/) | Java | A chain of log handlers (console, file, alert), each writing only messages at or above its own level. |
| [notification-service](notification-service/) | Python | Broadcasts a message to subscribed users over the channels each one picked: email, SMS or push. |

### Data structures and storage

| Design | Language | Summary |
|---|---|---|
| [lru-cache](lru-cache/) | Java | O(1) `get` and `put` with a HashMap and a hand-written doubly linked list. |
| [cache-with-eviction-policies](cache-with-eviction-policies/) | Python | Fixed-size cache with swappable LRU, LFU, FIFO and random eviction. |
| [bloom-filter](bloom-filter/) | Python | Bloom filter sized from a capacity and a target false-positive rate, using double hashing. It never gives a false negative. |
| [lsm-memtable](lsm-memtable/) | Python | LSM-tree write and read path: memtable, flushed sorted runs, tombstones and compaction. Reads always return the newest value. |

### Classic object-oriented interview problems

| Design | Language | Summary |
|---|---|---|
| [parking-lot](parking-lot/) | Java | Multi-floor lot that fits motorcycles, cars and buses into sized spots, issues tickets and charges hourly fees. |
| [elevator-system](elevator-system/) | Java | Several elevators, a nearest-elevator dispatcher and one class per elevator state, simulated floor by floor. |
| [vending-machine](vending-machine/) | Python | Coins, product selection, change and sold-out slots, with one class per machine state. |
| [atm](atm/) | Python | Card and PIN session with limited attempts, balance checks, and cash split into notes. |
| [library-management](library-management/) | Java | Books and their physical copies, checkout and return, and a notice to members when a book comes back. |
| [tic-tac-toe](tic-tac-toe/) | Python | Two players on a 3x3 board with win and draw detection. Scripted moves make the demo repeatable. |
| [snake-and-ladder](snake-and-ladder/) | Python | Multiplayer game on a 100-square board with snakes, ladders and a seeded die. |
| [splitwise](splitwise/) | Java | Shared expenses split equally, by exact amounts or by percentage, with the net amount each person owes the others. |
| [movie-ticket-booking](movie-ticket-booking/) | Python | Shows, seat maps, seat locking and booking, payment, and confirmation notices. |
| [car-rental](car-rental/) | Java | Fleet search, reservations, and daily or weekly pricing, with a factory for vehicle types. |
| [chess](chess/) | Python | 8x8 board, six piece types with their own move rules, and turn order. Moves are pseudo-legal (no check detection). |
| [hotel-booking](hotel-booking/) | Java | Room search over date ranges, booking, and a checkout invoice with weekend pricing. |
| [meeting-scheduler](meeting-scheduler/) | Java | Books shared meeting rooms without double-booking and tells the organizer and attendees either way. |

Patterns show up where they fit — strategy, factory, state, observer, chain of responsibility — not forced.

## Contributing

New designs are welcome. Each one is a folder with a runnable demo and a short README.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the layout and a list of open ideas.

## License

[MIT](LICENSE)
