# What a numeric confidence value actually means — and what 0.85 should become

Research report, 2026-09-28. Research only: no wiki file, schema, or commit was
touched in producing this.

## TL;DR

The single most important finding: **a number is not a probability unless somebody
measured that it is one.** Every system surveyed below falls into exactly two
camps, and the distinction is worth more than the specific range of any of them.

- **Measured probabilities.** FEVER-style claim verification, ORES. A model
  trained on human-labelled outcomes, with a calibration curve. Ask the
  calibration question and you get an answer.
- **Conventions.** RRF fusion scores, BM25, reranker scores, Weaviate
  `certainty`, VADER's 0.05. These are *ordering devices*. They were produced
  by an arithmetic formula, not by a success rate.

`confidence_reported: 0.85` in this corpus is in the second camp, and nothing in
the corpus or in the schema's own history shows it was ever validated against
outcomes. The rubric that produced it is not recorded anywhere. The
recommendation in §6 follows from that: **do not convert 0.85 into a band at
all.** Convert the *evidence*, and let the band fall out of that.

There is a live failure mode here, documented in §5: a miscalibrated numeric
confidence shown to a decision-maker causes measurable over-reliance, and the
reader cannot detect the miscalibration. If a downstream LLM reads `0.85` and
treats it as a fact, that is the documented behaviour, not a hypothetical.

---

## 1. Table: system → score type → range → documented meaning

| System | Score | Type | Range | Documented meaning | Comparable across systems? |
|---|---|---|---|---|---|
| Azure AI Search (hybrid) | `@search.score` | RRF fusion | Unbounded; each query contributes ≈`1/k` | "Reciprocal rank score" `1/(rank + k)`, summed over result lists. Pure rank position.[1] | **No.** Ceiling depends on how many queries were fused — three fused queries score higher than two.[1] |
| Azure AI Search (semantic) | `@search.rerankerScore` | Neural reranker | **0.00 – 4.00** | "Semantic relevance of the document for the given query"; 4.0 = fully answers the question, 0.0 = irrelevant.[1][2] | **No.** Microsoft warns the distribution "can exhibit slight variations due to conditions at the infrastructure level" and that ranking-model updates shift it — do not set fine-grained thresholds.[2] |
| Pinecone (inference rerank) | `score` | Reranker relevance | **0 – 1** | "Normalized between 0 and 1, the `score` represents the relevance of a passage to the query, with scores closer to 1 indicating higher relevance."[4] | **No.** Normalisation is per-call and per-model; the docs' own example returns 0.048 and 0.0076 for a good and a bad match.[4] |
| Pinecone (vector search) | `score` | Cosine/dot similarity | Cosine ≈ [-1, 1] | Similarity, not relevance probability. | **No.** |
| Weaviate `certainty` | `certainty` | **Normalised distance** | 0 ≤ c ≤ 1 *for cosine only* | "normalize the distance score into a value between 0 and 1, where 1 would represent identical vectors and 0 would represent opposite vectors." Weaviate now **prefers `distance` over `certainty`**, because "this concept is however unique to `cosine` distance. With other distance metrics, scores may be unbounded."[5] | **No.** The vendor's own deprecation is the strongest available evidence that a 0–1 normalised score is not a probability. |
| Vespa | rank score | Rank-profile expression | Unbounded, author-defined | A named collection of ranking logic; `first-phase { expression: ... }` sets the order. Scores are *composed by the application author* from rank features.[6][7] | **No.** The scale is literally whatever the schema author wrote. |
| Vespa `closest()` | `closeness()` | Explicit transform | (0, 1] | `closeness = 1.0 / (1.0 + distance)` — a **named, documented transform** that maps distance into (0,1]. This is what a bounded score looks like when someone is honest about it: a formula, not a rate.[6] | No, but at least the transform is stated. |
| Elasticsearch / Lucene BM25 | `_score` | Term-weight sum | Unbounded positive float | "The relevance score of each document is represented by a positive floating-point number called the `_score`. The higher the `_score`, the more relevant the document." A query normalisation factor exists but "is an attempt to normalize a query so that the results from one query may be compared with the results of another" — an *attempt*, not a guarantee.[26] | **No.** Unbounded, query-dependent, corpus-dependent. Not a probability. |
| ORES (edit / article quality) | `probability` | Trained classifier output | 0 – 1, per class | Real probabilities: `{"prediction": "FA", "probability": {"FA": 0.72, "C": 0.028, ...}}` — a softmax over classes from a model trained on human labels.[16] | **Within** a model+version only. A model update invalidates old scores — which is exactly why Wikimedia versions every model.[16][17] |
| FEVER claim verification | class score | 3-way classifier | 0 – 1 over {SUPPORTS, REFUTES, NEI} | Trained against human labels; scores are usable as probabilities if calibrated.[18][19] | **Within** a model only. |

**The pattern.** The only scores in this table with a defensible probabilistic
reading (ORES, FEVER) are the only ones produced by a *classifier trained on
human labels*. Everything else is arithmetic on rank or distance. The 0–1 shape
is common to both camps and therefore tells you nothing about which one you are
looking at.

### 1a. LangChain / Pinecone reranker convention

The LangChain ecosystem's rerankers (`CohereRerank`, `CrossEncoderRerank`)
return a `relevance_score` and document it as the underlying model's output, not
a probability. `[unverified]` — I did not obtain a primary LangChain doc page
for this in this pass; the underlying claim rests on the Pinecone and Cohere
model documentation above, which describes the same convention. Worth a
follow-up fetch if the reranker is ever wired in.

---

## 2. Band thresholds: what the cut-offs actually are

### 2.1 Conventional but unjustified

**VADER.** The canonical, widely copied thresholds:

- positive: `compound >= 0.05`
- neutral: `-0.05 < compound < 0.05`
- negative: `compound <= -0.05`[13]

The project's own README is careful about provenance: it says these are
"**typical threshold values (used in the literature cited on this page)**", and
attributes them to convention rather than derivation.[13] The compound score is
normalised to [-1, +1] by `x / sqrt(x² + α)` — a monotone squash function, not a
probability of sentiment. **0.05 is a convention.** The only defence offered is
that the tool is a lexical-intensity measure, where "barely above zero" is the
natural break. That is an aesthetic argument.

**TextBlob.** `sentiment` returns `polarity` in [-1.0, 1.0] and `subjectivity` in
[0.0, 1.0] — it does **not** ship a band threshold.[25] Banding is left to the
caller, which is the correct default and the reason there is no TextBlob number
to cite.

**The default 0.5.** Ubiquitous in classification and almost never derived. When
Google explains it, Google's explanation is about the *error trade-off*, not
about a natural boundary: raising the threshold trades recall for precision.
Google's ML Crash Course states the key warning directly — "**The probability
score is not reality, or ground truth.**"[9]

### 2.2 Measured, and what it costs to measure

**scikit-learn** is the only surveyed source that treats a probability as
something with a definition to be verified. Its definition: "Well calibrated
classifiers are probabilistic classifiers for which the output of
`predict_proba` can be directly interpreted as a confidence level. For instance,
a well calibrated (binary) classifier should classify the samples such that among
the samples to which it gave a `predict_proba` value close to, say, 0.8,
approximately 80% actually belong to the positive class."[12]

That is the test a 0.85 must pass: **of everything ever labelled 0.85, was ~85%
correct?** If that number has never been measured, 0.85 is decoration.

sklearn also notes that `CalibratedClassifierCV` (isotonic / sigmoid /
temperature scaling) exists precisely because raw model scores are usually *not*
calibrated, and warns that a lower Brier loss "does not necessarily mean a better
calibrated model."[12]

### 2.3 The honest summary of §2

There is **no authority** that publishes a canonical low/medium/high band cut-off
for epistemic confidence in a knowledge base. Every number in the wild is
either (a) a convention inherited from a demo script, or (b) an empirically
tuned operating point for one classifier on one dataset. Anyone who claims
"0.7 is the standard threshold for high confidence" is repeating folklore.

That is a legitimate reason to pick a threshold — you must pick one — but it is
not a reason to *believe* the threshold means something. The defensible move is
to document the threshold as a local convention and never present it as derived.

---

## 3. Wikipedia / Wikidata: the closest real precedent

**The scheme in the brief is not Wikipedia's.** There is no 1–5 "reliable /
generally reliable / mixed reliability / generally unreliable / unreliable" scale
in `Wikipedia:Reliable sources`. I fetched the raw wikitext to check.

What exists:

- **`Wikipedia:Reliable sources`** is a prose guideline, not a numeric scale.[14]
  Its operative principle is *contextual*: "The reliability of a source depends
  on context. Each source must be carefully weighed to judge whether it is
  reliable for the statement being made in the Wikipedia article."[14] This is
  the same insight as the existing local rubric's modifier M7.
- **`Wikipedia:Tiers of reliability`** is an *essay* — explicitly "not an
  encyclopedia article or a Wikipedia policy, as it has not been reviewed by the
  community" — and it has **four** tiers, not five: Tier 1 "most reliable",
  Tier 2 "more reliable", Tier 3 "reliable", Tier 4 "limited use".[15] T1 is
  peer-reviewed scholarship; T4 is "non-expert self-published" — official
  websites, promotional material, op-eds, theses.
- The phrases "generally reliable" / "generally unreliable" / "mixed" do appear
  on Wikipedia, but as **RfC options in `WP:RS/Noticeboard`** deliberation for
  a single named source — not as a published 1–5 scale.

**So: the 1–5 scale is folklore, and the existing local rubric's `T1–T6` +
high/medium/low is a legitimate independent construction** closely paralleling
WP:Tier's four tiers, not a misquote of it. Worth stating plainly, because
`docs/CONFIDENCE-RUBRIC.md` leans on Wikipedia repeatedly and it is good that it
leans on a real page.

Notably, the T1–T6 tiers in `schemas/okf-schema.yaml` map almost one-to-one onto
WP:Tier's T1–T4, with the addition of T6 (first-person experience) and T7
(unclassifiable). That is a *better* fit to a personal knowledge base than
Wikipedia's would be, because a personal vault legitimately contains
first-person observation that an encyclopedia may not.

### 3.1 How Wikipedia avoids per-article human judgement: ORES

ORES (Objective Revision Evaluation Service) is the answer, and it is
instructive precisely because of what it does *not* do.[16][17]

It does **not** attach a confidence number to an article. It predicts *specific,
narrow, decision-shaped quantities*:

- **edit quality** — `{"prediction": "OK", "probability": {"OK": 0.70, "attack": 0.003, "spam": 0.22, "vandalism": 0.078}}`[16]
- **article quality** — `{"prediction": "FA", "probability": {"FA": 0.72, "C": 0.028, ...}}`[16] where the labels are the ordinary Wikipedia assessment classes: Featured, Good, etc.

The scale comes from **ordinary Wikipedia quality-assessment labels that
humans already produce as a by-product of curation.** Nobody was asked to rate
reliability on a new scale; the editors were already bucketing articles as
Stub/Start/C/B/FA/GA for other reasons, and the ML reads that existing signal.
That is the entire trick, and it is the most transferable idea in this report.

The second trick is **participatory operation**: ORES deliberately decouples
"choosing or curating training data, building models to serve predictions,
auditing predictions, and developing interfaces or automated agents that act on
those predictions" so that non-engineers can influence them.[17] And every
model is **versioned** — `wp10` version `0.5.0` — because a score from a
retired model is not comparable to a score from its replacement.[16]

The literature surveys confirm the approach is feature-based and consensus-driven:
of 149 papers on automatic Wikipedia quality assessment, "most use a
feature-based traditional machine learning approach and refer to Wikipedia's
content assessment standards to measure quality," and 65 of the 81 ML papers use
classical learning.[24]

**Transfer to hermes-brain:** the tier is decided by *source attributes that are
checkable from the file* — host, DOI resolution, byline, corrections policy. The
classifier's job is easy because the features are decidable. `confidence_reported`
has no such features behind it.

---

## 4. FEVER: how a probability becomes a 3-way verdict

FEVER contains 185,445 claims generated by altering Wikipedia sentences, each
labelled SUPPORTS, REFUTES, or NOT ENOUGH INFO (NEI).[18] The shared task drew
23 teams; the best system reached a FEVER score of 64.21%.[19]

The structure is the point. FEVER separates two things that naive confidence
conflates:

1. **Label space.** Three named verdicts, human-defined, mutually exclusive.
2. **Score.** A number, per class, that can be thresholded to produce a label.

The third class is what is instructive. **NEI is a refusal, not a middle
confidence.** A model that is 0.4 SUPPORTS / 0.3 REFUTES is not "medium
confidence" — it is saying it cannot find evidence, which is a *different claim
about the world* from "the evidence is weak." Collapsing a distribution into
low/medium/high destroys exactly that distinction. FEVER keeps it because the
distinction is actionable: NEI means "go find more evidence," medium-confidence
SUPPORTS means "use it with a caveat."

This is the strongest structural argument in the report for **not** mapping
`confidence_reported` to a three-band enum. The float was someone's summary
judgement; the three-band enum demands a distinction (medium vs low) the float
was never equipped to make.

**None of this rescues 0.85.** A FEVER score is defensible because it comes from
a classifier with a calibration curve against human labels. `confidence_reported`
has neither.

---

## 5. The critical question: does numeric confidence help or hurt?

### 5.1 What Google actually says

I checked both places the operator might have meant, and the honest answer is that
neither says what is often attributed to them.

**`Rules of Machine Learning` (Zinkevich) does not mention "confidence" at
all.** Zero occurrences in the full text. So the common "Google's Rules of ML
say don't use confidence scores" citation is **not supported** — I checked, and
would not repeat it.

*Independently re-verified* against the live canonical page (HTTP 200,
"Last updated 2025-08-25 UTC", 152 KB) and against five Wayback snapshots
spanning 2018-01 to 2023-01, the pre-2019 `cloud.google.com/ml-engine` path,
the original 2017 PDF, and a third-party GitHub mirror: **zero occurrences in
every edition**, so this is not an artefact of reading a partial or abridged
revision. One incidental `confiden` substring exists in the raw HTML
(`Search__enable_dynamic_content_confidential_banner`, a site-chrome feature
flag) and is not document prose. The page's own Terminology glossary defines
Instance, Label, Feature, Feature Column, Example, Model, Metric, Objective,
Pipeline and Click-through Rate — **no score or confidence concept is defined
anywhere in it.**

**And Google's actual doctrine is the opposite of the folk saying.** Rules of ML
never says a model should not output a score. It tells you to make scores
interpretable, monotone, and — the operative point — *consumed through a policy
layer rather than shown raw*:

- **Rule 14:** "Starting with an interpretable model makes debugging easier...
  Each prediction is interpretable as a probability or an expected value." and
  "we use these probabilistic predictions to make a decision: e.g. rank posts in
  decreasing expected value... However, remember when it comes time to choose
  which model to use, **the decision matters more than the likelihood of the data
  given the model**." This is pro-calibration.
- **Rule 25:** "the key question is what you do with that prediction. If you are
  using it to rank documents, then the quality of the final ranking matters more
  than the prediction itself."
- **Rule 13:** don't ask the model to figure out whether the user is *satisfied*
  — the satisfaction signal is the policy, not the score.

That policy-layer doctrine is the most likely seed of the misremembered saying.
It is about *not exposing raw scores to end users*, not about confidence being
illegitimate.

**The saying traces to a real Google document, just not that one.** It is a
misattribution of the **PAIR Guidebook** (People + AI Guidebook), *Explainability
+ Trust* chapter, whose v2 pattern is titled "Determine how to show model
confidence, **if at all**." It does advise sometimes *not* showing confidence,
and its reasons are exactly the failure mode in section 5.2:

> "Determine if you should show confidence... There's always a risk that
> confidence displays will be distracting, or worse, **misinterpreted**."

> "Counterintuitively, showing more granular confidence can be confusing if the
> impact isn't clear — **what should I do when the system is 85.8% certain vs.
> 87% certain?**"

> "**Showing confidence could create mistrust.** If the confidence level could be
> misleading for less-savvy users, reconsider how it's displayed, or whether to
> display it at all. **A misleadingly high confidence, for example, may cause
> users to blindly accept a result.**"

That is the citable Google source, and it is a **UX and calibration argument,
not a statistical ban**. Note the specific example is 85.8% versus 87% — a
granularity complaint, not a rejection of confidence as such.

A second plausible seed, also verified: McMahan et al., *Ad Click Prediction: a
View from the Trenches* (KDD 2013, Google), which argues **confidence intervals**
are "inappropriate for our application" and proposes cheap **uncertainty scores**
plus a **calibration layer**. It argues for *replacing one form of confidence
with another*, not against confidence.

Honest limit on the archaeology: that PAIR is the real source is verified from
the official chapter PDF; that the saying *originated* there specifically is an
inference, and the earliest propagation point was not traced.

What Google *also* says:

- ML Crash Course: "**The probability score is not reality, or ground truth.**"
  Threshold choice is an error trade-off decision, not a discovery.[9]
- PAIR Guidebook, *Explainability + Trust*: the goal "should be for the user to
  trust it in some situations, but to double-check it when needed," and the
  chapter's first recommendation is to "**Help users calibrate their trust**."[10]
  The glossary defines "Confidence Level, Model Confidence" as "a statistical
  measure of how certain a prediction or outcome is" — note *how certain* is
  doing quiet work; a number is not a measure of certainty, it is a measure of
  a model's internal state.
- SRE Book, *Monitoring Distributed Systems*: the relevant guidance is about
  **actionability**, not confidence numerics — "you should never trigger an alert
  simply because 'something seems a bit weird'," and pages must have "good signal
  and very low noise" because alert fatigue "can even result in engineers
  ignoring incoming alerts, sometimes even ignoring a 'real' page that's masked
  by the noise."[11]

The SRE connection is the right one, and it is not about confidence at all. It
is about **cost of a false signal**. That framing transfers directly: a
confidence number that misleads is a page nobody reads, and then the *real*
problem is also ignored.

**Conclusion on "Google recommends against it": the sentiment is directionally
right and the citation is not.** Google says (a) a probability score is not
ground truth, (b) trust should be calibrated with double-checking, and (c) noisy
signals destroy the signal. None of these is a recommendation against storing
confidence. I would not put "Google recommends against numeric confidence" in a
document without the correction.

### 5.2 Evidence FOR

- **Calibration, properly validated, does improve reliance.** "Providing
  well-calibrated AI confidence can help promote users' appropriate trust in and
  reliance on AI." This is the *stated precondition*, not an optional
  extra.[21]
- **Presentation format matters and is fixable.** Cao, Liu & Huang found
  "showing the calibrated model uncertainty alone is inadequate. Rather,
  calibrating model uncertainty and presenting it in a frequency format allow
  users to adjust their reliance accordingly" — e.g. "8 out of 10 similar cases"
  rather than "80%."[23] This is a real, actionable finding: a *numeric* band
  can help, if it is a frequency of real outcomes.
- **Routing.** BeyondUncertainty used verbalised confidence as a retrieval
  trigger, reaching 0.483 F1 vs 0.467 always-retrieve and 0.401 no-retrieve.
  But the paper is admirably honest about the catch: "**Although poorly
  calibrated as an absolute probability**, probe uncertainty modestly predicts
  question-level retrieval benefit (AUROC = 0.628)."[27] Useful as a *ranking*
  signal*; useless as a *stated probability*.

### 5.3 Evidence AGAINST — the failure mode is documented

**This is the finding that matters most for hermes-brain.**

Li et al., *Understanding the Effects of Miscalibrated AI Confidence on User
Trust, Reliance, and Decision Efficacy* (N=126 per experiment, two
experiments):[21]

> "The danger of miscalibration is that human-decision maker may not be aware
> of the issue and take the stated confidence score as accurate, leading to
> inappropriate trust and reliance."

> "when collaborating with uncalibrated AI, they tended not to detect its
> miscalibration. This led them to **over-rely on overconfident AI and to
> under-rely on underconfident AI, ultimately reducing the efficacy of
> AI-assisted decision-making.**"

Their conclusion: users "faced challenges in detecting AI confidence
miscalibration"; communicating the calibration level "eroded users' trust in
uncalibrated AI, resulting in high levels of under-reliance... and **not
improved decision efficacy**." Merely *labelling* the problem did not fix it.

**"Too Sure for Our Own Good" (AAAI-26)** reaches the same place from the
opposite direction: "in high-stakes or cognitively demanding contexts,
**miscalibrated confidence, whether intentional or not, can significantly
exacerbate automation and conservatism biases**."[22]

**The direct RAG evidence.** A 2026 ECML-PKDD paper ran a controlled ablation
isolating metadata, structure, and retrieval strategy, with a metadata-free
structured control.[20] Two results bear directly on this repo:

1. **Accuracy peaks *before* full enrichment.** "On every benchmark, accuracy
   peaks before full enrichment." The optimum is an interior point on the
   metadata ladder, not the end.
2. **Models under-use confidence metadata and over-use other metadata.**
   "temporal utilization is consistently high (50–55%) while provenance is
   effectively zero (0–6%). **Confidence and conflict utilization vary by
   architecture (confidence: 14–49%; conflict: 0–15%)**, suggesting these
   mid-level metadata types interact with model-specific training."
3. **Adding more makes things worse.** "Full enrichment (G4) degrades multi-hop
   QA by 5–8% because it adds easy-to-process metadata that is not relevant to
   reasoning tasks." They name the mechanism **"metadata competition"** — an
   extension of lost-in-the-middle from position to content type: "models
   preferentially process information that narrows the answer space, regardless
   of position."

**So the failure mode the operator reported is real and has a name.** A model given
`confidence: 0.85` treats it as narrowing information — a soft assertion — and
attends to it (14–49%, model-dependent) *without* verifying it. Meanwhile the
provenance that would let it check the claim is used at 0–6%. The number
out-competes the evidence. That is precisely the reported symptom.

**Caveat, stated honestly:** [20] is a preprint-style accepted manuscript on
one benchmark family (NuggetPedia) with a specific enrichment ladder, and [21][22]
are human-subject studies, not LLM studies. I have found **no study that
directly tests "attach 0.85 to a KB entry, then measure whether an LLM
over-trusts it."** The mechanism is documented in the adjacent cases above and
in the human-reliance literature; the exact experiment the operator described is, as far
as I can verify, not published. I am not going to pretend otherwise.

### 5.4 Verdict

The evidence does not say "numeric confidence is bad." It says:

> **Numeric confidence changes behaviour. Whether that change is good depends
> entirely on whether the number is calibrated against outcomes. An uncalibrated
> number is a net negative: it is attended to, it is not detectable as wrong, and
> it suppresses checking.**

`confidence_reported: 0.85` is uncalibrated by any available evidence.

---

## 6. Recommendation for 0.85

### 6.1 The mapping question has a false premise

The question assumes 0.85 is a quantity that *can* be banded. It is not. It is
an unvalidated self-report from a rubric that no longer exists. There is no
"correct" band for 0.85, because the number does not encode the thing a band
would assert. Any mapping — `≥0.8 = high`, `≥0.6 = medium` — would be me
inventing a threshold and then writing it down as if it were derived. That is
the same error as the 0.05 in VADER, with worse provenance.

**I am not going to recommend a numeric cut-off, and I would push back on
adopting one in the schema.** The band should be a *consequence* of evidence
tiers, not a *function* of a float.

### 6.2 What to do instead

**1. Retire the float as an input. Keep it as a record.**
`confidence_reported` should stay in the files — it is the only trace of what
was previously claimed, and deleting it destroys information. But it should be
labelled in the schema as what it is: a historical self-report, not an evidence
input. The existing `WIKI-STANDARDS.md` S3 rule already forbids trusting it;
this makes the prohibition explicit in the schema rather than in a sibling doc.

**2. Let the existing rubric do the work.**
`schemas/okf-schema.yaml` `confidence_derivation` already has T1–T7, modifiers
M1–M10, and a per-claim-minimum aggregation rule. The band is a *derived
output* of that rubric, applied to a file's sources. That is the defensible
path, and it is already built. **No band-mapping work is needed — the
derivation work is needed.**

**3. Where a float-to-band mapping is genuinely required (migration
bookkeeping), use one explicit, documented, non-authoritative convention** and
say in the schema that it is arbitrary. If a mechanical mapping must exist:

| `confidence_reported` | provisional band | status |
|---|---|---|
| ≥ 0.90 | high | convention, not derived |
| 0.75 – 0.90 | medium | convention, not derived |
| 0.60 – 0.75 | low | convention, not derived |
| < 0.60 | low | convention, not derived |

Chosen to match the observed corpus distribution (222 files, range 0.65–0.96,
modal value 0.85 — 49 files) so that the temporary band roughly preserves the
current high/medium/low proportions and the change is not read as a
regression. **That is a reason about migration noise. It is not a reason the
0.85 means anything.** Every row is a convention. Write the word "convention" in
the schema.

**4. Add `confidence_basis`, and make the numeric field conditional on it.**
The rubric's own procedure step 10 already requires `confidence_basis` — the
tier ids, the modifiers, the date graded — and states: "Without a basis the
value is an unauditable self-report and MUST be treated as untrusted by
consumers." That rule is correct and it is the single most important line in
this report. **Enforce it structurally:** a numeric `confidence` field is only
valid alongside a `confidence_basis`. Without a basis, the only permitted value
is `ungraded`. This makes "uncalibrated number" unrepresentable rather than
merely discouraged.

**5. Follow Wikipedia on the ordering, not on the scale.**
ORES works because it predicts decision-shaped quantities from features humans
already produce. The equivalent here: `epistemic` (fact/observation/hypothesis/
prediction/decision) is a better-grounded field than a confidence float, because
it is *categorical and checkable* rather than a number requiring calibration.
The rubric already treats the two as independent, and that is right. If one
field is to be trusted by a consumer over the other, it is `epistemic`.

**6. Strip the number from what the model actually reads.**
Given the metadata-competition finding — confidence attended to at 14–49%,
provenance at 0–6%[20] — a frontmatter number that reaches the retrieval
context is a live liability. If a band is to influence retrieval, the defensible
mechanism is a **filter or ordering at retrieval time** (which is where
ranking scores legitimately live, per §1), not a number in the prompt. Same
discrimination, no over-trust.

### 6.3 The one-line version

**Don't band 0.85. Grade the sources, let the band fall out, keep the float as a
provenance record, and never let an unbasised number reach an LLM's context.**

---

## Open items and honest gaps

- **The 1–5 Wikipedia scale in the original brief does not exist.** Verified
  against raw wikitext of `WP:RS` and `WP:Tiers of reliability`. `WP:Tiers` is a
  4-tier essay. If a document in this repo asserts the 1–5 scale, it should be
  corrected — I did not audit for that.
- **No direct study of "0.85 on a KB entry causes LLM over-trust."** The
  mechanism is documented in [20][21][22]; the exact experiment is not
  published as far as I can verify.
- **LangChain reranker `relevance_score` semantics unverified** (§1a).
- **The original rubric that produced 0.85 is not recoverable from the repo or
  the schema.** `docs/CONFIDENCE-RUBRIC.md` is a *new* rubric (dated
  2026-09-28) that supersedes it. The old one is lost.
- Retrieval-score ranges are **not** comparable across the systems in §1, and
  the Pinecone/Weaviate/Azure sources are vendor docs, not peer-reviewed. Where
  vendor docs conflict with the calibration literature (sklearn, FEVER, ORES),
  the literature wins.

## Sources

[1] https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking
[2] https://learn.microsoft.com/en-us/azure/search/semantic-search-overview
[3] https://learn.microsoft.com/en-us/azure/search/semantic-how-to-enable-scoring-profiles
[4] https://docs.pinecone.io/guides/search/rerank-results
[5] https://docs.weaviate.io/weaviate/config-refs/distances
[6] https://docs.vespa.ai/en/reference/ranking/rank-features.html
[7] https://docs.vespa.ai/en/ranking.html
[8] https://learn.vespa.ai/ranking-fundamentals/rank-profiles
[9] https://developers.google.com/machine-learning/crash-course/classification/thresholding
[10] https://pair.withgoogle.com/guidebook-v2/chapters/explainability-trust
[11] https://sre.google/sre-book/monitoring-distributed-systems/
[12] https://scikit-learn.org/stable/modules/calibration.html
[13] https://github.com/cjhutto/vadersentiment
[14] https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources
[15] https://en.wikipedia.org/wiki/Wikipedia:Tiers_of_reliability
[16] https://www.mediawiki.org/wiki/ORES
[17] https://arxiv.org/abs/1909.05189
[18] https://arxiv.org/abs/1803.05355
[19] https://aclanthology.org/W18-5501
[20] https://arxiv.org/html/2606.29645
[21] https://arxiv.org/html/2402.07632v4
[22] https://ojs.aaai.org/index.php/AAAI/article/view/38798/42760
[23] https://arxiv.org/pdf/2401.05612
[24] https://arxiv.org/html/2310.02235
[25] https://textblob.readthedocs.io/en/dev/quickstart.html
[26] https://elastic.co/guide/en/elasticsearch/guide/master/relevance-intro.html
[27] https://arxiv.org/abs/2607.25600
