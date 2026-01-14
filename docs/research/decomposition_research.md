# NNRT Decomposition & Classification: Research Summary
## Date: 2026-01-14
## Purpose: Ground Phase 1-2 in established NLP science

---

## Key Research Findings

### 1. Clause Segmentation

**Problem**: spaCy does NOT have built-in clause segmentation. Our custom approach is the right direction.

**Established Approaches**:
- **Dependency Parsing** (what we started): Find ROOT, conj, advcl, ccomp
- **Constituency Parsing**: More powerful but heavier (Stanza, Berkeley parser)
- **Open Information Extraction (OIE)**: Extracts (subject, relation, object) tuples

**Tool Options**:
| Tool | Approach | Status |
|------|----------|--------|
| spaCy dependency | Custom rules on dep tree | ✅ Available |
| AllenNLP OIE | SRL-based extraction | ⚠️ Maintenance mode (Dec 2022) |
| Stanza | Constituency parsing | ✅ Active |
| ClausIE | Clause-based OIE | Research prototype |

**Recommendation**: 
- Use **spaCy dependency parsing** for clause boundaries (we're on right track)
- Consider **OpenIE / SRL** for extracting atomic facts as (subject, relation, object) tuples
- Our current approach is valid but needs refinement in token-to-text reconstruction

---

### 2. Discourse Parsing (RST)

**Rhetorical Structure Theory** is the gold standard for understanding text structure.

**Key Concepts**:
- **Elementary Discourse Units (EDUs)**: Minimal units (roughly clauses)
- **Nucleus vs Satellite**: Core content vs supporting content
- **Discourse Relations**: evidence, elaboration, cause-effect, concession

**RST is EXACTLY what NNRT needs**:
- "Claim → Evidence" = observation → supporting interpretation
- "Cause → Result" = action → consequence
- "Nucleus → Satellite" = main fact → supplementary detail

**Tool Options**:
| Tool | Notes |
|------|-------|
| isanlp_rst | Multi-language, Docker-ready |
| rstfinder | ETS, needs treebank training |
| rst-parser (PyPI) | Neural, PyTorch |
| rst-workbench | Multiple parsers, web UI |

**Recommendation**:
- Explore **isanlp_rst** or **rst-parser** for full discourse parsing
- This could replace/enhance our custom decomposition
- **BUT**: Heavy dependency, slower, may be overkill for v1

---

### 3. Epistemic Status Classification

**This is the CORE of NNRT's statement typing.**

**Key Categories** (aligned with our schema):
| Category | Definition | Linguistic Markers |
|----------|------------|-------------------|
| **Fact** | Verifiable, objective | Concrete verbs, dates, names |
| **Claim** | Assertion, may be unverified | First-person, assertion verbs |
| **Opinion** | Subjective judgment | Intensifiers, sentiment words |
| **Belief** | Faith-based, inarguable | "believe", "feel", modal verbs |
| **Interpretation** | Inference about others | "apparently", "seems", intent verbs |

**Linguistic Cues for Classification**:
- **Factive verbs**: "know", "realize", "discover" → signals presupposed fact
- **Intent verbs**: "wanted to", "tried to", "planned to" → interpretation
- **Epistemic markers**: "apparently", "seems", "I believe" → signals uncertainty
- **Evidential markers**: "according to", "he said" → signals reported speech

**NLP Approaches**:
- **Rule-based**: Pattern matching on markers (fast, explainable, limited)
- **ML Classification**: LSTM, RoBERTa-LSTM for sentence-level (accurate, opaque)
- **Hybrid**: Rules for obvious cases, ML for ambiguous

**Recommendation**:
- Start with **rule-based classification** using linguistic markers
- Add **confidence scoring** based on marker presence
- Consider **fine-tuned classifier** for Phase 3+ if accuracy insufficient

---

## Refined Architecture Proposal

Based on research, here's the recommended approach:

### Phase 1: Clause Decomposition (Refined)

**Option A: Fix Current Approach**
- Fix token-to-text reconstruction (our current bug)
- Add subtree exclusion for nested clauses
- Handle punctuation separately

**Option B: Use OpenIE/SRL**
- Use AllenNLP's SRL model to extract (subject, verb, object) tuples
- Each tuple becomes an atomic statement
- More principled than custom dep parsing

**Recommendation**: **Option A first**, Option B as enhancement

### Phase 2: Statement Classification

**Rule-Based First**:
```python
INTENT_MARKERS = ["wanted to", "tried to", "deliberately", "intentionally"]
EPISTEMIC_MARKERS = ["apparently", "seems", "appears", "allegedly"]
EVIDENTIAL_MARKERS = ["according to", "stated", "said", "reported"]
FACTIVE_VERBS = ["know", "realize", "discover", "notice", "see", "hear"]

def classify_statement(text, doc):
    text_lower = text.lower()
    
    # Interpretation: intent attribution
    if any(m in text_lower for m in INTENT_MARKERS):
        return StatementType.INTERPRETATION, 0.9
    
    # Quote: direct speech
    if has_quotation_marks(text):
        return StatementType.QUOTE, 1.0
    
    # Observation: factive verbs + first person
    if has_first_person(doc) and has_factive_verb(doc):
        return StatementType.OBSERVATION, 0.8
    
    # Claim: default for assertions
    return StatementType.CLAIM, 0.5
```

### Phase 3: RST Integration (Future)

For proper discourse structure:
1. Install `isanlp_rst` or similar
2. Parse document into RST tree
3. Use discourse relations to:
   - Link interpretations to source observations
   - Identify nucleus (main claim) vs satellite (support)
   - Build provenance graph

---

## Immediate Action Items

### Today: Fix Decomposition Bug
1. Fix token-to-text reconstruction
2. Test with compound sentences
3. Verify no information loss

### Next Session: Classification Rules
1. Implement rule-based classifier
2. Use linguistic markers from research
3. Add confidence scoring

### Future: Consider RST
1. Evaluate isanlp_rst performance
2. Benchmark against rule-based approach
3. Decide if worth the dependency

---

## References

### Academic
- Mann & Thompson (1988) - Rhetorical Structure Theory
- Semantic Role Labeling models
- Open Information Extraction research

### Tools
- spaCy: https://spacy.io/
- AllenNLP: https://allennlp.org/ (maintenance mode)
- isanlp_rst: https://github.com/tchewik/isanlp_rst
- rst-parser: https://pypi.org/project/rst-parser/

### Key Insight

> "Clause segmentation is considered a 'non-trivial problem' in NLP"
> — Multiple sources

We're not failing because we're doing it wrong. This is genuinely hard.
The key is to:
1. Get 80% accuracy with rules
2. Flag uncertain cases for review
3. Improve iteratively with real data
