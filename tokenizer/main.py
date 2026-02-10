"""Byte-pair-encoding tokenizer, GPT-2 style: operates on raw UTF-8 bytes (not characters),
so every one of the 256 byte values is a valid base token and any input - including bytes
never seen during training - can always be encoded. That's what makes exact round-trip
decoding a guarantee rather than a best-effort.
"""

import re
from collections import Counter


class BPETokenizer:
    def __init__(self):
        self.vocab: dict[int, bytes] = {i: bytes([i]) for i in range(256)}
        self.merge_rank: dict[tuple[int, int], int] = {}  # pair -> order learned (lower = merge first)
        self._merge_id: dict[tuple[int, int], int] = {}  # pair -> id it merges into

    @staticmethod
    def _pretokenize(text: str) -> list[str]:
        # Split into word / whitespace runs so merges never cross a word boundary.
        # \S+ and \s+ alternate and are non-overlapping, so ''.join(chunks) == text exactly.
        return re.findall(r"\S+|\s+", text)

    @staticmethod
    def _merge_pass(ids: list[int], pair: tuple[int, int], new_id: int) -> list[int]:
        out = []
        i = 0
        while i < len(ids):
            if i < len(ids) - 1 and (ids[i], ids[i + 1]) == pair:
                out.append(new_id)
                i += 2
            else:
                out.append(ids[i])
                i += 1
        return out

    def train(self, corpus: str, num_merges: int):
        chunks = [list(c.encode("utf-8")) for c in self._pretokenize(corpus)]

        for step in range(num_merges):
            pair_counts: Counter = Counter()
            for ids in chunks:
                pair_counts.update(zip(ids, ids[1:]))

            if not pair_counts:
                break
            best_pair, count = pair_counts.most_common(1)[0]
            if count < 2:
                break  # a merge that fires once isn't earning its vocab slot

            new_id = 256 + len(self._merge_id)
            self._merge_id[best_pair] = new_id
            self.merge_rank[best_pair] = step
            self.vocab[new_id] = self.vocab[best_pair[0]] + self.vocab[best_pair[1]]
            chunks = [self._merge_pass(ids, best_pair, new_id) for ids in chunks]

    def encode(self, text: str) -> list[int]:
        out: list[int] = []
        for chunk in self._pretokenize(text):
            ids = list(chunk.encode("utf-8"))
            while len(ids) >= 2:
                candidates = [(self.merge_rank[p], p) for p in zip(ids, ids[1:]) if p in self.merge_rank]
                if not candidates:
                    break
                _, pair = min(candidates)  # apply earliest-learned merge first, same order as training
                ids = self._merge_pass(ids, pair, self._merge_id[pair])
            out.extend(ids)
        return out

    def decode(self, ids: list[int]) -> str:
        raw = b"".join(self.vocab[i] for i in ids)
        return raw.decode("utf-8")

    def vocab_size(self) -> int:
        return len(self.vocab)


def main():
    corpus = (
        "the quick brown fox jumps over the lazy dog. "
        "the dog barks at the quick fox. the fox runs away quickly. "
        "a lazy dog sleeps while the quick fox jumps over the fence. "
    ) * 3

    tok = BPETokenizer()
    tok.train(corpus, num_merges=60)
    print(f"trained vocab: {tok.vocab_size()} tokens ({tok.vocab_size() - 256} learned merges)")

    print("\nsample learned merges (in learning order):")
    ranked = sorted(tok.merge_rank.items(), key=lambda kv: kv[1])
    for pair, rank in ranked[:8]:
        merged_id = tok._merge_id[pair]
        print(f"  #{rank:>2}  {tok.vocab[merged_id]!r}")

    test_strings = [
        "the quick fox jumps over a lazy dog",   # in-distribution
        "the zebra jumps over the fence",         # unseen word "zebra"
        "café naïve 你好 🚀",                       # multibyte UTF-8 the corpus never saw
        "",                                        # empty string edge case
        "   \n\t  ",                                # whitespace-only
    ]

    print("\nround-trip check:")
    all_ok = True
    for s in test_strings:
        ids = tok.encode(s)
        decoded = tok.decode(ids)
        ok = decoded == s
        all_ok &= ok
        raw_bytes = len(s.encode("utf-8"))
        ratio = raw_bytes / len(ids) if ids else 1.0
        label = repr(s) if len(s) < 30 else repr(s[:27] + "...")
        print(f"  {label:<45} bytes={raw_bytes:>3} tokens={len(ids):>3} ratio={ratio:.2f}x  match={ok}")

    assert all_ok, "round-trip failed for at least one test string"
    print("\nself-check passed: every test string decodes back to exactly the original.")


if __name__ == "__main__":
    main()
