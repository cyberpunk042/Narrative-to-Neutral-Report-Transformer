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

# V5: Self-reported ACUTE state (during incident - fear, shock)
STATE_ACUTE_PATTERNS = [
    r'\b(i\s+)?was\s+(so\s+)?(scared|terrified|frightened|afraid|anxious)\b',
    r'\b(i\s+)?was\s+(absolutely\s+)?(terrified|shocked|stunned|horrified)\b',
    r'\b(i\s+)?was\s+in\s+(complete\s+)?(shock|disbelief)\b',
    r'\bi\s+froze\b',
    r'\bfelt\s+(scared|terrified|afraid)\b',
    r'\bmy\s+(fear|terror)\b',
]

# V5: Self-reported INJURY (physical after-effects)
STATE_INJURY_PATTERNS = [
    r'\bwrists?\s+were\s+(bleeding|bruised)\b',
    r'\bbruised\b',
    r'\b(bleeding|cuts?|abrasions?|sprained?|broken)\b',
    r'\bi\s+have\s+(permanent|chronic)\s+(scars?|injuries?)\b',
    r'\b(injuries?|wounds?)\s+(to|on)\s+my\b',
    r'\bi\s+was\s+in\s+pain\b',
    r'\bi\s+screamed\s+in\s+pain\b',
]

# V5: Self-reported PSYCHOLOGICAL (long-term mental health)
STATE_PSYCHOLOGICAL_PATTERNS = [
    r'\bi\s+(now\s+)?suffer\s+from\s+(ptsd|anxiety|depression)\b',
    r'\bpanic\s+attacks?\b',
    r'\bpsychological\s+trauma\b',
    r'\bi\s+can\s+no\s+longer\b',
    r'\bpost.?traumatic\s+stress\b',
    r'\b(nightmares?|flashbacks?|insomnia)\b',
]

# V5: Self-reported SOCIOECONOMIC (job loss, lifestyle impact)
STATE_SOCIOECONOMIC_PATTERNS = [
    r'\blost\s+my\s+job\b',
    r'\bcould\s?n\'?t\s+show\s+up\b',
    r'\bcan\'?t\s+work\b',
    r'\bfear\s+of\s+going\s+outside\b',
    r'\bcan\s+no\s+longer\s+walk\s+outside\b',
]

# V5: Legacy combined pattern (for backward compatibility)
SELF_REPORT_PATTERNS = (
    STATE_ACUTE_PATTERNS + 
    STATE_INJURY_PATTERNS + 
    STATE_PSYCHOLOGICAL_PATTERNS + 
    STATE_SOCIOECONOMIC_PATTERNS +
    [
        # General self-report (not in specific sub-category)
        r'\b(i\s+)?was\s+(exhausted|tired|drained|overwhelmed)\b',
        r'\b(i\s+)?felt\s+\w+',
        r'\bit\s+felt\s+like\b',
        r'\bi\s+just\s+wanted\b',
        r'\bafter\s+pulling\s+a\s+.*shift\b',
        r'\bi\s+could\s?n\'?t\s+hear\b',
        r'\bthey\s+kept\s+looking\b',
        r'\bshaking\s+(their\s+)?heads?\b',
    ]
)

# V5: CHARACTERIZATION (subjective adjectives, insults, name-calling)
# These are opinion words, not inferences about intent
CHARACTERIZATION_PATTERNS = [
    r'\bthug\s*(cop|cops|police|officer)?\b',
    r'\bpsychotic\b',
    r'\bmaniac\b',
    r'\bbrutal\b',
    r'\bvicious\b',
    r'\bcorrupt\b',
    r'\bviolent\s+(?:cop|cops|officer|officers|police)\b',
    r'\blike\s+a\s+(criminal|maniac|thug|animal)\b',
    r'\bknown\s+(violent|criminal)\s+offender\b',
    r'\bhistory\s+of\s+(brutality|violence|abuse)\b',
    r'\bvictimizing\s+(innocent|people|citizens)\b',
    r'\bdismissive\s+attitude\b',
]

# V5: INFERENCE (intent attribution, mental state inference - claims about what someone was thinking)
# These go beyond description to claim knowledge of intent/motive
INFERENCE_PATTERNS = [
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
    r'\b(he|she|they)\s+obviously\b',
    r'\bit\s+was\s+obvious\b',
    r'\bdesigned\s+to\s+(?:protect|cover|hide|intimidate)\b',
    r'\bfishing\s+through\b',
]

# V5: Legacy combined pattern (for backward compatibility)
INTERPRETATION_PATTERNS = CHARACTERIZATION_PATTERNS + INFERENCE_PATTERNS

# =============================================================================
# P2 FIX: Split Legal Claims into Sub-Categories (Issue #2)
# =============================================================================
# Legal allegations bucket was mixing different epistemic classes:
# - Direct legal allegations ("excessive force", "false arrest")
# - Admin outcomes ("IA found within policy")
# - Medical causation ("PTSD directly caused by")
# - Attorney opinions ("attorney says this is clearest case")
#
# These are now separate sub-types for taxonomy purity.
# =============================================================================

# LEGAL_CLAIM_DIRECT: Pure legal allegations made by reporter
# These are claims about law violation, not admin or medical
LEGAL_CLAIM_DIRECT_PATTERNS = [
    r'\bwithout\s+(my\s+)?consent\b',
    r'\bwithout\s+(any\s+)?legal\s+justification\b',
    r'\billegal\s+(assault|search|detention|arrest|stop)\b',
    r'\bexcessive\s+(force|violence)\b',
    r'\bexcessive\s+(and\s+)?\w*\s*(force|violence)\b',  # "excessive and unnecessary violence"
    r'\bpolice\s+(brutality|misconduct)\b',
    r'\bcivil\s+rights\s+violations?\b',  # singular or plural
    r'\bviolated\s+(my|his|her|their|our)\s+(civil\s+)?rights\b',
    r'\bfalse\s+(imprisonment|arrest)\b',
    r'\bconstitutional\s+rights\b',
    r'\bobstruction\s+of\s+justice\b',
    r'\bwitness\s+intimidation\b',
    r'\bracial\s+profiling\b',
    r'\bcriminal\s+behavior\b',
    r'\bcomplete\s+(and\s+total\s+)?lie\b',
    r'\bfabricated\b',
    r'\bwhitewash\b',
    r'\bcover.?up\b',
    r'\bcorrupt(ion)?\b',
    r'\bharassment\b',
    r'\bassault\s+and\s+battery\b',
    r'\bassaulted\s+(me|him|her|them|us)\b',
    r'\bno\s+legal\s+basis\b',
    r'\bthe\s+racism\b',
]

# LEGAL_CLAIM_ADMIN: Administrative outcomes (IA, policy findings, letters)
# These are document-based findings, not allegations
LEGAL_CLAIM_ADMIN_PATTERNS = [
    r'\breceived\s+a\s+letter\b',
    r'\bfiled\s+a\s+(formal\s+)?complaint\b',
    r'\bformal\s+complaint\b',
    r'\bcomplaint\s+had\s+been\s+investigated\b',
    r'\binternal\s+affairs\b',
    r'\bfound\s+to\s+be\b.*\bpolicy\b',
    r'\bwithin\s+policy\b',
    r'\b(ia|internal\s+affairs)\s+(found|concluded|determined)\b',
    r'\bdepartment\s+(ruled|found|concluded)\b',
    r'\bcleared\s+of\s+(any\s+)?(wrongdoing|misconduct)\b',
    r'\bexonerated\b',
    r'\bsustained\s+(the\s+)?complaint\b',
    r'\bunsustained\b',
    r'\bunfounded\b',
]

# LEGAL_CLAIM_CAUSATION: Medical/psychological causation claims
# These link a condition to an event ("PTSD directly caused by")
LEGAL_CLAIM_CAUSATION_PATTERNS = [
    r'\b(ptsd|anxiety|depression|trauma)\s+(directly\s+)?(caused|resulted\s+from)\b',
    r'\bcaused\s+by\s+(the\s+)?(incident|stop|arrest|assault|encounter)\b',
    r'\b(injuries?|condition)\s+(were|was)\s+(directly\s+)?(caused|result)\b',
    r'\bdirectly\s+(caused|resulted|led\s+to)\b',
    r'\bas\s+a\s+(direct\s+)?result\s+of\b',
    r'\bdue\s+to\s+(the\s+)?(trauma|incident|assault|actions?)\b',
    r'\bsuffering\s+(as\s+a\s+)?(direct\s+)?result\b',
]

LEGAL_CLAIM_ATTORNEY_PATTERNS = [
    r'\b(my\s+)?(attorney|lawyer)\s+(says?|said|told|believes?|thinks?|stated)\b',
    r'\b(my\s+)?(attorney|lawyer)\s+\w+\s+\w+\s+(says?|said|told|believes?)\b',  # "My attorney Jennifer Walsh says"
    r'\battorney\s+(opinion|assessment|evaluation)\b',
    r'\b(clearest|strongest|most\s+egregious)\s+(case|example)\b',
    r'\blegally\s+(speaking|qualified)\b',
    r'\bfrom\s+a\s+legal\s+standpoint\b',
    r'\b(my\s+)?lawyer\s+(has|thinks?|believes?|says?)\b',
    r'\blegal\s+counsel\s+(advised|recommended|stated)\b',
    r'\bper\s+(my\s+)?(attorney|lawyer|legal)\b',
]

# Legacy combined pattern (for backward compatibility)
LEGAL_CLAIM_PATTERNS = (
    LEGAL_CLAIM_DIRECT_PATTERNS + 
    LEGAL_CLAIM_ADMIN_PATTERNS + 
    LEGAL_CLAIM_CAUSATION_PATTERNS + 
    LEGAL_CLAIM_ATTORNEY_PATTERNS
)

# Direct quote markers
QUOTE_PATTERNS = [
    r'^["\']',
    r'^\w+\s+said\s+["\']',
    r'^\w+\s+yelled\s+["\']',
    r'^\w+\s+told\s+(me|him|her|them)\s+["\']',
]

# Document-based / administrative (legacy, now mostly in LEGAL_CLAIM_ADMIN)
DOCUMENT_PATTERNS = [
    r'\breceived\s+a\s+letter\b',
    r'\bfiled\s+a\s+(formal\s+)?complaint\b',
    r'\bformal\s+complaint\b',
    r'\bcomplaint\s+had\s+been\s+investigated\b',
    r'internal\s+affairs\b',
    r'\bfound\s+to\s+be\b.*\bpolicy\b',
]
# =============================================================================
# P1 FIX: Medical documentation (when attributed to medical provider)
# =============================================================================
# Issue #3: Medical content was being misclassified as self-report
# These patterns MUST be checked BEFORE self-report injury patterns
# to correctly attribute provider findings vs reporter claims
# =============================================================================

MEDICAL_FINDING_PATTERNS = [
    # Doctor as subject (explicit title) - allow name after title
    r'\b(dr\.?|doctor)\s+\w+\s+(documented|said|diagnosed|noted|found|observed|recorded)\b',
    r'\b(dr\.?|doctor)\s+\w+\s+\w+\s+(documented|said|diagnosed|noted|found|observed|recorded)\b',  # "Dr. Amanda Foster documented"
    r'\b(the\s+)?(doctor|physician|nurse|emt|ems|paramedic|attendant)\s+(documented|noted|found|observed|said|recorded)\b',
    
    # Provider pronoun patterns (key fix for Issue #3)
    # When "she/he" refers to a medical provider and documents medical info
    # Allow optional words between verb and medical term (e.g., "the", "my", "several")
    r'\b(she|he)\s+documented\s+(\w+\s+)*(bruises?|injuries?|wounds?|trauma|lacerations?)\b',
    r'\b(she|he)\s+noted\s+(\w+\s+)*(bruises?|injuries?|wounds?|condition|swelling|redness)\b',
    r'\b(she|he)\s+found\s+(\w+\s+)*(bruises?|trauma|injuries?|fractures?|contusions?)\b',
    r'\b(she|he)\s+observed\s+(\w+\s+)*(bruises?|injuries?|swelling|redness|marks?)\b',
    r'\b(she|he)\s+photographed\s+(\w+\s+)*(injuries?|bruises?|wounds?)\b',
    r'\b(she|he)\s+recorded\s+(\w+\s+)*(injuries?|condition|symptoms)\b',
    
    # Medical provider as subject (title then action)
    r'\b(the\s+)?(nurse|emt|paramedic|physician)\s+(saw|examined|treated|noted|documented)\b',
    r'\b(my\s+)?(doctor|physician)\s+(told\s+me|said|confirmed|diagnosed)\b',
    
    # Medical documentation markers
    r'\bmedical\s+records?\s+(show|indicate|document|state|reflect)\b',
    r'\bmedical\s+report\s+(states?|shows?|indicates?)\b',
    r'\b(er|emergency\s+room)\s+(staff|doctor|nurse)\s+(noted|documented|recorded)\b',
    r'\b(hospital|clinic)\s+(records?|documentation)\s+(show|indicate)\b',
    
    # Diagnosed patterns (provider is implicit source)
    r'\bdiagnosed\s+(me\s+)?with\b',
    r'\bi\s+was\s+diagnosed\s+(with|as\s+having)\b',
    r'\binjuries\s+were\s+consistent\s+with\b',
    r'\bmedical\s+examination\s+(revealed|showed|found)\b',
    r'\bx.?ray\s+(showed|revealed|confirmed)\b',
    r'\b(ct|mri|scan)\s+(showed|revealed|found)\b',
    
    # Attribution to medical source
    r'\baccording\s+to\s+(my\s+)?(doctor|physician|the\s+medical)\b',
    r'\bper\s+(the\s+)?(medical|doctor|physician)\b',
    r'\b(the\s+)?medical\s+(professional|staff|team)\s+(said|noted|documented)\b',
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
    
    V5: Returns fine-grained sub-types for self-reports and interpretations.
    
    Returns (epistemic_type, evidence_source, confidence).
    """
    text_lower = text.lower()
    
    # Check patterns in priority order (most specific first)
    
    # 1. Conspiracy claims (highest priority - most dangerous)
    for pattern in CONSPIRACY_PATTERNS:
        if re.search(pattern, text_lower):
            return ("conspiracy_claim", "inference", 0.9)
    
    # 2. P2 FIX: Legal claims with sub-types for taxonomy purity
    # Check specific sub-types first, then fall back to generic
    
    # 2a. Attorney opinions (professional opinion, highest specificity)
    for pattern in LEGAL_CLAIM_ATTORNEY_PATTERNS:
        if re.search(pattern, text_lower):
            return ("legal_claim_attorney", "opinion", 0.85)
    
    # 2b. Medical/psych causation claims (links condition to event)
    for pattern in LEGAL_CLAIM_CAUSATION_PATTERNS:
        if re.search(pattern, text_lower):
            return ("legal_claim_causation", "inference", 0.85)
    
    # 2c. Admin outcomes (IA findings, policy determinations)
    for pattern in LEGAL_CLAIM_ADMIN_PATTERNS:
        if re.search(pattern, text_lower):
            return ("legal_claim_admin", "document", 0.85)
    
    # 2d. Direct legal allegations (fallback for other legal claims)
    for pattern in LEGAL_CLAIM_DIRECT_PATTERNS:
        if re.search(pattern, text_lower):
            return ("legal_claim_direct", "inference", 0.85)
    
    # 3. V5: CHARACTERIZATION (name-calling, insults - distinct from inference)
    for pattern in CHARACTERIZATION_PATTERNS:
        if re.search(pattern, text_lower):
            return ("characterization", "opinion", 0.85)
    
    # 4. V5: INFERENCE (intent/motive attribution)
    for pattern in INFERENCE_PATTERNS:
        if re.search(pattern, text_lower):
            return ("inference", "inference", 0.85)
    
    # 5. P1 FIX: Medical findings BEFORE self-report
    # This is critical for Issue #3: "She documented bruises" should be
    # medical_finding, not state_injury. Medical provider as subject changes
    # the provenance from self-report to document.
    for pattern in MEDICAL_FINDING_PATTERNS:
        if re.search(pattern, text_lower):
            return ("medical_finding", "document", 0.90)
    
    # 6. V5: Self-reported with sub-types
    # Only check these AFTER medical findings to avoid mis-classification
    for pattern in STATE_PSYCHOLOGICAL_PATTERNS:
        if re.search(pattern, text_lower):
            return ("state_psychological", "self_report", 0.9)
    
    for pattern in STATE_SOCIOECONOMIC_PATTERNS:
        if re.search(pattern, text_lower):
            return ("state_socioeconomic", "self_report", 0.9)
    
    for pattern in STATE_INJURY_PATTERNS:
        if re.search(pattern, text_lower):
            return ("state_injury", "self_report", 0.9)
    
    for pattern in STATE_ACUTE_PATTERNS:
        if re.search(pattern, text_lower):
            return ("state_acute", "self_report", 0.9)
    
    # General self-report (fallback)
    for pattern in SELF_REPORT_PATTERNS:
        if re.search(pattern, text_lower):
            return ("self_report", "self_report", 0.9)
    
    # 7. Administrative/document-based
    for pattern in DOCUMENT_PATTERNS:
        if re.search(pattern, text_lower):
            return ("admin_action", "document", 0.8)
    
    # 8. Direct quotes
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
        
        # =====================================================================
        # V6: Honest Provenance Status (Invariant: verified requires evidence)
        # =====================================================================
        # CRITICAL: "verified" can ONLY be used with non-reporter source.
        # Reporter content is "self_attested" - not externally verified.
        # =====================================================================
        
        if epistemic_type == "medical_finding":
            stmt.source_type = "medical"
            stmt.provenance_status = "cited"  # Has provider attribution
        elif epistemic_type == "admin_action":
            stmt.source_type = "document"
            stmt.provenance_status = "cited"  # Document reference
        elif epistemic_type in ("self_report", "state_acute", "state_injury", 
                                 "state_psychological", "state_socioeconomic"):
            stmt.source_type = "reporter"
            stmt.provenance_status = "self_attested"  # V6: Not verified without evidence
        elif epistemic_type == "direct_event":
            stmt.source_type = "reporter"
            stmt.provenance_status = "self_attested"  # V6: Reporter's observation, not externally verified
        elif epistemic_type in ("interpretation", "inference", "characterization"):
            stmt.source_type = "reporter"
            stmt.provenance_status = "inference"  # Reporter's subjective interpretation
        elif epistemic_type in ("legal_claim", "conspiracy_claim"):
            stmt.source_type = "reporter"
            stmt.provenance_status = "needs_provenance"  # V6: Clear label for missing verification
        elif epistemic_type == "third_party_report":
            stmt.source_type = "witness"
            stmt.provenance_status = "cited"  # Attributed to named witness
        elif epistemic_type == "quote":
            stmt.source_type = "reporter"
            stmt.provenance_status = "cited"  # Attributed speech
        else:
            stmt.source_type = "reporter"
            stmt.provenance_status = "needs_provenance"  # Unknown - needs provenance
        
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
