# NNRT v2 Quick Reference

## The Shift

```
v1: Input → [Process] → Softened Prose
                              ↑
                        WRONG OUTPUT

v2: Input → [Decompose] → [Classify] → [Link] → Typed Statements
                                                       ↓
                                              (optional prose)
```

## Statement Types Cheat Sheet

| Type | Keywords/Signals | Example |
|------|------------------|---------|
| **observation** | Physical verbs, visible actions | "Officer grabbed arm" |
| **reported_speech** | Quotes | "Stop right there!" |
| **claim** | Internal states, pain, fear | "I felt terrified" |
| **interpretation** | "deliberately", "wanted to", "intentionally" | "Reporter believes intent was harm" |
| **medical_record** | Doctor, hospital, ER, diagnosis | "ER documented bruising" |
| **third_party_claim** | Witness says, neighbor states | "Witness states he saw X" |

## What Makes Good Output

✅ **GOOD**: Observer can instantly distinguish facts from interpretations
❌ **BAD**: Reader feels emotional pull in any direction

✅ **GOOD**: Every interpretation has `derived_from` links
❌ **BAD**: Judgment appears without source observation

✅ **GOOD**: "Unknown" type is rare (<5%)
❌ **BAD**: System confidently misclassifies

## Files Created Today

```
docs/
├── analysis/
│   └── architectural_gap_analysis_v4.md  # The problem
├── schema/
│   ├── nnrt_output_schema_v0.1.yaml      # The solution
│   └── gold_standard_example.md          # Correct output example
└── roadmap/
    └── nnrt_v2_roadmap.md                # How to get there
```

## CLI Options

```bash
# Current (v1)
nnrt transform "text"              # Softened prose (default)
nnrt transform "text" --raw        # Debug: show decomposition

# Future (v2)
nnrt transform "text" --format structured  # NEW default
nnrt transform "text" --format prose       # Old mode (deprecated)
nnrt transform "text" --filter observations
```

## Next Session

Start **Phase 1: Statement Decomposition**
- Create `p25_decompose.py` pass
- Split segments into atomic statements
