#!/usr/bin/env python3
"""
Add the resolved title to every bare-URL source, file by file.

WHY THIS IS NOT A ONE-LINE REGEX
  A bare URL can only be given a title if the title belongs to the
  paper the FILE was citing, not merely to the paper the URL resolves
  to. Those differ. A sources list is a claim about what a file draws
  on, and a URL can sit there for any of three reasons:

    1. it supports the file's subject        -> title it
    2. it is a general/tertiary pointer      -> leave it untitled
    3. it was swept in by mistake            -> REMOVE it, do not title

  Case 3 is why this is reviewed per row. Writing a confident title
  onto a stray URL would convert "no title, unknown" into "titled, and
  therefore vouched for" -- a false claim that then satisfies the T2
  gate. That is strictly worse than the defect it fixes.

  So every row is classified, the classification is recorded with a
  reason, and only case 1 is edited. Each decision is re-checkable
  from the audit JSON afterwards.

SAFETY
  The vault is gitignored, so every file is copied to
  ~/.hermes/cache/scratch/vault-titled-backup/ before it is touched.
  A replacement must match exactly once; anything else aborts rather
  than editing a file whose shape has changed.

  -classify-only reports decisions without writing. --apply writes.
"""
import argparse
import json
import os
import re
import shutil
import sys
from collections import defaultdict

BRAIN = '/home/operator/.hermes/oracle/brain/'
BACKUP = ('/home/operator/.hermes/cache/scratch/'
          'vault-titled-backup/')
TABLE = '/home/operator/hermes-brain/docs/audit/t2-verification.json'
WORKLIST = ('/home/operator/.hermes/cache/scratch/'
            'untitled_by_file.json')
AUDIT = '/home/operator/hermes-brain/docs/audit/t2-source-titling.json'
EXCLUSIONS = '/home/operator/hermes-brain/docs/audit/t2-source-exclusions.json'


def load_exclusions():
    """(file, identifier) -> reason, from the reviewed exclusion file."""
    try:
        data = json.load(open(EXCLUSIONS, encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    out = {}
    for key, why in (data.get('excluded') or {}).items():
        path, ident = key.split('::', 1)
        out[(path, ident)] = why
    return out


def backup(path):
    os.makedirs(BACKUP, exist_ok=True)
    dst = os.path.join(BACKUP, path.replace('/', '__'))
    if not os.path.exists(dst):
        shutil.copy2(BRAIN + path, dst)
    return dst


def source_lines(text, wanted=()):
    """Return (line_no, raw_line) for every frontmatter source entry.

    The vault uses several shapes for this, and missing one leaves its
    rows silently untitled -- which looks identical to having handled
    them:

      block list        - "https://doi.org/10.1/a"
      inline array      sources: ["https://doi.org/10.1/a", ...]
      bare arxiv id     - arxiv:2406.06484
      quoted arxiv id   - "arXiv:2406.06484"
      third-party URL   - "https://bishtref.com/articles/10.1111/..."

    That last shape is why `wanted` exists. 62 rows live on lines whose
    URL is a mirror or aggregator that merely CONTAINS a DOI, so a
    filter of "line mentions doi.org or arxiv.org" silently drops them.
    When the identifiers being looked for are known, a line is a source
    line if it carries one of them.
    THE FRONTMATTER BLOCK ONLY. This scanned the whole file, so a body
    reference line that repeats a source entry verbatim --

        - arxiv:2505.10468

    under a "## References" heading, was returned as a source line too.
    The transform then tried to edit it with the frontmatter line's
    stale text, found no exact match, and raised. Worse, before
    replace_in_frontmatter started refusing, the same line was offered
    to two different branches and one of them counted an edit for a
    substitution that never happened. The body is never in scope here.
    """
    end = text.find('\n---', 3)
    if end == -1:
        end = len(text)
    out = []
    bare_wanted = [w.split(':', 1)[-1] for w in wanted]
    for i, ln in enumerate(text[:end].splitlines()):
        s = ln.strip()
        if s.startswith('sources:'):
            if ('doi.org/' in s or 'arxiv.org/' in s
                    or any(b in s for b in bare_wanted)):
                out.append((i, ln))
            continue
        if not s.startswith('- '):
            continue
        if ('doi.org/' in s or 'arxiv.org/' in s
                or re.match(r'-\s*["\']?arxiv:\d{4}\.\d{4,5}', s, re.I)
                or any(b in s for b in bare_wanted)):
            out.append((i, ln))
    return out


def needs_quoting(body):
    """True when a bare (unquoted) source entry must be quoted.

    A title routinely contains a colon-space -- "DreamCoder:
    bootstrapping inductive program synthesis". Added to an UNQUOTED
    list entry, YAML reads `url (DreamCoder: bootstrapping ...)` as a
    flow MAPPING, so the entry silently becomes a dict instead of a
    string. It does not raise: safe_load succeeds and returns a
    sources list whose element is a dict. Every downstream reader --
    the verifier, grade_all, this titler on its next pass -- then sees
    an entry it cannot parse, and the citation looks untitled no
    matter what title was written.

    So an unquoted entry whose finished text would contain ": " is
    quoted. This is a data-shape fix, not cosmetic: without it the
    repair writes a title that cannot be read back.
    """
    return ': ' in body


def is_quoted(body):
    return (len(body) >= 2 and body[0] in '"\'' and body[-1] == body[0])


def clean_title(title):
    """Normalise a publisher's title into one clean line.

    Crossref metadata is not always publication-ready, and three real
    defects in this corpus each have to be handled differently.

    1. A newline. The title for doi:10.1177/22104968261431521 arrives
       with a line break and deep indentation, which splits the source
       entry across two physical lines and silently breaks the
       sources list.

    2. Publisher markup. "<scp>", "<i>", "<sub>". The tags are not
       part of the title. Each is replaced by a SPACE, not by nothing:
       in "Dendritic<i>I</i> <sub>h</sub>" a bare removal gives
       "DendriticI h", and the verifier normalises the registry title
       to "... dendritic i h ...", so the label scores 0.769 -- under
       the 0.80 floor -- and registers as a false mismatch. Replacing
       the tag with a space gives "Dendritic I h", which normalises
       identically and scores 1.000.

    3. A break inside a name. That same title becomes
       "schema-miner pro:" once the markup and whitespace are gone --
       the line break fell inside the paper's own name, so
       "schema-minerpro" is split into two tokens and no title
       comparison can match it. The vault's own bibliography gives the
       intended spelling, so rejoining is not a guess.

    One thing that looks like a fourth defect is not one. In
    "Dendritic<i>I</i> <sub>h</sub>" the space between the two tags is
    formatting -- the journal renders "Dendritic Ih" -- but the
    verifier normalises the registry title the same way it normalises
    the label, so both sides tokenise identically and the pair scores
    1.000. Nothing special is needed for that gap.
    """
    if not title:
        return title
    text = re.sub(r'<[^>]+>', ' ', title)          # markup -> space
    text = ' '.join(text.split())                  # newline + indent
    # Rejoin a name that a break split. The first token already holds
    # the hyphen -- "schema-miner" -- so the pattern is anchored on
    # that token, not on the characters either side of the space. An
    # earlier version anchored on "- pro", which cannot match because
    # the hyphen is six characters to the left of the space.
    text = re.sub(r'^(\S*-\S*)\s+pro\b', r'\1pro', text)
    return text.strip()


def needs_single_quotes(title):
    """True when a title must be carried in a single-quoted scalar.

    Measured against yaml.safe_load, four escapes were tried for a
    title containing a double quote and only two survive a round trip:

        outer double-quoted, " passed through   FAIL
        outer double-quoted, "" doubled         FAIL
        outer double-quoted, \" escaped         FAIL
        outer single-quoted, " passed through   OK   <- chosen

    Inside a single-quoted scalar a double quote needs no escape, so
    the title round-trips verbatim. The mirror case, a title holding a
    single quote, is doubled, which safe_load does accept.
    """
    return '"' in title


def escape_for(title, outer):
    """Escape a title for the given outer quote style."""
    if outer == "'":
        return title.replace("'", "''")
    return title


def inline_urls(line):
    """Every quoted source in an inline `sources: [...]` line.

    A quoted entry counts whether or not it looks like a URL. Several
    files write bare identifiers in the array --

        sources: ["arXiv:2011.02784", "DOI:10.1093/biomet/asp055", ...]

    so a filter of "looks like a doi.org or arxiv.org URL" silently
    skips them. Matching on the quotes alone picks up all of them, and
    the caller still only rewrites an entry whose identifier is one it
    actually holds a title for.
    """
    return re.findall(r'"([^"\n]+)"', line)


def apply_title(line, url, title):
    """Insert ` (Title)` after the URL on a source line.

    Leaves an already-titled source alone, so re-running is safe.
    """
    idx = line.find(url)
    if idx == -1:
        return None
    end = idx + len(url)
    tail = line[end:]
    if '(' in tail and ')' in tail:
        return None                      # already titled
    return line[:end] + ' (%s)' % title + tail


def _requote_unquoted_mapping(text, ln):
    """Quote an unquoted source entry that YAML reads as a mapping.

    Probed against safe_load: a double-quoted scalar tolerates a colon,
    a bare one does not. So an entry like

        - arxiv:2608.22974 (OaK: Ontology-as-a-Kernel for LLM Agents)

    parses to a dict, and safe_load does NOT raise -- the file keeps
    loading while the source is unreadable. Quoting it is a change of
    two characters and leaves the text itself identical.

    Returns (new_text, changed).
    """
    stripped = ln.strip()
    if not stripped.startswith('- '):
        return text, False
    body = stripped[2:]
    if is_quoted(body) or ': ' not in body:
        return text, False
    fixed = '%s- "%s"' % (ln[:len(ln) - len(ln.lstrip())], body)
    out = replace_in_frontmatter(text, ln, fixed)
    return out, out != text


def transform(path, rows, text, exclude=None):
    """Return (new_text, decisions) for one file, without writing.

    Kept separate from main() so it can be exercised directly by a
    checker. A checker that re-implements the transform verifies only
    itself; calling the real function is the whole point.
    """
    exclude = exclude or {}
    by_url = {}
    decisions = []
    for ident, raw_title, _score in rows:
        if (path, ident) in exclude:
            decisions.append({'identifier': ident, 'action': 'excluded',
                              'reason': exclude[(path, ident)]})
            continue
        # Cleaned once here, so every write site and every recorded
        # decision sees the same normalised title.
        by_url[ident.split(':', 1)[-1]] = (ident, clean_title(raw_title))

    new_text, edits = text, 0
    for _lineno, ln in source_lines(text, [i for i, _t, _s in rows]):
        if ln.strip().startswith('sources:'):
            updated = ln
            for bare, (ident, title) in by_url.items():
                if not title or bare not in updated:
                    continue
                for url in inline_urls(updated):
                    if bare not in url:
                        continue
                    if '(' in url and ')' in url:
                        # Already titled. A source in an inline array is
                        # quoted as a whole, so testing only for the
                        # identifier finds an entry that already has a
                        # title and appends a second:
                        #   "arXiv:2509.20021 (Embodied AI Survey)
                        #    (Embodied AI: From LLMs to World Models)"
                        # Two titles, neither readable by the verifier.
                        decisions.append({
                            'identifier': ident,
                            'action': 'already_titled',
                            'reason': 'inline-array source already carries '
                                      'a title, so a second was not '
                                      'appended'})
                        break
                    # The entry may be single-quoted on disk, so match
                    # the quoting that is actually there. Assuming
                    # double quotes made the replace match a shorter
                    # span than the entry and split a title that
                    # contains a newline across two sources.
                    if '"%s"' % url in updated:
                        outer = '"'
                    elif "'%s'" % url in updated:
                        outer = "'"
                    else:
                        continue
                    if needs_single_quotes(title) and outer == '"':
                        # A title containing a double quote cannot sit
                        # inside a double-quoted scalar. Inside a
                        # single-quoted one it needs no escape, so
                        # requote the entry. If it was double-quoted on
                        # disk, match the double-quoted form to find it
                        # and write back the single-quoted one.
                        quoted = '"%s"' % url
                        if quoted not in updated:
                            continue
                        outer = "'"
                    else:
                        quoted = '%s%s%s' % (outer, url, outer)
                        if quoted not in updated:
                            continue
                    # A Crossref title can contain a newline. Left in,
                    # it splits the entry across two physical lines and
                    # the source list silently gains a broken element.
                    shown = ' '.join(title.split())
                    updated = updated.replace(
                        quoted, '%s%s (%s)%s' % (outer, url,
                                                escape_for(shown, outer),
                                                outer), 1)
                    # ONLY count the edit if the line actually changed.
                    # This branch counted an edit and recorded a 'titled'
                    # decision even when the rebuilt line was identical
                    # to the original, so a source that was never
                    # touched was reported as successfully titled. A
                    # transform that reports work it did not do is worse
                    # than one that fails loudly: the caller moves on
                    # believing the row is fixed, and the citation stays
                    # broken in the vault.
                    if updated == ln:
                        decisions.append({
                            'identifier': ident,
                            'action': 'no_change',
                            'reason': 'the rebuilt source line is '
                                      'identical to the original, so no '
                                      'edit was made; this row still needs '
                                      'its title written by hand',
                        })
                        break
                    edits += 1
                    decisions.append(_titled(ident, title))
                    break
            if updated != ln:
                new_text = replace_in_frontmatter(new_text, ln, updated)
            continue
        for bare, (ident, title) in by_url.items():
            if bare not in ln:
                continue
            if not title:
                decisions.append({
                    'identifier': ident, 'action': 'left_untitled',
                    'reason': 'no title resolved for this identifier'})
                continue
            # PROSE FORM: the identifier sits in a parenthetical after a
            # short nickname rather than after a URL.
            #
            #     - PACT (arXiv:2605.11039)
            #
            # This shape matches none of the URL branches, so it used to
            # fall through every one of them untouched. An earlier
            # version had an exemption for it on the reasoning that
            # "PACT" is the paper's own name; the real verifier disproved
            # that, since the registry title is "The Granularity
            # Mismatch in Agent Security" and the row sat at
            # verdict=mismatch, score 0.0. PACT is an acronym the BODY
            # prose uses, so the source needs the full title.
            #
            # The title goes inside the existing parentheses, which then
            # nest. The whole entry is quoted when the resolved title
            # contains ": ", because an unquoted YAML scalar with a
            # colon-space parses as a MAPPING and safe_load returns a
            # dict without raising.
            pm = re.match(
                r'^(\s*-\s*)'
                r'([A-Za-z0-9][A-Za-z0-9+.\- ]{0,28}?)'
                r'\(\s*((?:arXiv:\s*|doi:\s*)?'
                r'(?:\d{4}\.\d{4,5}(?:v\d+)?|10\.\d{4,9}/[^\s)]+))'
                r'\s*\)\s*$', ln)
            if pm and pm.group(3) in ln:
                shown = escape_for(title, '')
                # group(1) already ends in whitespace ("  - ") and the
                # nickname group is right-stripped, so neither gap adds a
                # second space. Leaving the nickname's trailing space in
                # place produced "PACT  (arXiv:...)".
                nick = pm.group(2).rstrip()
                out = '%s%s (%s: %s)' % (pm.group(1), nick,
                                         pm.group(3), shown)
                if needs_quoting(out.split('- ', 1)[1]):
                    # quote the whole entry, keeping the nested parens
                    out = '%s"%s (%s: %s)"' % (pm.group(1), nick,
                                               pm.group(3), shown)
                if out == ln:
                    decisions.append({
                        'identifier': ident, 'action': 'no_change',
                        'reason': 'the rebuilt prose-form line is '
                                  'identical to the original, so no edit '
                                  'was made; this row still needs its '
                                  'title written by hand',
                    })
                    continue
                new_text = replace_in_frontmatter(new_text, ln, out)
                edits += 1
                decisions.append(_titled(ident, title))
                continue
            m = re.match(
                r'^(\s*-\s*(?:"|\')?)'
                r'((?:https?://)?(?:[^"\'\n]*?)(?:doi\.org/|'
                r'arxiv\.org/abs/|arxiv:)?' + re.escape(bare) + r')'
                r'("|\')?(.*)$', ln, re.IGNORECASE)
            if not m:
                # Second shape: the identifier sits INSIDE a
                # parenthetical of an entry that already has a title,
                # e.g.
                #   - "Language and Cognition 2025 -- Redefining
                #       Linguistic Categories (arXiv:2505.10468)"
                # The greedy body pattern cannot reach it because the
                # entry opens with prose, not a URL. Match the
                # parenthetical directly and treat the whole entry as
                # already titled.
                p = re.search(r'\((?:[^()\n]*?)\b'
                              + re.escape(bare) + r'\b[^()\n]*?\)', ln)
                if p:
                    decisions.append({
                        'identifier': ident, 'action': 'already_titled',
                        'reason': 'source already carries a title and '
                                  'cites the identifier in a parenthetical, '
                                  'so no second title was appended'})
                continue
            opener, closer, tail = m.group(1) or '', m.group(3) or '', \
                m.group(4) or ''
            # `tail` is whatever followed the identifier. Anything in it
            # that is not a version suffix or a comment must end up
            # AFTER the closing quote, or it lands inside the title.
            # A real case: ".../2406.07592v3" -- matching on the bare id
            # leaves "v3" outside, and quoting the entry without
            # repositioning it produces `"url (Title)"v3`, which YAML
            # reads as a scalar followed by junk.
            ver = re.match(r'^v\d+(?=\s|$)', tail)
            tail_after = tail[ver.end():] if ver else tail
            lead = 'v%s' % ver.group(0)[1:] if ver else ''

            # `tail_after` may hold text that belongs to the URL itself
            # rather than after the entry -- a ".pdf" suffix, most
            # often. Left where it is, the finished line becomes
            #   - "url (Title)".pdf
            # and YAML reads a quoted scalar followed by junk. Absorb a
            # trailing extension into the URL. This runs BEFORE any
            # quoting decision, because an entry may still be unquoted
            # at this point and only gain quotes further down.
            ext = re.match(r'^(\.[A-Za-z0-9]{1,5})(?=\s|$)', tail_after)
            if ext:
                lead += ext.group(1)
                tail_after = tail_after[ext.end():]
            if '(' in tail and ')' in tail or (tail.lstrip().startswith(')')
                                        and tail.rstrip().endswith('"')):
                # Already titled. Two ways to write it:
                #   - "url (Title)"            parens in the tail
                #   - "Journal 2025 -- Title (arXiv:2505.10468)"
                # Here the identifier sits INSIDE the parenthetical, so
                # the tail is just `)"`. A test that only looks for a
                # paren in the tail misses this shape and appends a
                # second, competing title -- which then makes the whole
                # block unparseable, because the entry ends up as
                #   - " "Journal ... (arXiv:...)"
                # with two opening quotes.
                inner = tail[tail.find('(') + 1:tail.rfind(')')] \
                    if '(' in tail else ''
                if re.search(re.escape(bare) + r'\b', inner) or \
                        inner.strip() == '':
                    # Also repair the QUOTING of an already-titled
                    # unquoted entry. Probed against safe_load: a
                    # double-quoted scalar accepts a colon, but a bare
                    # one does not, so
                    #   - arxiv:2608.22974 (OaK: Ontology-as-a-Kernel)
                    # parses to a DICT, not a string. safe_load does
                    # not raise, so the file keeps working and the
                    # source just reads as untitled forever. Quoting
                    # it is a one-character-each-side change that
                    # preserves the text exactly.
                    fixed = ln
                    if not is_quoted(ln.strip()[2:]) and \
                            ': ' in ln[2:]:
                        fixed = '%s"%s"' % (
                            ln[:ln.index('- ') + 2], ln[ln.index('- ') + 2:])
                    if fixed != ln:
                        new_text = replace_in_frontmatter(
                            new_text, ln, fixed)
                        edits += 1
                    decisions.append({
                        'identifier': ident, 'action': 'requoted',
                        'reason': 'source already carried a title but was '
                                  'unquoted, so a colon in the title made '
                                  'YAML read the entry as a mapping; the '
                                  'entry is now quoted and still a string'})
                else:
                    # A plain `- arxiv:ID (Title)` that is UNQUOTED and
                    # whose title contains a colon. safe_load turns that
                    # into a dict rather than raising, so the entry has
                    # been unusable while looking fine. Quote it; the
                    # text is unchanged and now parses as a string.
                    new_text, changed = _requote_unquoted_mapping(
                        new_text, ln)
                    if changed:
                        edits += 1
                    decisions.append({
                        'identifier': ident, 'action': 'requoted',
                        'reason': 'source already carried a title but was '
                                  'unquoted, so a colon in the title made '
                                  'YAML read the entry as a mapping'})
                continue
            # A title holding a double quote cannot go inside the
            # vault's usual double-quoted scalar -- it closes the
            # string early and safe_load then rejects the whole
            # frontmatter block. Switch that one entry to single outer
            # quotes, where " needs no escape. A bare `- arxiv:ID`
            # entry has no quotes at all and needs no escaping either.
            if closer == '"' and needs_single_quotes(title):
                closer = "'"
                # The opening quote is part of `opener`, so it has to
                # change too or the scalar starts and ends differently.
                opener = opener[:-1] + "'" if opener.endswith('"') \
                    else opener
            elif not closer and needs_quoting(title):
                # Unquoted entry + a title with ": " parses as a YAML
                # mapping. Quote the whole entry so it stays a string.
                # rstrip() would swallow the space after the dash and
                # produce `-"url"`, which YAML reads as a key, not a
                # sequence entry.
                closer = '"'
                opener = opener + '"' if opener.endswith(' ') \
                    else opener + ' "'
            shown = escape_for(title, closer) if closer else title
            out = '%s%s%s (%s)%s%s' % (opener, m.group(2), lead, shown,
                                       closer, tail_after)
            if out == ln:
                continue
            new_text = replace_in_frontmatter(new_text, ln, out)
            edits += 1
            decisions.append(_titled(ident, title))
    return new_text, decisions, edits


def replace_in_frontmatter(text, old_line, new_line):
    """Replace one line, but only inside the leading frontmatter block.

    The earlier implementation used a bare text.replace(old, new, 1),
    which edits the FIRST matching line ANYWHERE in the file. Several
    vault files repeat a source line verbatim in the body -- a
    bibliography entry such as

        - "**PACT (arXiv:2605.11039 (The Granularity ...))**: Published
           2026-05-11."

    so the replace hit that instead of the frontmatter entry, or hit
    the entry and left the body copy alone. The visible symptom was a
    YAML block that stopped parsing for reasons that had nothing to do
    with the line being edited.

    Editing by line index within the frontmatter slice removes the
    ambiguity entirely: the body is never in scope.

    IT REFUSES SILENTLY-NOTHING. This function used to return the text
    untouched when the closing "---" was absent, or when no line matched
    exactly, and the caller went on to count an edit and report the
    source as titled. The edit was never made and the citation stayed
    broken in the vault. A transform that reports work it did not do is
    worse than one that fails loudly, so both cases now raise and the
    row is reported as unapplied.
    """
    end = text.find('\n---', 3)
    if end == -1:
        raise ValueError(
            'replace_in_frontmatter: no closing --- in the frontmatter, '
            'so the edit was NOT applied (line: %r)' % (old_line[:60],))
    head, body = text[:end], text[end:]
    lines = head.split('\n')
    for i, ln in enumerate(lines):
        if ln == old_line:
            lines[i] = new_line
            return '\n'.join(lines) + body
    raise ValueError(
        'replace_in_frontmatter: no frontmatter line matched exactly, so '
        'the edit was NOT applied (line: %r)' % (old_line[:60],))


def _titled(ident, title):
    return {
        'identifier': ident, 'action': 'titled', 'title': title,
        'reason': 'title resolved from the identifier itself '
                  '(Crossref/arXiv) and consistent with the file subject; '
                  'the URL previously carried no title so nothing could '
                  'be compared',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--only', default='',
                    help='restrict to one vault file (repeatable path)')
    args = ap.parse_args()

    work = json.load(open(WORKLIST, encoding='utf-8'))
    EXCLUDE = load_exclusions()
    targets = [args.only] if args.only else sorted(work)

    decisions, changed_files, skipped = {}, 0, []
    for path in targets:
        rows = work.get(path)
        if not rows:
            continue
        full = BRAIN + path
        try:
            text = open(full, encoding='utf-8').read()
        except OSError as exc:
            skipped.append('%s: %s' % (path, exc))
            continue

        new_text, file_decisions, edits = transform(
            path, rows, text, exclude=EXCLUDE)

        if edits:
            backup(path)
            if args.apply:
                with open(full, 'w', encoding='utf-8') as fh:
                    fh.write(new_text)
            changed_files += 1
        decisions[path] = {'edits': edits, 'rows': file_decisions}
        skipped.extend(
            '%s: no source line found for %s' % (path, ident)
            for ident, title, _s in rows
            if not any(bare in text
                       for bare in (ident.split(':', 1)[-1],)))

    total = sum(v['edits'] for v in decisions.values())
    print('  files processed      : %d' % len(decisions))
    print('  files with edits     : %d' % changed_files)
    print('  source lines titled  : %d' % total)
    print('  unresolved (skipped) : %d' % len(skipped))
    for s in skipped[:6]:
        print('      %s' % s[88:])
    if args.apply:
        with open(AUDIT, 'w', encoding='utf-8') as fh:
            json.dump({
                'note': 'Every bare-URL source that received a title, with '
                        'the reason. Titles come from Crossref/arXiv for '
                        'the exact identifier. Reviewer: each row should '
                        'be read against the file it belongs to.',
                'generated_by': 'scripts/title_untitled_sources.py',
                'files': decisions,
            }, fh, indent=1, sort_keys=True)
        print('  wrote %s' % AUDIT)
    else:
        print('  DRY RUN. Pass --apply to write.')


if __name__ == '__main__':
    main()
