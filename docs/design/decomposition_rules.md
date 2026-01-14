# Statement Decomposition Rules
# Phase 1: How to break segments into atomic statements

## Core Principle

> One statement = one verifiable fact OR one claim OR one interpretation
> 
> If you need "and" or "because" to describe it, it's probably multiple statements.

---

## Decomposition Triggers

### 1. Coordinating Conjunctions (AND, OR, BUT)
```
"He grabbed my arm AND twisted it"
→ Statement 1: "He grabbed reporter's arm"
→ Statement 2: "He twisted reporter's arm"
```

### 2. Causal Connectors (BECAUSE, SO, THEREFORE)
```
"He grabbed me BECAUSE he wanted to hurt me"
→ Statement 1: "He grabbed reporter" (observation)
→ Statement 2: "Reporter believes he wanted to hurt reporter" (interpretation)
```

### 3. Temporal Connectors (THEN, AFTER, BEFORE, WHILE)
```
"He yelled THEN grabbed me"
→ Statement 1: "He yelled"
→ Statement 2: "He grabbed reporter"
```

### 4. Contrast Connectors (BUT, HOWEVER, ALTHOUGH)
```
"I said stop BUT he continued"
→ Statement 1: "Reporter said stop"
→ Statement 2: "He continued"
```

---

## Non-Decomposition Cases

### Keep Together
- Adverbial phrases: "He grabbed my arm forcefully" → 1 statement
- Prepositional phrases: "He twisted it behind my back" → 1 statement
- Quotes: "He said 'stop'" → 1 statement (reported_speech)

### Edge Cases
- "He grabbed and twisted my arm" → Context decides:
  - If same instant, same action = 1 statement
  - If sequential = 2 statements

---

## Implementation Strategy

### Use spaCy Dependency Parsing
1. Find ROOT verb(s)
2. Find coordinating conjunctions (cc) 
3. Find conjuncts (conj)
4. Find adverbial clauses (advcl) — often causal
5. Split at clause boundaries

### Example Parse
```
"He grabbed my arm and twisted it because he wanted to hurt me"
     ↓
ROOT: grabbed
  └── conj: twisted (via "and")
  └── advcl: wanted (via "because")
```

### Output Structure
```python
@dataclass
class AtomicStatement:
    id: str
    text: str
    type: StatementType  # observation, claim, interpretation, etc.
    span_start: int
    span_end: int
    parent_segment_id: str
    confidence: float
    flags: list[str]
```

---

## Success Criteria

1. **No information loss**: All content from original appears in statements
2. **Atomic**: Each statement has exactly one predicate
3. **Typed**: Each statement has a preliminary type
4. **Traceable**: Link back to original span

---

## Test Cases

### Simple
- "He grabbed me" → 1 statement
- "He grabbed me and pushed me" → 2 statements

### Complex  
- "He grabbed me because he wanted to hurt me" → 2 statements (obs + interp)
- "He said 'stop' but continued" → 2 statements
- "He grabbed my arm forcefully" → 1 statement (modifier, not separate action)

### Quotes
- 'He yelled "stop right there!"' → 1 statement (reported_speech)
- 'He yelled "stop" and pushed me' → 2 statements
