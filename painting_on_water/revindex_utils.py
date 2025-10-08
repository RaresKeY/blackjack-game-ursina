from collections import defaultdict
# [ ] top-level TODO: generalize
# [ ] top-level TODO: finish and clean up

# [ ] TODO: cobmbine with ngram method in class and make static
# ngrams - n len substrings of word
def build_ngram_substrings(words: list | str, n: int = 3) -> list[str]:
    if not isinstance(words, (list, str)):
        raise ValueError(f"Expected list or str, got {type(words).__name__}: {words}")
    if isinstance(words, str):
        words = [words] # normalize to list

    ngrams = []
    for word in words:
        for i in range(len(word) - n + 1):
            ngrams.append(word[i:i + n])
    return ngrams


class ReverseIndex:
    """
    Reversed Index
    Partial ngrams Search
    Integers mapping
    """
    def __init__(self, data: dict | None = None):
        # maps int index -> UUID
        self.integermap = {}
        # maps term/ngram -> set of int indices
        self.reverse_index = defaultdict(set)

        if data is not None:
            self.rebuild(data)


    def rebuild(self, data: dict):
        """Rebuild reverse index"""
        self.integermap.clear()
        self.reverse_index.clear()

        for idx, (key, value) in enumerate(data.items()):
            self.integermap[idx] = key
            self._walk(value, idx)

    def _walk(self, obj, idx: int):
        """Recursively walk dicts/lists/sets and add terms."""
        if isinstance(obj, str):
            # index full string
            self._add_term(obj, idx)
            # index ngrams
            for ng in self._ngrams(obj):
                self._add_term(ng, idx)
        elif isinstance(obj, (list, set, tuple)):
            for item in obj:
                self._walk(item, idx)
        elif isinstance(obj, dict):
            for v in obj.values():
                self._walk(v, idx)
        # else ignore numbers, None, etc.

    def _add_term(self, term: str, idx:int):
        if not term:   # catches "" or None
            return
        self.reverse_index[term.casefold()].add(idx)
       
    def _ngrams(self, words: list | str, n: int = 3) -> list[str]:
        # ngrams = all n len substrings of word
        # [ ] TODO: think about edge case when it returns empty list if word length < n
        if not isinstance(words, (list, str)):
            raise ValueError(f"Expected list or str, got {type(words).__name__}: {words}")
        if isinstance(words, str):
            words = [words] # normalize to list

        ngrams = []
        for word in words:
            word = word.casefold()
            for i in range(len(word) - n + 1):
                ngrams.append(word[i:i + n])
        return ngrams

    def search(self, term: str) -> list[str]:
        """Return UUIDs that match a search term"""
        term = term.casefold()
        if term not in self.reverse_index:
            return []
        return [self.integermap[i] for i in self.reverse_index[term]]
    
    def get_key(self, indexer: int) -> str:
        return self.integermap[indexer]


if __name__ == "__main__":
    my_friends_list = dict()

    user_idx = ReverseIndex(my_friends_list)

    print(user_idx.reverse_index)
    print(user_idx.integermap)

    # check
    print(len(user_idx.reverse_index), "entries")
    for key, items in user_idx.reverse_index.items():
        for idx in items:
            print(key, '', user_idx.get_key(idx))