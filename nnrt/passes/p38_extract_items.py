"""
Pass 38 — Items Discovered Extraction

V7 / Stage 1: Extracts and categorizes items allegedly found during searches.

This pass creates ItemDiscovered objects for items mentioned in:
- Search descriptions
- Discovery mentions
- Seizure statements

Categories:
- personal_effects: wallet, phone, keys, etc.
- work_items: apron, uniform, badge, etc.
- valuables: cash, money, tips, etc.
- contraband: specific illegal substances
- unspecified_substances: vague "drugs", "pills" (needs clarification)
- weapons: firearms, knives, etc.
- other: uncategorized items

Logic migrated from V1 structured.py lines 828-1031.
"""

import re
from typing import List, Set, Dict, Any
from dataclasses import dataclass, field

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger

PASS_NAME = "p38_extract_items"
log = get_pass_logger(PASS_NAME)


@dataclass
class ItemDiscovered:
    """An item allegedly discovered during a search."""
    id: str
    description: str
    category: str  # personal_effects, work_items, valuables, contraband, unspecified_substances, weapons, other
    context: str = ""  # The sentence where it was discovered
    confidence: float = 0.8
    needs_clarification: bool = False  # True for vague substance terms


# Patterns that indicate discovery/seizure of items (V1 lines 835-839)
DISCOVERY_PATTERNS = [
    r'(?:he|she|they|officer|rodriguez|jenkins)\s+found\s+(.+?)(?:\.|$)',
    r'(?:he|she|they)\s+(?:took|seized|grabbed|confiscated)\s+(.+?)(?:\.|$)',
    r'(?:searched|searching).+?(?:found|discovered)\s+(.+?)(?:\.|$)',
]

# SPECIFIC illegal substances - these ARE contraband (V1 lines 843-848)
CONTRABAND_TERMS = {
    'cocaine', 'heroin', 'meth', 'methamphetamine', 'fentanyl',
    'crack', 'ecstasy', 'mdma', 'lsd', 'pcp',
    'marijuana', 'weed', 'cannabis',
    'paraphernalia', 'pipe', 'bong', 'syringe', 'needles',
}

# VAGUE substance terms - need clarification (V1 lines 851-854)
VAGUE_SUBSTANCE_TERMS = {
    'drugs', 'drug', 'pills', 'narcotics', 'controlled substance',
    'substances', 'medication', 'medicine', 'prescriptions',
}

# Weapon terms (V1 lines 856-859)
WEAPON_TERMS = {
    'gun', 'firearm', 'pistol', 'revolver', 'rifle', 'knife', 'blade',
    'weapon', 'brass knuckles', 'taser', 'ammunition', 'ammo', 'bullets',
}

# Personal effects (V1 lines 861-865)
PERSONAL_EFFECTS = {
    'wallet', 'phone', 'keys', 'id', 'identification', 'license',
    'credit card', 'debit card', 'cash', 'money', 'watch', 'ring',
    'glasses', 'sunglasses', 'bag', 'purse', 'backpack',
}

# Work-related items (V1 lines 867-870)
WORK_ITEMS = {
    'apron', 'uniform', 'badge', 'id badge', 'work id', 'tips',
    'employee', 'work', 'job',
}

# False positives to skip (V1 lines 909, 925)
FALSE_POSITIVE_STARTS = [
    'out', 'that', 'to be', 'it was', 'the', 'a ', 'an ', 'evidence', 'at least',
    'said', 'told', 'asked', 'yelled', 'screamed', 'whispered', 'replied',  # Quote markers
]

# Words/phrases that indicate sentence-like content (not items)
SENTENCE_WORDS = [
    'which proves', 'that at least', 'to be', 'the police', 'was', 'were', 'is', 'are',
    'they all', 'you did', 'i did', 'he did', 'she did', 'we did',  # Quote fragments
    'what they', 'what you', 'what he', 'what she', 'what we',  # Speech patterns
]

# Quote fragment patterns - skip items containing these
QUOTE_PATTERNS = [
    r'"[^"]*',  # Opens quote but doesn't close
    r"'[^']*",  # Single quote unclosed
    r'^sure\b', r'^right\b', r'^okay\b', r'^yeah\b', r'^yes\b', r'^no\b',  # Responses
    r'\bthey all\b', r'\byou did\b', r'\bi did\b',  # Assertions
]


def extract_items(ctx: TransformContext) -> TransformContext:
    """
    Extract and categorize items allegedly found during searches.
    
    V7 / Stage 1: Migrates item discovery logic from V1 renderer
    to populate ItemDiscovered objects during pipeline processing.
    
    Adds items to ctx.discovered_items (new field).
    """
    # Build full text from atomic statements
    all_text_parts = []
    
    if ctx.atomic_statements:
        for stmt in ctx.atomic_statements:
            text = getattr(stmt, 'text', str(stmt))
            all_text_parts.append(text)
    
    if ctx.events:
        for event in ctx.events:
            if event.description:
                all_text_parts.append(event.description)
    
    full_text = ' '.join(all_text_parts)
    
    if not full_text.strip():
        log.debug("no_text", message="No text to extract items from")
        return ctx
    
    # Extract items by category
    discovered_sets: Dict[str, Set[str]] = {
        'personal_effects': set(),
        'work_items': set(),
        'valuables': set(),
        'contraband': set(),
        'unspecified_substances': set(),
        'weapons': set(),
        'other': set(),
    }
    
    item_contexts: Dict[str, str] = {}  # item -> context sentence
    item_counter = 0
    
    for pattern in DISCOVERY_PATTERNS:
        for match in re.finditer(pattern, full_text, re.IGNORECASE):
            items_text = match.group(1)
            context = match.group(0)
            
            # Skip false positives
            if any(items_text.strip().lower().startswith(fp) for fp in FALSE_POSITIVE_STARTS):
                continue
            
            # Parse individual items
            items = re.split(r',\s*(?:and\s+)?|\s+and\s+', items_text)
            
            for item in items:
                item = item.strip().lower()
                
                # Skip empty or too short
                if not item or len(item) < 2:
                    continue
                
                # Skip if too long (not a real item)
                if len(item) > 60:
                    continue
                
                # Skip sentence-like content
                if any(word in item for word in SENTENCE_WORDS):
                    continue
                
                # V7 FIX: Skip quote fragments and speech-like content
                is_quote = False
                for pattern in QUOTE_PATTERNS:
                    if re.search(pattern, item, re.IGNORECASE):
                        is_quote = True
                        break
                if is_quote:
                    continue
                
                # Remove possessives
                item = re.sub(r'^my\s+', '', item)
                item = re.sub(r'^his\s+', '', item)
                item = re.sub(r'^her\s+', '', item)
                item = re.sub(r'^their\s+', '', item)
                
                # Classify the item
                category = _classify_item(item)
                if category:
                    discovered_sets[category].add(item)
                    item_contexts[item] = context
    
    # Create ItemDiscovered objects
    discovered_items: List[ItemDiscovered] = []
    
    for category, items in discovered_sets.items():
        for item_desc in items:
            item_counter += 1
            discovered_items.append(ItemDiscovered(
                id=f"item_{item_counter:03d}",
                description=item_desc,
                category=category,
                context=item_contexts.get(item_desc, ""),
                confidence=0.85 if category != 'other' else 0.6,
                needs_clarification=(category == 'unspecified_substances'),
            ))
    
    # Store in context (using a new field or extending existing)
    # For now, store as attribute
    ctx.discovered_items = discovered_items
    
    log.info(
        "extracted_items",
        total=len(discovered_items),
        categories={cat: len(items) for cat, items in discovered_sets.items() if items},
    )
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="extract_items",
        after=f"Extracted {len(discovered_items)} items from text",
    )
    
    return ctx


def _classify_item(item: str) -> str:
    """
    Classify an item into a category.
    
    Returns category name or 'other' for uncategorized.
    """
    item_lower = item.lower()
    
    # Check VAGUE SUBSTANCES first (drugs, pills, etc.)
    if any(term in item_lower for term in VAGUE_SUBSTANCE_TERMS):
        return 'unspecified_substances'
    
    # Then check SPECIFIC contraband (cocaine, heroin, meth)
    if any(term in item_lower for term in CONTRABAND_TERMS):
        return 'contraband'
    
    # Weapons
    if any(term in item_lower for term in WEAPON_TERMS):
        return 'weapons'
    
    # Work items
    if any(term in item_lower for term in WORK_ITEMS):
        return 'work_items'
    
    # Personal effects
    if any(term in item_lower for term in PERSONAL_EFFECTS):
        # Cash/money go to valuables
        if 'cash' in item_lower or 'money' in item_lower or 'tips' in item_lower:
            return 'valuables'
        return 'personal_effects'
    
    # Valuables (catch remaining money terms)
    if 'cash' in item_lower or 'money' in item_lower or 'tip' in item_lower:
        return 'valuables'
    
    # Only add to "other" if it looks like a real item
    if len(item) < 30:
        return 'other'
    
    return None  # Skip this item
