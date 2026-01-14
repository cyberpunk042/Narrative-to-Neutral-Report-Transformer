"""
Constrained Renderer — LLM-assisted rendering from IR.

Uses a constrained LLM to polish IR into fluent neutral text.

Per LLM policy:
- Generator input is IR, not raw text
- Generator proposes, does not decide  
- Output is reviewable/rejectable
- Ambiguity must be preserved, not resolved
"""

# TODO: Implement when NLP dependencies are added
# This will use a small instruction model constrained to:
# - Only render what IR contains
# - Not add meaning or resolve ambiguity
# - Produce multiple candidates for selection
