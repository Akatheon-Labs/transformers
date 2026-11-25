#!/usr/bin/env python3
"""merge_certs.py TURBO_DIR OUT PART.json... : certificates recorded in parts (each part a group of the slice's test
files, all at one commit, after the same install) merged into one with Akatheon Turbo's own merge (poly/cert_merge in
the release archive: the parts' files are disjoint, so every test is kept as its part recorded it). The untracked
inputs' hashes are the union of the parts' (each part hashed the untracked files its own tests read); a path two parts
hashed differently is given a hash no file has, so every test that read it is selected. Prints what it merged."""
import json, os, subprocess, sys

turbo, out, parts = sys.argv[1], sys.argv[2], sys.argv[3:]
assert parts, "no parts"
loaded = [json.load(open(p)) for p in parts]
revs = {c["rev"] for c in loaded}
assert len(revs) == 1, f"parts recorded at different commits: {revs}"
seen = {}
for p, c in zip(parts, loaded):
    files = {n.split("::")[0] for n in c["tests"]}
    for f in files:
        assert f not in seen, f"{f} recorded in {seen[f]} and {p}"
        seen[f] = p
    print(f"{p}: {len(c['tests'])} tests, {len(files)} files, {len(c.get('untracked', {}))} untracked")
acc = parts[0]
for i, p in enumerate(parts[1:], 1):
    nxt = f"{out}.step{i}"
    subprocess.run([sys.executable, os.path.join(turbo, "poly", "ak_run.py"), "cert_merge", acc, p, nxt], check=True)
    if acc != parts[0]:
        os.remove(acc)
    acc = nxt
merged = json.load(open(acc))
untracked, conflicts = {}, []
for c in loaded:
    for path, h in c.get("untracked", {}).items():
        if path in untracked and untracked[path] != h:
            conflicts.append(path)
        untracked.setdefault(path, h)
for path in conflicts:
    untracked[path] = "parts-disagree"
merged["untracked"] = dict(sorted(untracked.items()))
want = sum(len(c["tests"]) for c in loaded)
assert len(merged["tests"]) == want, (len(merged["tests"]), want)
json.dump(merged, open(out, "w"))
if acc != parts[0]:
    os.remove(acc)
print(f"merged: {len(merged['tests'])} tests from {len(parts)} parts at {merged['rev'][:10]}, {len(untracked)} untracked"
      f" ({len(conflicts)} hashed differently by two parts: {conflicts[:5]})")
