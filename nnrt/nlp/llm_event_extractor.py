"""
LLM-based Event Extraction for Observable Events.

V10: Uses LOCAL LLM (embedded) to extract camera-friendly, observable events.
No API key required - model runs locally in memory.

Supported models (in order of capability/size):
1. microsoft/Phi-3-mini-4k-instruct (~3.8B) - Best quality
2. Qwen/Qwen2-1.5B-Instruct (~1.5B) - Good balance
3. TinyLlama/TinyLlama-1.1B-Chat-v1.0 (~1.1B) - Fastest

Respects NNRT fundamentals:
- Only observable physical actions (camera-friendly)
- Proper actor attribution (named entities, not pronouns)
- Neutral language (no subjective characterizations)
- No interpretation or inference
"""

import json
import structlog
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

log = structlog.get_logger("nnrt.llm_event_extractor")

# Default model - Phi-3-mini is best balance of quality/speed
DEFAULT_MODEL = "microsoft/Phi-3-mini-4k-instruct"
FALLBACK_MODELS = [
    "Qwen/Qwen2-1.5B-Instruct",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
]

# System prompt for event extraction
EVENT_EXTRACTION_PROMPT = """Extract ONLY observable physical actions from this text.

Rules:
1. OBSERVABLE: Only actions visible on camera (not thoughts/feelings)
2. RESOLVE PRONOUNS: Replace "he/she/they" with actual names
3. NEUTRAL: Remove subjective words like "brutally", "viciously"
4. FORMAT: Return JSON array with actor, action, target fields

Known entities: {entities}

TEXT:
{text}

Return ONLY a JSON array, example format:
[{{"actor": "Officer Jenkins", "action": "grabbed", "target": "Reporter arm"}}]

JSON:"""


@dataclass
class ExtractedEvent:
    """An event extracted by the LLM."""
    actor: str
    action: str
    target: str
    source_text: str = ""


class LocalLLMEventExtractor:
    """Extract observable events using local embedded LLM."""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or DEFAULT_MODEL
        self._model = None
        self._tokenizer = None
        self._available = None
        self._device = None
        
    @property
    def available(self) -> bool:
        """Check if local LLM can be loaded."""
        if self._available is not None:
            return self._available
        
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Check for GPU
            if torch.cuda.is_available():
                self._device = "cuda"
                log.info("llm_device", device="cuda")
            else:
                self._device = "cpu"
                log.info("llm_device", device="cpu")
            
            self._available = True
            return True
            
        except ImportError as e:
            log.warning("llm_not_available", reason=f"Missing dependency: {e}")
            self._available = False
            return False
    
    def load_model(self) -> bool:
        """Load the model into memory. Call once at startup."""
        if self._model is not None:
            return True  # Already loaded
            
        if not self.available:
            return False
        
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        models_to_try = [self.model_name] + FALLBACK_MODELS
        
        for model_name in models_to_try:
            try:
                log.info("loading_model", model=model_name)
                
                self._tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                )
                
                # Load in appropriate precision
                dtype = torch.float16 if self._device == "cuda" else torch.float32
                
                self._model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=dtype,
                    device_map="auto" if self._device == "cuda" else None,
                    trust_remote_code=True,
                    low_cpu_mem_usage=True,
                )
                
                if self._device == "cpu":
                    self._model = self._model.to("cpu")
                
                self.model_name = model_name
                log.info("model_loaded", model=model_name, device=self._device)
                return True
                
            except Exception as e:
                log.warning("model_load_failed", model=model_name, error=str(e))
                continue
        
        log.error("all_models_failed")
        self._available = False
        return False
    
    def extract_events(self, text: str, entities: List[str] = None) -> List[ExtractedEvent]:
        """
        Extract observable events from text using local LLM.
        
        Args:
            text: The narrative text to extract events from
            entities: List of known entity names for reference
            
        Returns:
            List of ExtractedEvent objects
        """
        if not self.load_model():
            log.warning("llm_extraction_skipped", reason="Model not loaded")
            return []
        
        import torch
        
        # Build prompt
        entities_str = ", ".join(entities) if entities else "Reporter, Officers"
        prompt = EVENT_EXTRACTION_PROMPT.format(
            entities=entities_str,
            text=text[:2000],  # Limit text length
        )
        
        try:
            # Tokenize
            inputs = self._tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048,
            )
            
            if self._device == "cuda":
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.1,  # Low temperature for consistent output
                    do_sample=True,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            
            # Decode
            response = self._tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True,
            )
            
            # Parse events from response
            events = self._parse_events(response)
            
            log.info(
                "llm_events_extracted",
                event_count=len(events),
                model=self.model_name,
            )
            
            return events
            
        except Exception as e:
            log.error("llm_extraction_failed", error=str(e))
            return []
    
    def _parse_events(self, response: str) -> List[ExtractedEvent]:
        """Parse LLM response into ExtractedEvent objects."""
        events = []
        
        try:
            # Find JSON array in response
            start = response.find('[')
            end = response.rfind(']') + 1
            
            if start >= 0 and end > start:
                json_str = response[start:end]
                # Clean up common issues
                json_str = json_str.replace("'", '"')
                data = json.loads(json_str)
                
                for item in data:
                    if isinstance(item, dict) and item.get('actor'):
                        events.append(ExtractedEvent(
                            actor=item.get('actor', '').strip(),
                            action=item.get('action', '').strip(),
                            target=item.get('target', '').strip(),
                        ))
        except json.JSONDecodeError as e:
            log.warning("json_parse_failed", error=str(e), response=response[:200])
            # Try line-by-line fallback
            events = self._parse_events_fallback(response)
        
        return events
    
    def _parse_events_fallback(self, response: str) -> List[ExtractedEvent]:
        """Fallback parser for non-JSON responses."""
        events = []
        # Look for patterns like "Actor action target" or bullet points
        import re
        
        # Match patterns like "• Officer Jenkins grabbed arm"
        pattern = r'[•\-\*]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+([\w]+(?:ed|s)?)\s+(.+?)(?:\.|$)'
        
        for match in re.finditer(pattern, response):
            events.append(ExtractedEvent(
                actor=match.group(1).strip(),
                action=match.group(2).strip(),
                target=match.group(3).strip(),
            ))
        
        return events


# Singleton instance
_extractor: Optional[LocalLLMEventExtractor] = None


def get_llm_event_extractor() -> LocalLLMEventExtractor:
    """Get the local LLM event extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = LocalLLMEventExtractor()
    return _extractor


def preload_model(model_name: str = None) -> bool:
    """
    Preload the LLM model into memory.
    Call this at application startup for faster first extraction.
    
    Args:
        model_name: Optional model to use (default: Phi-3-mini)
        
    Returns:
        True if model loaded successfully
    """
    global _extractor
    _extractor = LocalLLMEventExtractor(model_name)
    return _extractor.load_model()


def extract_observable_events(text: str, entities: List[str] = None) -> List[Dict]:
    """
    High-level function to extract observable events using local LLM.
    
    Returns list of dicts with actor, action, target, sentence.
    Falls back to empty list if LLM unavailable.
    """
    extractor = get_llm_event_extractor()
    events = extractor.extract_events(text, entities)
    
    result = []
    for ev in events:
        # Build camera-friendly sentence
        if ev.target:
            sentence = f"{ev.actor} {ev.action} {ev.target}."
        else:
            sentence = f"{ev.actor} {ev.action}."
        
        # Capitalize and clean up
        sentence = sentence[0].upper() + sentence[1:] if sentence else ""
        sentence = sentence.replace("  ", " ").strip()
        
        result.append({
            'actor': ev.actor,
            'action': ev.action,
            'target': ev.target,
            'sentence': sentence,
        })
    
    return result
