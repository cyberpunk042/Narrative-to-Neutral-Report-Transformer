"""
Pass 27 — Epistemic Tagging

V4 Alpha: Tags every AtomicStatement with proper epistemic metadata.

This is the core V4 fix: statements are tagged at extraction time, not
sorted into buckets later. Every statement carries:
- source: who is speaking
- epistemic_type: what kind of content
- polarity: asserted/denied/uncertain
- evidence_source: what supports this

Buckets like "OBSERVATIONS" and "CLAIMS" become views over tagged items.
"""

import re
from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger

PASS_NAME = "p27_epistemic_tag"
log = get_pass_logger(PASS_NAME)


# =============================================================================
# Epistemic Pattern Definitions
# =============================================================================

# Self-reported experience (emotion, pain, perception - not observable)
SELF_REPORT_PATTERNS = [
    r'\b(i\s+)?was\s+(so\s+)?(scared|terrified|frightened|afraid|anxious)\b',
    r'\b(i\s+)?was\s+(absolutely\s+)?(terrified|shocked|stunned|horrified)\b',
    r'\b(i\s+)?was\s+in\s+(complete\s+)?(shock|disbelief|pain)\b',
    r'\b(i\s+)?was\s+(exhausted|tired|drained|overwhelmed)\b',
    r'\b(i\s+)?was\s+(completely\s+)?(innocent|confused|lost)\b',
    r'\b(i\s+)?felt\s+\w+',
    r'\bmy\s+(fear|pain|anxiety|terror|trauma)\b',
    r'\bi\s+(now\s+)?suffer\s+from\b',
    r'\bi\s+can\s+no\s+longer\b',
    r'\bi\s+have\s+(permanent|chronic)\b',
    r'\bpanic\s+attacks?\b',
    r'\bpsychological\s+trauma\b',
    r'\bi\s+screamed\s+in\s+pain\b',
    r'\bit\s+felt\s+like\b',
    r'\bi\s+froze\b',
    r'\bi\s+just\s+wanted\b',
    r'\bafter\s+pulling\s+a\s+.*shift\b',
    # V4.1: More self-report patterns
    r'\bwrists?\s+were\s+(bleeding|bruised)\b',  # "My wrists were bleeding"
    r'\bbruised\b',  # fragment "bruised"
    r'\bi\s+could\s?n\'?t\s+hear\b',  # "I couldn't hear"
    r'\bthey\s+kept\s+looking\b',  # "they kept looking at me"
    r'\bshaking\s+(their\s+)?heads?\b',  # "shaking their heads"
]

# Interpretations (mental state attribution, inference, perception of intent)
INTERPRETATION_PATTERNS = [
    r'\b(clearly|obviously|apparently)\s+(was|were|wanted|trying|looking)\b',
    r'\bcould\s+tell\s+(from|that)\b',
    r'\bknew\s+(that|he|she|they)\b',
    r'\bwas\s+(clearly|obviously|deliberately)\b',
    r'\bwanted\s+to\s+(inflict|cause|hurt|harm|punish)\b',
    r'\bintention(ally|al)?\b',
    r'\bdeliberately\b',
    r'\blooking\s+for\s+trouble\b',
    r'\bready\s+to\s+(shoot|attack|assault)\b',
    r'\benjoying\s+(my|his|her|the)\b',
    r'\bmocking\b',
    r'\bthug\s+cop\b',
    r'\bpsychotic\b',
    r'\bmaniac\b',
    r'\b(he|she|they)\s+obviously\b',
    r'\bit\s+was\s+obvious\b',
    r'\bdismissive\s+attitude\b',
    # V4: Additional interpretation patterns
    r'\bdesigned\s+to\s+(?:protect|cover|hide|intimidate)\b',
    r'\bviolent\s+(?:cop|cops|officer|officers|police)\b',
    # V4.1: More interpretation patterns
    r'\bfishing\s+through\b',  # "fishing through my belongings"
    r'\blike\s+a\s+(criminal|maniac|thug)\b',  # "like a criminal"
    r'\bknown\s+(violent|criminal)\s+offender\b',  # "known violent offender"
    r'\bhistory\s+of\s+(brutality|violence|abuse)\b',  # "history of brutality"
    r'\bvictimizing\s+(innocent|people|citizens)\b',  # "victimizing innocent citizens"
]

# Legal characterizations (legal conclusions, rights claims)
LEGAL_CLAIM_PATTERNS = [
    r'\bwithout\s+(my\s+)?consent\b',
    r'\bwithout\s+(any\s+)?legal\s+justification\b',
    r'\billegal\s+(assault|search|detention|arrest|stop)\b',
    r'\bexcessive\s+(force|violence)\b',
    r'\bpolice\s+(brutality|misconduct)\b',
    r'\bcivil\s+rights\s+violation\b',
    r'\bviolated\s+(my|his|her|their|our)\s+(civil\s+)?rights\b',
    r'\bfalse\s+(imprisonment|arrest)\b',
    r'\bconstitutional\s+rights\b',
    r'\bobstruction\s+of\s+justice\b',
    r'\bwitness\s+intimidation\b',
    r'\bracial\s+profiling\b',
    r'\bwithin\s+policy\b',
    r'\bcriminal\s+behavior\b',
    r'\bcomplete\s+(and\s+total\s+)?lie\b',
    r'\bfabricated\b',
    r'\bwhitewash\b',
    r'\bcover.?up\b',
    r'\bcorrupt(ion)?\b',
    r'\bharassment\b',
    r'\bassault\s+and\s+battery\b',
    r'\bassaulted\s+(me|him|her|them|us)\b',
    # V4.1: More legal patterns
    r'\bno\s+legal\s+basis\b',  # "no legal basis to stop me"
    r'\bthe\s+racism\b',  # "the racism in this department"
]

# Direct quote markers
QUOTE_PATTERNS = [
    r'^["\']',
    r'^\w+\s+said\s+["\']',
    r'^\w+\s+yelled\s+["\']',
    r'^\w+\s+told\s+(me|him|her|them)\s+["\']',
]

# Document-based / administrative
DOCUMENT_PATTERNS = [
    r'\breceived\s+a\s+letter\b',
    r'\bfiled\s+a\s+(formal\s+)?complaint\b',
    r'\bformal\s+complaint\b',
    r'\bcomplaint\s+had\s+been\s+investigated\b',
    r'internal\s+affairs\b',
    r'\bfound\s+to\s+be\b.*\bpolicy\b',
]

# Medical documentation (when attributed to medical provider)
MEDICAL_FINDING_PATTERNS = [
    r'\b(dr\.?|doctor)\s+\w+\s+(documented|said|diagnosed|noted)\b',
    r'\bmedical\s+records?\b',
    r'\b(she|he)\s+documented\b',
    r'\bdiagnosed\s+(with|me)\b',
    r'\binjuries\s+were\s+consistent\s+with\b',
]

# Conspiracy claims (unfalsifiable allegations)
CONSPIRACY_PATTERNS = [
    r'\bproves\s+(there[\'\"]?s|that)\b',
    r'\bmysteriously\b.*\b(lost|disappeared)\b',
    r'\bmassive\s+cover.?up\b',
    r'\bthey\s+always\s+protect\s+their\s+own\b',
    r'\bconspiring\b',
    r'\bwhich\s+proves\b',
    # V4: Additional conspiracy patterns
    r'\bhiding\s+(?:evidence|the\s+truth|information)\b',
    r'\bcover(?:ing)?\s+(?:up|for)\b',
    r'\bpattern\s+of\s+(?:violence|abuse|misconduct)\b',
    # V4.1: More conspiracy patterns
    r'\bthugs\s+with\s+badges\b',  # "thugs with badges"
    r'\bsystematic\s+and\s+institutionalized\b',  # "systematic and institutionalized"
    r'\bterrorize\s+(?:our|the)\s+communit\b',  # "terrorize our communities"
    r'\bsilenced\b',  # "I refuse to be silenced"
    r'\bfight\s+for\s+justice\b',  # "fight for justice"
    r'\breal\s+accountability\b',  # "real accountability"
    r'\bthe\s+whole\s+system\s+is\s+corrupt\b',  # "whole system is corrupt"
]


def _classify_epistemic(text: str) -> tuple[str, str, float]:
    """
    Classify a statement's epistemic type based on linguistic patterns.
    
    Returns (epistemic_type, evidence_source, confidence).
    """
    text_lower = text.lower()
    
    # Check patterns in priority order (most specific first)
    
    # 1. Conspiracy claims (highest priority - most dangerous)
    for pattern in CONSPIRACY_PATTERNS:
        if re.search(pattern, text_lower):
            return ("conspiracy_claim", "inference", 0.9)
    
    # 2. Legal characterizations
    for pattern in LEGAL_CLAIM_PATTERNS:
        if re.search(pattern, text_lower):
            return ("legal_claim", "inference", 0.85)
    
    # 3. Interpretations (intent attribution, mental state inference)
    for pattern in INTERPRETATION_PATTERNS:
        if re.search(pattern, text_lower):
            return ("interpretation", "inference", 0.85)
    
    # 4. Self-reported experience (emotions, pain, trauma)
    for pattern in SELF_REPORT_PATTERNS:
        if re.search(pattern, text_lower):
            return ("self_report", "self_report", 0.9)
    
    # 5. Medical findings (when attributed to provider)
    for pattern in MEDICAL_FINDING_PATTERNS:
        if re.search(pattern, text_lower):
            return ("medical_finding", "document", 0.85)
    
    # 6. Administrative/document-based
    for pattern in DOCUMENT_PATTERNS:
        if re.search(pattern, text_lower):
            return ("admin_action", "document", 0.8)
    
    # 7. Direct quotes
    for pattern in QUOTE_PATTERNS:
        if re.search(pattern, text_lower):
            return ("quote", "direct_observation", 0.9)
    
    # 8. V4 ALPHA: Narrative glue (filler, transitions - low information value)
    narrative_glue_patterns = [
        r'^it\s+all\s+started\b',
        r'^this\s+is\s+(what|how|why)\b',
        r'^let\s+me\s+(explain|tell)\b',
        r'^here\s+is\s+what\s+happened\b',
        r'^that\s+is\s+when\b',
        r'^out\s+of\s+nowhere\b',
        r'^suddenly\b',
        r'^just\s+then\b',
    ]
    for pattern in narrative_glue_patterns:
        if re.search(pattern, text_lower):
            return ("narrative_glue", "self_report", 0.6)
    
    # 9. V4 ALPHA: Expanded direct event patterns
    action_patterns = [
        # Physical actions
        r'\b(grabbed|pushed|punched|slammed|twisted|searched|put|took|pulled)\b',
        r'\b(kicked|struck|hit|shoved|threw|dragged|arrested|handcuffed)\b',
        r'\b(picked up|put down|placed|held|released)\b',
        r'\b(found|cut|uncuffed|cuffed|pressed)\b',  # V4.1: more actions
        r'\b(tried|attempted)\s+to\b',  # V4.1: "tried to explain"
        # Movement
        r'\b(arrived|approached|walked|ran|drove|came|went|left|entered|exited)\b',
        r'\b(walking|running|driving|approaching|leaving)\b',
        r'\b(got\s+out|jumped\s+out|got\s+in|stepped)\b',  # V4.1: "got out of the car"
        r'\b(screeching|screeched|sped|accelerated)\b',  # V4.1: vehicle actions
        # Verbal
        r'\b(said|yelled|asked|told|whispered|screamed|shouted)\b',
        r'\b(responded|replied|answered|stated|claimed)\b',
        r'\b(started\s+screaming|started\s+yelling)\b',  # V4.1: "started screaming"
        # Observation verbs (reporter sees something happen)
        r'\b(saw|watched|witnessed|noticed|observed|heard)\b',
        # Recording/documenting
        r'\b(recorded|filmed|photographed|took\s+a\s+picture)\b',
        # Communication
        r'\b(called|phoned|texted|contacted|reported)\b',
        # Research/discovery
        r'\b(researched|looked\s+up|found\s+that|discovered)\b',  # V4.1
    ]
    
    for pattern in action_patterns:
        if re.search(pattern, text_lower):
            return ("direct_event", "self_report", 0.7)
    
    # 10. V4 ALPHA: Third-party reports
    third_party_patterns = [
        r'\b(my\s+)?(neighbor|friend|coworker|colleague)\s+\w+\s+(said|told|mentioned)\b',
        r'\b(witnesses?\s+)?saw\b',
        r'\baccording\s+to\b',
        r'\b(they|he|she)\s+later\s+told\s+me\b',
    ]
    for pattern in third_party_patterns:
        if re.search(pattern, text_lower):
            return ("third_party_report", "third_party", 0.75)
    
    return ("unknown", "self_report", 0.5)



def _classify_polarity(text: str) -> str:
    """Determine if statement is asserted, denied, or uncertain."""
    text_lower = text.lower()
    
    # Denial markers
    if re.search(r'\b(didn\'t|did not|never|wasn\'t|was not|weren\'t|were not)\b', text_lower):
        return "denied"
    
    # Uncertainty markers (expanded)
    if re.search(r'\b(might|maybe|perhaps|probably|possibly|could have|may have)\b', text_lower):
        return "uncertain"
    if re.search(r'\bi\s+(think|believe|guess|suppose)\b', text_lower):
        return "uncertain"
    if re.search(r'\b(it\s+)?seem(s|ed)\s+(like|that|to)\b', text_lower):
        return "uncertain"
    if re.search(r'\bapparently\b', text_lower):
        return "uncertain"
    
    # Hypothetical
    if re.search(r'\b(if|would have|could have been)\b', text_lower):
        return "hypothetical"
    
    return "asserted"


def tag_epistemic(ctx: TransformContext) -> TransformContext:
    """
    Tag every AtomicStatement with epistemic metadata.
    
    V4 Alpha: This is the core fix. Every statement gets tagged at
    extraction time with:
    - source
    - epistemic_type
    - polarity
    - evidence_source
    """
    if not ctx.atomic_statements:
        log.warning("no_statements", message="No atomic statements to tag")
        return ctx
    
    tagged_count = 0
    type_counts = {}
    
    for stmt in ctx.atomic_statements:
        # Classify epistemic type
        epistemic_type, evidence_source, confidence = _classify_epistemic(stmt.text)
        
        # Classify polarity
        polarity = _classify_polarity(stmt.text)
        
        # Set the fields
        stmt.epistemic_type = epistemic_type
        stmt.evidence_source = evidence_source
        stmt.polarity = polarity
        
        # Update confidence if classification is strong
        if confidence > stmt.confidence:
            stmt.confidence = confidence
        
        # Track counts
        type_counts[epistemic_type] = type_counts.get(epistemic_type, 0) + 1
        if epistemic_type != "unknown":
            tagged_count += 1
        
        # Add diagnostic for dangerous types
        if epistemic_type in ("interpretation", "legal_claim", "conspiracy_claim"):
            ctx.add_diagnostic(
                level="info",
                code=f"EPISTEMIC_{epistemic_type.upper()}",
                message=f"Statement classified as {epistemic_type}",
                source=PASS_NAME,
                affected_ids=[stmt.id],
            )
    
    log.info(
        "tagged_statements",
        total=len(ctx.atomic_statements),
        tagged=tagged_count,
        **type_counts,
    )
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="tagged_epistemic",
        after=f"Tagged {tagged_count}/{len(ctx.atomic_statements)} statements",
    )
    
    return ctx
