#!/usr/bin/env python3
"""Résout les noms d'états d'animation Destiny (hash FNV-1 32 bits).

Entrées (lecture seule) :
  - data/destiny/extract/out/recluse_t/the_recluse/states.json
  - data/destiny/extract/out/gnawing_hunger/states.json
  - data/destiny/extract/work/names/wordlist.txt.gz (liste de mots Charm)

Sorties :
  - data/destiny/extract/work/names/state_names.json (hash -> nom, états résolus)
  - states_named.json à côté de chaque states.json (noms complétés ;
    les non résolus deviennent state_XXXXXXXX)

Usage (depuis la racine du dépôt) :
  data/destiny/extract/venv/bin/python -I tools/resolve_state_names.py
"""
import gzip
import itertools
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK_NAMES = ROOT / "data/destiny/extract/work/names"
WORDLIST = WORK_NAMES / "wordlist.txt.gz"
OUT = ROOT / "data/destiny/extract/out"
STATE_FILES = [
    OUT / "recluse_t/the_recluse/states.json",
    OUT / "gnawing_hunger/states.json",
]
TOKENS = (
    "reload empty full mag magazine clip insert out in start end enter exit "
    "loop idle fire iron sight ads hip sprint run walk melee warlock hunter "
    "titan grenade throw charge charged ready put away jump double land soft "
    "hard slide crouch alt special pull strike finisher inspect weapon down up "
    "switch swap recoil bolt chamber cock tap lift lower raise airborne add "
    "additive pose fidget shoot shot quick fast slow"
).split()
SUFFIXES = [""] + [f"_{i}" for i in range(1, 6)]


def fnv1(data):
    """FNV-1 32 bits (multiplication puis XOR)."""
    value = 0x811C9DC5
    for byte in data:
        value = ((value * 0x01000193) & 0xFFFFFFFF) ^ byte
    return value


def fnv1a(data):
    """FNV-1a 32 bits (XOR puis multiplication)."""
    value = 0x811C9DC5
    for byte in data:
        value = ((value ^ byte) * 0x01000193) & 0xFFFFFFFF
    return value


def iter_states(doc):
    for rig in doc.get("rigs", []):
        for state in rig.get("states", []):
            yield state


def validate(docs):
    """Cherche la variante de hachage qui reproduit tous les noms connus."""
    variants = [
        ("fnv1", fnv1, False),
        ("fnv1 minuscules", fnv1, True),
        ("fnv1a", fnv1a, False),
        ("fnv1a minuscules", fnv1a, True),
    ]
    for label, fn, lower in variants:
        ok = bad = 0
        for doc in docs:
            for state in iter_states(doc):
                hashes = {int(h, 16) for h in state.get("hashes", [])}
                for name in state.get("names", []):
                    if not name or name.startswith("state_"):
                        continue
                    text = name.lower() if lower else name
                    if fn(text.encode("utf-8")) in hashes:
                        ok += 1
                    else:
                        bad += 1
        print(f"validation {label}: ok={ok} ko={bad}")
        if ok and bad == 0:
            return fn, lower
    return None, None


def iter_candidates():
    """Liste de mots (telle quelle et en minuscules), puis combinaisons de jetons."""
    with gzip.open(WORDLIST, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            word = line.strip()
            if not word:
                continue
            yield word
            if word.lower() != word:
                yield word.lower()
    for count in (1, 2, 3):
        for combo in itertools.product(TOKENS, repeat=count):
            base = "_".join(combo)
            for suffix in SUFFIXES:
                yield base + suffix


def search(targets, fn, lower):
    found = {}
    tested = 0
    started = time.time()
    for cand in iter_candidates():
        tested += 1
        text = cand.lower() if lower else cand
        h = fn(text.encode("utf-8"))
        if h in targets and h not in found:
            found[h] = cand
            if len(found) == len(targets):
                break
    print(f"candidats testés : {tested} ; trouvés : {len(found)} ; "
          f"durée : {time.time() - started:.0f} s")
    return found


def main():
    docs = [json.loads(path.read_text(encoding="utf-8")) for path in STATE_FILES]

    all_hashes = set()
    for doc in docs:
        for state in iter_states(doc):
            all_hashes.update(int(h, 16) for h in state.get("hashes", []))
    print(f"hashes d'états uniques : {len(all_hashes)}")

    fn, lower = validate(docs)
    if fn is None:
        print("ARRÊT : aucune variante de hachage ne reproduit les noms connus.")
        sys.exit(1)

    known = {}
    for doc in docs:
        for state in iter_states(doc):
            state_hashes = {int(h, 16) for h in state.get("hashes", [])}
            for name in state.get("names", []):
                if not name or name.startswith("state_"):
                    continue
                h = fn((name.lower() if lower else name).encode("utf-8"))
                if h in state_hashes:
                    known[h] = name
    unresolved = all_hashes - set(known)
    print(f"nommés avant : {len(known)} ; non résolus avant : {len(unresolved)}")

    found = search(unresolved, fn, lower)
    resolved = dict(known)
    resolved.update(found)
    still = all_hashes - set(resolved)
    print(f"nommés après : {len(resolved)} ; encore non résolus : {len(still)}")

    WORK_NAMES.mkdir(parents=True, exist_ok=True)
    state_names = {f"{h:08X}": resolved[h] for h in sorted(resolved)}
    (WORK_NAMES / "state_names.json").write_text(
        json.dumps(state_names, indent=1, ensure_ascii=False), encoding="utf-8")

    named_docs = []
    for path, doc in zip(STATE_FILES, docs):
        for state in iter_states(doc):
            state["names"] = [
                resolved.get(int(h, 16), f"state_{h.upper()}")
                for h in state.get("hashes", [])
            ]
        path.with_name("states_named.json").write_text(
            json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
        named_docs.append(doc)

    print("--- états liés au rechargement (nom -> clips) ---")
    reload_clips = {}
    for doc in named_docs:
        for state in iter_states(doc):
            for name in state["names"]:
                if "reload" in name:
                    clips = reload_clips.setdefault(name, set())
                    for choice in state.get("choices", []):
                        for clip in choice.get("clips", []):
                            clips.add(clip.get("clip", "?"))
    for name in sorted(reload_clips):
        print(f"{name} -> {', '.join(sorted(reload_clips[name]))}")

    print(f"5BE3C8ED -> {resolved.get(0x5BE3C8ED, 'non résolu')} "
          f"(présent dans les deux fichiers : "
          f"{all(0x5BE3C8ED in {int(h, 16) for s in iter_states(d) for h in s.get('hashes', [])} for d in docs)})")


if __name__ == "__main__":
    main()
