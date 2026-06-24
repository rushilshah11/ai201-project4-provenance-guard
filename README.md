# Provenance Guard

Provenance Guard is a Flask API that classifies submitted text as human-written or AI-generated using two independent detection signals, combines their scores into a single confidence value, and returns a transparency label explaining the result. Disputed classifications can be flagged for human review through an appeals endpoint.

---

## 1. Architecture Overview

When a piece of text is submitted, it passes through two signals running independently, gets aggregated into a confidence score, mapped to a transparency label, written to an audit log, and returned to the caller. Appeals follow a separate, simpler path.

```
SUBMISSION FLOW
===============
POST /submit
    |
    +-----------------------------+
    |                             |
    v                             v
Signal 1: Groq LLM         Signal 2: Stylometrics
(semantic/stylistic            (structural score 0–1)
 score 0–1)
    |                             |
    +-----------------------------+
                 |
                 v
      Confidence Aggregator
      (weighted average of both scores)
                 |
                 v
          Label Generator
      (maps score to transparency label)
                 |
                 v
             Audit Log
                 |
                 v
JSON response → { content_id, attribution, confidence, label }


APPEAL FLOW
===========
POST /appeal
    |
    v
Update content status → "under_review"
    |
    v
Audit Log
    |
    v
JSON confirmation → { message, content_id, status }
```

---

## 2. Detection Signals

### Signal 1 — Groq LLM

**What it measures:** Semantic and stylistic properties of the text. The model evaluates word choice, sentence flow, coherence patterns, hedging language, and the overall "feel" of the writing.

**Why it matters:** AI-generated text tends to exhibit smooth, overconfident prose with consistent hedging, generic transitions, and an absence of personal quirks. Human writing tends to be messier, more idiosyncratic, and more contextually grounded. A large language model is well-positioned to detect these high-level patterns.

**Blind spot:** Polished human writers — academics, lawyers, non-native speakers writing carefully — can produce prose that reads as "too clean" to the model. Signal 1 may flag formal human writing as AI-generated even when it is not.

### Signal 2 — Stylometrics (pure Python)

**What it measures:** Three structural properties of the text, computed without any API call:

- **Sentence length variance** — AI text tends toward uniform sentence lengths; high variance suggests human writing. Normalized as `1 - min(variance, 400) / 400`.
- **Type-token ratio (TTR)** — unique words divided by total words. Low lexical diversity can indicate repetitive AI phrasing. Normalized as `1 - ttr`.
- **Punctuation density** — punctuation characters divided by total characters. AI text often uses minimal punctuation. Normalized as `1 - min(density, 0.2) / 0.2`.

The three normalized values are averaged into a single score between 0 and 1.

**Why it matters:** Structural heuristics are fast, deterministic, and free — they require no API call and have no rate limits. They catch patterns that are invisible to semantic analysis, such as abnormally uniform sentence lengths.

**Blind spot:** Beginner writers and non-native English speakers often write short, grammatically simple, uniform sentences — the same structural pattern Signal 2 associates with AI. This signal can produce false positives for this group regardless of whether AI was used.

---

## 3. Confidence Scoring

The two signal scores are combined using a weighted average that gives more weight to the Groq LLM signal:

```
confidence = (0.6 × signal_1_score) + (0.4 × signal_2_score)
```

Signal 1 is weighted higher because it evaluates meaning and context, not just surface structure. A text can have varied sentence lengths and dense punctuation while still reading as clearly AI-generated — structure alone is not sufficient. Signal 2 serves as a corroborating structural check.

### Score thresholds

| Confidence | Attribution | Meaning |
|---|---|---|
| 0.85 and above | `likely_ai` | Strong evidence from both signals |
| 0.60 – 0.84 | `uncertain_leaning_ai` | Some AI characteristics, not conclusive |
| 0.40 – 0.59 | `uncertain_leaning_human` | Some human characteristics, not conclusive |
| Below 0.40 | `likely_human` | Strong evidence from both signals |

The threshold for a confident AI label (0.85) is deliberately higher than the threshold for a confident human label (below 0.40). It is worse to wrongly accuse a human of using AI than to miss an AI-generated submission.

### Real examples from the audit log

**Example 1 — formal AI-style text:**

```
content_id:   cc79bc98-a6bf-4a78-8c8c-5292fcb74046
signal_1:     0.9
signal_2:     0.7099
confidence:   0.824
attribution:  uncertain_leaning_ai
```

Both signals agreed the text was AI-like. The Groq model noted "overly formal and repetitive language, with an abundance of buzzwords and clichés." Stylometrics detected near-zero sentence length variance. The combined score of 0.824 lands just below the 0.85 threshold, so the system returned an uncertain label rather than a definitive AI classification.

**Example 2 — casual human-style text:**

```
content_id:   373e3ca7-b154-4c23-b01b-38d9bfc18988
signal_1:     0.2
signal_2:     0.345
confidence:   0.258
attribution:  likely_human
```

Both signals agreed the text was human-written. Groq noted "informal, conversational language and erratic sentence structure." Stylometrics detected high sentence length variance (short outbursts mixed with long run-ons) and heavier punctuation density. The combined score of 0.258 is well below 0.40, producing a high-confidence human label.

---

## 4. Transparency Labels

The label returned in the API response is chosen based on the confidence score bucket:

**Score 0.85 and above:**
> "This content was likely generated by AI. Confidence: High"

**Score 0.60 – 0.84:**
> "We were unable to determine with confidence whether this content was human or AI-generated, though it shows some characteristics of AI-generated content. If you believe this is incorrect, you may submit an appeal."

**Score 0.40 – 0.59:**
> "We were unable to determine with confidence whether this content was human or AI-generated, though it shows some characteristics of human writing. If you believe this is incorrect, you may submit an appeal."

**Score below 0.40:**
> "This content appears to be human-written. Confidence: High"

---

## 5. Rate Limiting

Rate limiting is applied to `POST /submit` only, using Flask-Limiter with in-memory storage:

- **3 requests per minute**
- **20 requests per day**

The per-minute limit allows normal submit/review/resubmit behavior while blocking automated scripts from probing the system rapidly. The per-day limit is generous enough for even the most active user but stops adversarial probing campaigns. Neither limit is applied to `POST /appeal` or `GET /log` because those endpoints do not call external APIs, are not exploitable for probing, and creators should not be penalized for accessing their own appeal status or audit history.

When the limit is exceeded, the server returns HTTP 429. During verification, requests 1–3 to `/submit` within a single minute returned HTTP 201 and request 4 returned HTTP 429.

---

## 6. Known Limitations

**Non-native English speakers and beginner writers.** Signal 2 (Stylometrics) associates low sentence-length variance and low type-token ratio with AI authorship. Writers who naturally produce short, grammatically simple, structurally uniform sentences — whether due to language proficiency, age, or writing style — will score high on Signal 2 even if they have not used AI. Signal 1 may partially counteract this if the Groq model correctly reads the underlying meaning as human, but the appeal workflow is the main recourse for these writers.

**Formal academic and legal human writing.** Signal 1 (Groq LLM) can interpret precise, well-structured, impersonal prose as "too polished" and return a high AI-likelihood score. The asymmetric thresholds reduce the risk that such a writer receives a definitive AI label, but they may still fall into the uncertain-leaning-AI zone and be prompted to submit an appeal.

---

## 7. Spec Reflection

**One way the spec helped.** The planning document's discussion of false positive risk — specifically the concern about wrongly accusing a human of using AI — led directly to the asymmetric confidence thresholds. The uncertain zone is deliberately wide (0.40–0.84) and the confident-AI threshold is set high (0.85). Without that discussion in the spec, it would have been easy to split the range evenly at 0.5 and produce far more false positives.

**One way implementation diverged from the spec.** The spec initially defined three label categories: high-confidence AI, uncertain, and high-confidence human. During planning this evolved to four categories by splitting the uncertain zone into "uncertain, leaning AI" and "uncertain, leaning human." This gives users more actionable information — a creator in the leaning-human zone can reasonably decide not to appeal, while one in the leaning-AI zone knows the system has real concerns and an appeal may be warranted.

---

## 8. AI Usage

### Instance 1 — Milestone 3: Flask skeleton and Signal 1

Claude Code was directed to build the Flask app skeleton, the Groq signal function, the audit log helpers, and the label generator. The initial output used human-readable strings for the `attribution` field (`'Uncertain'` and `'Human-written'`) instead of the four machine-readable codes specified in planning.md. A follow-up prompt was required, explicitly naming the four correct values — `likely_ai`, `uncertain_leaning_ai`, `uncertain_leaning_human`, `likely_human` — to get the implementation into spec.

### Instance 2 — Milestone 4: Stylometrics signal and test inputs

Claude Code was directed to build the stylometrics signal and verify it with four test inputs representing clearly AI, clearly human, borderline human (academic), and borderline AI (lightly edited) text. The initial test texts were too short — all four scores clustered between 0.63 and 0.66, showing no meaningful discrimination. The test inputs were overridden with longer, more extreme texts (150+ words each) specifically constructed to exercise each metric: uniform sentence lengths for the AI case, wildly varying lengths and dense punctuation for the human case. With the revised inputs the scores ranged from 0.51 to 0.71 in the correct order.
