"""SQLite FTS5-backed lexical chunk index."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from gestaltx.ingest.models import Chunk


def _payload(chunk: Chunk | dict[str, Any]) -> dict[str, Any]:
    if isinstance(chunk, dict):
        return dict(chunk)
    if hasattr(chunk, "model_dump"):
        return chunk.model_dump(mode="json")
    return chunk.dict()


class FTSIndex:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
                chunk_id UNINDEXED, doc_id UNINDEXED, text,
                tier UNINDEXED, doctype UNINDEXED, path UNINDEXED,
                entities, payload UNINDEXED, tokenize='unicode61'
            )
            """
        )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "FTSIndex":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def add(self, chunks: Iterable[Chunk | dict[str, Any]], *, replace: bool = True) -> int:
        rows = []
        for chunk in chunks:
            item = _payload(chunk)
            chunk_id = str(item["chunk_id"])
            if replace:
                self.connection.execute("DELETE FROM chunks WHERE chunk_id = ?", (chunk_id,))
            rows.append(
                (
                    chunk_id,
                    str(item["doc_id"]),
                    str(item.get("text", "")),
                    int(item.get("tier", 5)),
                    str(item.get("doctype", "")),
                    str(item.get("path", "")),
                    " ".join(item.get("entities", [])),
                    json.dumps(item, ensure_ascii=False),
                )
            )
        self.connection.executemany(
            "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
        )
        self.connection.commit()
        return len(rows)

    index = add

    def remove_document(self, doc_id: str) -> int:
        """Delete every chunk belonging to ``doc_id``. Returns rows removed."""
        cursor = self.connection.execute("DELETE FROM chunks WHERE doc_id = ?", (str(doc_id),))
        self.connection.commit()
        return int(cursor.rowcount or 0)

    def count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()
        return int(row["n"] if row is not None else 0)

    def clear(self) -> None:
        self.connection.execute("DELETE FROM chunks")
        self.connection.commit()

    def search(
        self,
        query: str,
        limit: int = 10,
        *,
        tier: int | Iterable[int] | None = None,
        doctype: str | Iterable[str] | None = None,
        entity: str | None = None,
    ) -> list[dict[str, Any]]:
        if not query.strip() or limit < 1:
            return []
        clauses = ["chunks MATCH ?"]
        parameters: list[Any] = [query]

        def add_filter(column: str, value: Any) -> None:
            values = list(value) if isinstance(value, (list, tuple, set, frozenset)) else [value]
            clauses.append(f"{column} IN ({','.join('?' for _ in values)})")
            parameters.extend(values)

        if tier is not None:
            add_filter("tier", tier)
        if doctype is not None:
            add_filter("doctype", doctype)
        if entity:
            clauses.append("lower(entities) LIKE ?")
            parameters.append(f"%{entity.casefold()}%")
        parameters.append(limit)
        sql = (
            "SELECT payload, bm25(chunks) AS rank FROM chunks WHERE "
            + " AND ".join(clauses)
            + " ORDER BY rank LIMIT ?"
        )
        try:
            rows = self.connection.execute(sql, parameters).fetchall()
        except sqlite3.OperationalError:
            parameters[0] = '"' + query.replace('"', '""') + '"'
            rows = self.connection.execute(sql, parameters).fetchall()
        output = []
        for row in rows:
            item = json.loads(row["payload"])
            item["score"] = 1.0 / (1.0 + max(0.0, float(row["rank"])))
            output.append(item)
        return output


SQLiteFTSIndex = FTSIndex

__all__ = ["FTSIndex", "SQLiteFTSIndex"]
