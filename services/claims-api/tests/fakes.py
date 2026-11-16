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

    def sort(self, key=None, direction=1, *args, **kwargs):
        if isinstance(key, str):
            self.docs = sorted(self.docs, key=lambda d: d.get(key, 0), reverse=direction < 0)
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
                keep_id = "_id" in query
                return copy.deepcopy({k: v for k, v in doc.items() if keep_id or k != "_id"})
        return None

    def find(self, query=None, projection=None):
        return FakeCursor([copy.deepcopy(d) for d in self.docs if _matches(d, query or {})])

    async def find_one_and_update(self, query, update, upsert=False, return_document=False):
        await self.update_one(query, update, upsert=upsert)
        return await self.find_one(query)

    async def update_one(self, query, update, upsert=False):
        for doc in self.docs:
            if _matches(doc, query):
                doc.update(update.get("$set", {}))
                for key, value in update.get("$inc", {}).items():
                    doc[key] = doc.get(key, 0) + value
                for key, value in update.get("$push", {}).items():
                    doc.setdefault(key, []).append(value)
                return
        if upsert:
            doc = dict(query)
            for key, value in update.get("$inc", {}).items():
                doc[key] = value
            doc.update(update.get("$set", {}))
            self.docs.append(doc)


class FakeDB(dict):
    def __missing__(self, name):
        self[name] = FakeCollection()
        return self[name]
