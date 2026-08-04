from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "resources" / "evidence" / "corpus.json"
DEFAULT_INDEX = ROOT / "resources" / "evidence" / "index.json"
TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def build_index(corpus: dict[str, Any]) -> dict[str, Any]:
    if corpus.get("schema_version") != 1:
        raise ValueError("Unsupported evidence corpus schema version.")
    sources = corpus.get("sources")
    if not isinstance(sources, list) or not 5 <= len(sources) <= 10:
        raise ValueError("The evidence corpus must contain between 5 and 10 sources.")

    documents: list[dict[str, Any]] = []
    source_cards: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for source in sources:
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id or source_id in source_ids:
            raise ValueError("Each evidence source needs a unique source_id.")
        source_ids.add(source_id)
        passages = source.get("passages")
        if not isinstance(passages, list) or not passages:
            raise ValueError(f"Evidence source {source_id} has no passages.")
        content_sha256 = hashlib.sha256(_canonical(passages)).hexdigest()
        card = {
            key: source[key]
            for key in (
                "source_id",
                "title",
                "organization",
                "url",
                "document_date",
                "version",
                "status",
                "topics",
            )
        }
        card.update(
            captured_at=corpus["captured_at"],
            content_sha256=content_sha256,
            rights_basis=corpus["rights_basis"],
        )
        source_cards.append(card)
        for passage in passages:
            section = passage.get("section")
            excerpt = passage.get("excerpt")
            claim = passage.get("claim")
            if not all(isinstance(item, str) and item.strip() for item in (section, excerpt, claim)):
                raise ValueError(f"Evidence source {source_id} has an invalid passage.")
            location = f"{passage.get('page') or ''}\0{section}\0{excerpt}"
            chunk_id = f"{source_id}:{hashlib.sha256(location.encode()).hexdigest()[:16]}"
            searchable = " ".join(
                [source["title"], " ".join(source["topics"]), section, claim, excerpt]
            )
            token_counts = Counter(tokenize(searchable))
            documents.append(
                {
                    **card,
                    "captured_at": corpus["captured_at"],
                    "content_sha256": content_sha256,
                    "chunk_id": chunk_id,
                    "section": section,
                    "page": passage.get("page"),
                    "claim": claim,
                    "excerpt": excerpt,
                    "tokens": dict(sorted(token_counts.items())),
                    "length": sum(token_counts.values()),
                    "conflict_group": passage.get("conflict_group"),
                    "stance": passage.get("stance"),
                }
            )

    documents.sort(key=lambda item: item["chunk_id"])
    source_cards.sort(key=lambda item: item["source_id"])
    return {
        "schema_version": 1,
        "captured_at": corpus["captured_at"],
        "corpus_sha256": hashlib.sha256(_canonical(corpus)).hexdigest(),
        "rights_basis": corpus["rights_basis"],
        "source_count": len(source_cards),
        "passage_count": len(documents),
        "sources": source_cards,
        "documents": documents,
    }


def rendered_index(corpus_path: Path = DEFAULT_CORPUS) -> bytes:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    return (json.dumps(build_index(corpus), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the deterministic local ADME evidence index.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_INDEX)
    args = parser.parse_args()
    payload = rendered_index(args.corpus)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(f"wrote {args.output} ({len(payload)} bytes, sha256={hashlib.sha256(payload).hexdigest()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
