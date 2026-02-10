# Tokenizer (Byte-Pair Encoding)

## Problem
Build a BPE tokenizer: learn a fixed number of merge rules from a small
corpus, then use those rules to encode arbitrary text into token IDs and
decode IDs back into text. The round trip must be exact for every input,
including text the tokenizer never saw during training.

## Design
- `BPETokenizer.vocab` - `dict[int, bytes]`, seeded with all 256 single-byte
  tokens before any training happens. Operating on raw UTF-8 bytes rather
  than characters (GPT-2's approach) is what makes the round-trip guarantee
  hold unconditionally: every possible byte value already has a token, so
  encoding can never hit an "unknown" input.
- `_pretokenize` - splits text into word/whitespace runs (`\S+` or `\s+`) so
  merges never cross a word boundary. The split is total and non-overlapping,
  so re-joining the chunks always reproduces the original text exactly.
- `train(corpus, num_merges)` - counts adjacent byte-pair frequencies across
  all chunks, repeatedly merges the most frequent pair into a new token ID,
  and records the order merges were learned in (`merge_rank`) so `encode` can
  replay them in the same order.
- `encode` / `decode` - `encode` re-pretokenizes, then repeatedly applies the
  lowest-rank (earliest-learned) applicable merge to each chunk until none
  apply. `decode` just concatenates each token's raw bytes and does one final
  UTF-8 decode - since every token maps back to an exact byte sequence, this
  can never lose information.

## Patterns used
- No GoF pattern is the point here - BPE's structure (a learned merge table
  applied greedily) is the "pattern"; the code stays a small, self-contained
  algorithm rather than an object hierarchy.

## How to run
```
cd /Users/bhargav/Desktop/low-level-design/tokenizer
python3 main.py
```
The demo trains on a small repeated corpus, then round-trips several test
strings - including an unseen word, multibyte UTF-8 (accents, CJK, emoji),
an empty string, and a whitespace-only string - and asserts every one comes
back byte-for-byte identical.
