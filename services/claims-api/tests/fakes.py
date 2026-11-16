"""Minimal in-memory stand-in for the Motor collection operations the code uses."""

import copy


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def __aiter__(self):
        self._it = iter(self.docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration from None

    def sort(self, *args, **kwargs):
        return self

    def limit(self, n):
        return FakeCursor(self.docs[:n])

    async def to_list(self, length=None):
        return list(self.docs[:length])


def _matches(doc, query):
    for key, cond in query.items():
        if isinstance(cond, dict) and "$in" in cond:
            if doc.get(key) not in cond["$in"]:
                return False
        elif doc.get(key) != cond:
            return False
    return True


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = [dict(d) for d in (docs or [])]

    async def insert_one(self, doc):
        self.docs.append(copy.deepcopy(doc))

    async def insert_many(self, docs):
        self.docs.extend(copy.deepcopy(d) for d in docs)

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if _matches(doc, query):
                return copy.deepcopy({k: v for k, v in doc.items() if k != "_id"})
        return None

    def find(self, query=None, projection=None):
        return FakeCursor([copy.deepcopy(d) for d in self.docs if _matches(d, query or {})])

    async def update_one(self, query, update, upsert=False):
        for doc in self.docs:
            if _matches(doc, query):
                doc.update(update.get("$set", {}))
                for key, value in update.get("$inc", {}).items():
                    doc[key] = doc.get(key, 0) + value
                for key, value in update.get("$push", {}).items():
                    doc.setdefault(key, []).append(value)
                return


class FakeDB(dict):
    def __missing__(self, name):
        self[name] = FakeCollection()
        return self[name]
