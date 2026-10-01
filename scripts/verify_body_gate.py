"""The body gate is the LAST line of defence before a bulk write, so its
own normalization must be controlled. A too-greedy pattern there would
strip prose on BOTH sides and report a clean pass while the transform ate
knowledge.

Test that strip() removes citation syntax and leaves prose alone, for all
six old syntaxes and the new one."""
import importlib.util, io, contextlib, os, sys

HERE = '/home/operator/hermes-brain/scripts'
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    spec = importlib.util.spec_from_file_location(
        'm32', os.path.join(HERE, 'citation_migrate_32.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

# Pull strip() out of body_gate by re-running it on a probe and inverting:
# simpler to reimplement the call and compare gate verdicts.
def gate(orig, new):
    return m.body_gate(orig, new, 'probe')


CASES = []


def case(name, orig, new, want_pass):
    ok, why = gate(orig, new)
    CASES.append((name, ok == want_pass, ok, want_pass, why))


PROSE = ('A real sentence about dendritic computation, with a comma and a\n'
         'second line of prose that must survive entirely intact.\n')

# 1. A transform that changes NOTHING must pass.
case('no-op passes', PROSE, PROSE, True)

# 2. Each old syntax -> new definition, must pass.
for label, old_line, new_line in [
    ('bold',      '- **[1]** Anderson, J. R. (2007). *Systems research*. *Psychological Review*.',
                 '[^anderson-systems]: Anderson, J. R. (2007). *Systems research*. *Psychological Review*.'),
    ('bold-nb',   '**[2]** Fuster, E. (2009). Memory. *Science*.',
                 '[^fuster-memory]: Fuster, E. (2009). Memory. *Science*.'),
    ('bullet-br', '- [3] Large Ontology Models -- arXiv 2602.00029',
                 '[^large-ontology]: Large Ontology Models -- arXiv 2602.00029'),
    ('br',        '[4] OntoLLM -- ESWA 2026',
                 '[^ontollm]: OntoLLM -- ESWA 2026'),
    ('wikilink',  '[[5]] George, D. (2009). Micro-circuits. *PLOS Comp Biol*.',
                 '[^george-micro]: George, D. (2009). Micro-circuits. *PLOS Comp Biol*.'),
    ('bare',      '6. Honey, O. J., et al. (2012). ECoG. *Nature Neuroscience*.',
                 '[^honey-ecog]: Honey, O. J., et al. (2012). ECoG. *Nature Neuroscience*.'),
]:
    orig = PROSE + '\n## Sources\n' + old_line + '\n'
    new = PROSE + '\n## Sources\n' + new_line + '\n'
    case(f'{label} list -> footnote passes', orig, new, True)

# 3. A body marker -> footnote use, must pass.
orig = PROSE + 'The finding [[1]] holds.\n## Sources\n- [1] A real paper. arXiv 2601.00001\n'
new = PROSE + 'The finding [^a-real] holds.\n## Sources\n[^a-real]: A real paper. arXiv 2601.00001\n'
case('body marker -> footnote passes', orig, new, True)

# 4. A DELETED prose line must FAIL. This is the load-bearing control.
#    The first version of this case compared a bare list line against its
#    footnote equivalent, which is a NO-OP transform: both sides strip to
#    the same text, so it passed and taught nothing. A real deletion has to
#    drop actual PROSE while the citation syntax changes around it.
orig = (PROSE + 'A distinct third sentence of real knowledge [[1]].\n'
        '## Sources\n- [1] A real paper. arXiv 2601.00001\n')
new = (PROSE + '## Sources\n[^a-real]: A real paper. arXiv 2601.00001\n')
case('dropped prose sentence FAILS', orig, new, False)

# 5. An ALTERED prose line must FAIL.
orig = PROSE + 'Second sentence that matters [[1]].\n## Sources\n- [1] Paper. arXiv 2601.1\n'
new = PROSE.replace('matters', 'MUTATED') + 'Second sentence [[^paper]].\n## Sources\n[^paper]: Paper. arXiv 2601.1\n'
case('altered prose FAILS', orig, new, False)

# 6. An inline-link number dropped must PASS (that is the INLINE transform).
orig = 'Cut failures 49% [[1]](https://ex.org/p) this year.\n'
new = 'Cut failures 49% (https://ex.org/p) this year.\n'
case('inline number dropped passes', orig, new, True)

# 7. An inline link whose URL is destroyed must FAIL.
orig = 'Cut failures 49% [[1]](https://ex.org/p) this year.\n'
new = 'Cut failures 49% ( this year.\n'
case('destroyed inline URL FAILS', orig, new, False)

failed = [c for c in CASES if not c[1]]
for name, ok, got, want, why in CASES:
    print(f'  {"ok  " if ok else "FAIL"} {name}: got pass={got} want={want}'
          + (f'  {why[:60]}' if not ok and why else ''))
print(f'\n  {len(CASES) - len(failed)}/{len(CASES)} body-gate controls passed')
sys.exit(1 if failed else 0)
