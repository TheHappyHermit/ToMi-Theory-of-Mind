"""Invalidate exactly the T2 rows whose vault citation this session repaired.

Same discipline as scripts/invalidate_repaired_t2.py, and for the same reason:
filtering by FILE would wipe dozens of still-valid rows, because a repaired
file holds many other adjudications. Only the identifier that was actually
rewritten can have changed verdict, so the key is (file, removed identifier).

Deleting the row is what makes the verifier re-resolve it. Rows it has already
judged are skipped, so a stale verdict would otherwise survive the vault edit
and quietly become the evidence.

THE REPAIRS THIS SESSION (all in the vault, all verified on disk):
  1. Consolidation/Adaptive-Forgetting.md
       removed 10.1038/379232a0          (phantom Anderson 1996 Nature)
       added   10.1037/0278-7393.20.5.1063 (Anderson, Bjork & Bjork 1994)
  2. Consolidation/Adaptive-Forgetting.md
       removed 10.1037/0033-295X.96.2.323 (McCloskey & Cohen 1989 -- real paper,
               Crossref has simply not deposited the 1989 record; row TITLED in
               place rather than dropped)
  3. AI-Architecture/Neuromorphic-Computing.md
       removed 10.1142/10269              (finance DOI, zero body mentions)

Only REMOVED identifiers are listed. Newly added identifiers have no row yet
and the verifier will create them.

Note on 10.1037/0033-295X.96.2.323: re-deriving it may well return
'unresolvable' again, because the underlying cause is a Crossref backfill gap
rather than a bad citation. That is the correct and honest outcome -- the row
now carries a real title, and the evidence table will show what the resolver
can actually see. Do NOT 'fix' that by deleting the citation.
"""
import json
import os
import sys

REPO = '/home/operator/hermes-brain'
VER = os.path.join(REPO, 'docs/audit/t2-verification.json')
ADJ = os.path.join(REPO, 'docs/audit/t2-adjudication.json')

STALE = [
    # 1. Anderson phantom -> replaced by a real 1994 paper
    ('Consolidation/Adaptive-Forgetting.md', 'doi:10.1038/379232a0'),
    # 2. McCloskey & Cohen row: titled in place, identifier unchanged
    ('Consolidation/Adaptive-Forgetting.md', 'doi:10.1037/0033-295X.96.2.323'),
    # 3. finance DOI dropped outright
    ('AI-Architecture/Neuromorphic-Computing.md', 'doi:10.1142/10269'),
    # 4-6. item C: three fabricated RIF citations dropped and marked.
    # The body CLAIMS were deliberately retained and labelled unverified --
    # only the identifiers are gone. These three are therefore expected to
    # disappear from the table rather than re-derive.
    ('Consolidation/Adaptive-Forgetting.md', 'doi:10.1177/2515245920933748'),
    ('Consolidation/Adaptive-Forgetting.md', 'doi:10.1037/xlm0000908'),
    ('Consolidation/Adaptive-Forgetting.md', 'doi:10.3758/s13421-014-0408-9'),
    # 7-15. The nine dead, uncited sources removed in the final phase. They
    # returned 404 on three routes proved live, and had zero body occurrences,
    # so removing them orphaned no claim. Each file also carries an in-file
    # dated audit note recording the removal.
    ('Belief-Revision/Belief-Revision-Safe-Belief-Updating.md', 'doi:10.1016/j.artint.2014.01.1475'),
    ('Cellular-Neuroscience/Pyramidal-Neuron-Apical-Dendrite-Computations.md', 'doi:10.1038/nn1199_989'),
    ('Executive-Control/Habit-Formation.md', 'doi:10.1037/a0046060'),
    ('Executive-Control/Habit-Formation.md', 'doi:10.1146/annurev-psych-010418-103041'),
    ('Knowledge-Representation/Cognitive-Maps-Beyond-Space.md', 'doi:10.1177/0956797615621371'),
    ('Learning/Desirable-Difficulties-Bjork.md', 'doi:10.1016/S0010-0277(85)80010-3'),
    ('Learning/Desirable-Difficulties-Bjork.md', 'doi:10.1016/j.memco.2008.10.002'),
    ('Learning/Desirable-Difficulties-Bjork.md', 'doi:10.1037/0096-3445.137.4.595'),
    ('Social-Cognition/Cognitive-Dissonance-and-Self-Justification.md', 'doi:10.1177/1754073917724993'),
    # 16-17. The final-phase repairs inside Adaptive-Forgetting. These are
    # REPAIRS, not removals: McCloskey & Cohen 1989 is a real body-cited work
    # that carried a non-resolving identifier, and is now cited correctly;
    # Rouder & Morey 2005 was fabricated and the identifier pointed at a
    # neighbouring article by Johnson & Busemeyer.
    ('Consolidation/Adaptive-Forgetting.md', 'doi:10.1037/0033-295X.96.2.323'),
    ('Consolidation/Adaptive-Forgetting.md', 'doi:10.1037/0033-295X.112.4.842'),
    # 18. The Friston 2017 phantom, removed and marked.
    ('Predictive-Processing/predictive-processing-and-active-inference.md',
     'doi:10.1093/brain/awag101/8519179'),
    # 19-20. My own unearned substitution of a dopamine/addiction paper as a
    # placeholder for the Friston reference. Removed after the verifier
    # correctly reported it as 'mismatch'. Recorded here so the mistake is
    # visible rather than quietly deleted.
    ('Predictive-Processing/predictive-processing-and-active-inference.md',
     'doi:10.1098/rstb.2008.0107'),
    # 21. The Encoding-Specificity row, as the pre-fix parser recorded it. TWO
    # independent defects shared one identifier: the verifier's regex used to
    # truncate it before the AID suffix (fixed in verify_t2_titles.py, pinned
    # by tests/test_t2_sici_doi.py), and the vault's own copy was missing the
    # trailing '0' of the year segment, (199812) rather than (1998120). The
    # corrected form is confirmed to resolve on Crossref and derives as
    # 'match'; the stale row below is the (199812) variant and must go, or the
    # table reports one file as both matching and unresolvable.
    #
    # NOTE: table keys are the FULL identifier, not a truncated prefix -- the
    # rows the cache holds are the complete 135-character strings, so an
    # exact-match invalidation list has to spell them out in full.
    ('Temporal-Cognition/Encoding-Specificity-Context-Dependent-Memory.md',
     'doi:10.1002/(SICI)1099-0720(199812)12:6<617::AID-ACP542>3.0.CO;2-5'),
    # 22. Anderson & Neely 1996. The vault asserted a chapter titled
    # 'Interference and retrieval in memory' in Metcalfe & Shimamura's
    # *Attribution of Memory* (pp. 107-133) under a Cambridge identifier whose
    # prefix is not itself registered. The real, resolvable record is an
    # Elsevier handbook chapter with a different title, host book and page
    # range. Repaired, with the discrepancy recorded in the file.
    ('Consolidation/Adaptive-Forgetting.md', 'doi:10.1017/CBO9780511628136.006'),
    # 23. Bjork & Bjork 1992 in Desirable-Difficulties. The cited title does not
    # exist, and the identifier's stem belongs to a different journal than the
    # one cited (its volume corresponds to a different decade). The real 1992
    # chapter is 'A new theory of disuse and an old theory of stimulus
    # fluctuation', in the Estes festschrift, and it has NO DOI -- absence
    # from Crossref and OpenAlex was confirmed rather than assumed. The
    # identifier is therefore gone for good and will never re-derive.
    ('Learning/Desirable-Difficulties-Bjork.md', 'doi:10.1037/0033-2909.124.4.421'),
]


def main():
    ver = json.load(open(VER, encoding='utf-8'))
    adj = json.load(open(ADJ, encoding='utf-8'))
    drop = {'%s::%s' % (f, i) for f, i in STALE}

    hit_v = sorted(drop & set(ver))
    hit_a = sorted(drop & set(adj))
    print('  keys to invalidate : %d' % len(drop))
    print('  present in verify  : %d' % len(hit_v))
    print('  present in adjud.  : %d' % len(hit_a))
    for k in hit_v:
        print('      %-58s %s' % (k.split('::')[0][-56:], ver[k].get('verdict')))

    missing = sorted(drop - set(ver))
    # Rows already absent were invalidated in an EARLIER run of this script.
    # That is normal, not drift: the script is intentionally re-runnable, and
    # the vault and the table legitimately differ for keys already handled.
    # A row is only 'drift' if it is absent AND we have never seen it here --
    # which cannot be determined from this table alone, so instead we require
    # that AT LEAST ONE key is present, and report the rest as already-done.
    already = [k for k in missing]
    if already:
        print('  already invalidated in an earlier run: %d' % len(already))
        for k in already:
            print('      %s' % k)
    # Require that AT LEAST ONE requested key was present, so a wholly stale
    # list is still caught as drift. A single run may legitimately find only
    # some of its keys already applied -- the list is cumulative across
    # repeated invocations, and demanding every key be present made a second
    # run impossible once earlier keys had been consumed by an earlier run.
    if not hit_v:
        raise SystemExit('refusing: none of the %d keys are present; the vault '
                         'and the evidence have drifted apart' % len(drop))

    if '--apply' not in sys.argv:
        print('  dry run; pass --apply')
        return

    before = len(ver)
    for d in drop:
        ver.pop(d, None)
        adj.pop(d, None)

    # refuse to write a table that lost more than it intended
    expected_drop = len(hit_v)
    if before - len(ver) != expected_drop:
        raise SystemExit('refusing: expected to drop %d rows, would drop %d'
                         % (expected_drop, before - len(ver)))

    json.dump(ver, open(VER, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    json.dump(adj, open(ADJ, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    print('  wrote tables: verify %d -> %d rows' % (before, len(ver)))
    print('  next: re-run scripts/verify_t2_titles.py (background, ~3.5 min)')


if __name__ == '__main__':
    main()
