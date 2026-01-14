"""
NNRT Web API — Flask backend for the web interface.

Provides REST endpoints for:
- /api/transform — Transform narrative text
- /api/history — Get/save transformation history
- /api/examples — Sample narratives for testing
"""

import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from nnrt.core.context import TransformRequest
from nnrt.core.engine import Engine
from nnrt.cli.main import setup_default_pipeline
from nnrt.output.structured import build_structured_output

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# History storage directory
HISTORY_DIR = Path(__file__).parent / "history"
HISTORY_DIR.mkdir(exist_ok=True)

# Initialize engine once
_engine = None

def get_engine():
    """Get or create the transformation engine."""
    global _engine
    if _engine is None:
        _engine = Engine()
        setup_default_pipeline(_engine)
    return _engine


# =============================================================================
# API Routes
# =============================================================================

@app.route('/')
def index():
    """Serve the main interface."""
    return send_from_directory('.', 'index.html')


@app.route('/api/transform', methods=['POST'])
def transform():
    """Transform narrative text to neutral representation."""
    data = request.json
    text = data.get('text', '')
    
    if not text.strip():
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        engine = get_engine()
        request_obj = TransformRequest(text=text)
        result = engine.transform(request_obj)
        
        # Build structured output
        structured = build_structured_output(result, text)
        
        # Convert to dict
        output = {
            'id': str(uuid4())[:8],
            'timestamp': datetime.now().isoformat(),
            'status': result.status.value,
            'input': text,
            'rendered_text': result.rendered_text,
            'statements': [s.model_dump() for s in structured.statements],
            'entities': [e.model_dump() for e in structured.entities],
            'events': [e.model_dump() for e in structured.events],
            'uncertainties': [u.model_dump() for u in structured.uncertainties],
            'diagnostics': [
                {'level': d.level, 'code': d.code, 'message': d.message}
                for d in result.diagnostics
            ],
            'stats': {
                'segments': len(result.segments),
                'statements': len(structured.statements),
                'entities': len(structured.entities),
                'events': len(structured.events),
                'transformations': sum(len(s.transformations) for s in structured.statements),
            }
        }
        
        return jsonify(output)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get transformation history."""
    history = []
    
    for file in sorted(HISTORY_DIR.glob('*.json'), reverse=True)[:50]:
        try:
            with open(file) as f:
                item = json.load(f)
                history.append({
                    'id': item.get('id'),
                    'timestamp': item.get('timestamp'),
                    'preview': item.get('input', '')[:100] + '...',
                    'status': item.get('status'),
                })
        except:
            pass
    
    return jsonify(history)


@app.route('/api/history', methods=['POST'])
def save_history():
    """Save transformation to history."""
    data = request.json
    
    if not data.get('id'):
        return jsonify({'error': 'No id provided'}), 400
    
    filepath = HISTORY_DIR / f"{data['id']}.json"
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return jsonify({'saved': True})


@app.route('/api/history/<item_id>', methods=['GET'])
def get_history_item(item_id):
    """Get a specific history item."""
    filepath = HISTORY_DIR / f"{item_id}.json"
    
    if not filepath.exists():
        return jsonify({'error': 'Not found'}), 404
    
    with open(filepath) as f:
        return jsonify(json.load(f))


@app.route('/api/examples', methods=['GET'])
def get_examples():
    """Get example narratives for testing."""
    examples = [
        {
            'id': 'intent_attribution',
            'name': 'Intent Attribution',
            'category': 'Basic',
            'text': 'The officer intentionally grabbed my arm and deliberately twisted it behind my back. He obviously wanted to hurt me.'
        },
        {
            'id': 'legal_conclusions',
            'name': 'Legal Conclusions',
            'category': 'Legal',
            'text': 'He assaulted me and committed battery. The brutal cop is guilty of police brutality.'
        },
        {
            'id': 'mixed_quotes',
            'name': 'Quote Preservation',
            'category': 'Speech',
            'text': 'She said "Get out of the car now!" Then I asked "Why are you stopping me?" She replied that I was being arrested.'
        },
        {
            'id': 'charges_context',
            'name': 'Charge Context',
            'category': 'Legal',
            'text': 'I was charged with assault on a police officer and resisting arrest. The officer accused me of attacking him, which is completely false.'
        },
        {
            'id': 'physical_force',
            'name': 'Physical Force',
            'category': 'Physical',
            'text': 'He grabbed my neck and choked me. I tried to say "I can\'t breathe" but he wouldn\'t let go. His partner punched me in the stomach.'
        },
        {
            'id': 'ambiguous_refs',
            'name': 'Ambiguous References',
            'category': 'Complex',
            'text': 'John told Mike that he was going to arrest him. Then someone else came and they started arguing. He pushed him against the wall.'
        },
        {
            'id': 'emotional_narrative',
            'name': 'Emotional Narrative',
            'category': 'Inflammatory',
            'text': 'This psycho cop viciously attacked me for no reason. The thug brutally slammed me to the ground and destroyed my life.'
        },
        {
            'id': 'already_neutral',
            'name': 'Already Neutral',
            'category': 'Edge Case',
            'text': 'At approximately 10:30 PM, the vehicle was stopped at the intersection. The officer approached and requested identification.'
        },
        {
            'id': 'full_incident',
            'name': 'Full Incident Report',
            'category': 'Complex',
            'text': '''I was walking home from work on January 15th around 11:30 PM when I saw a police cruiser pull up beside me. Officer badge number 4821 stepped out and yelled "Stop right there!" I stopped and asked "What's the problem, officer?" He intentionally grabbed my arm and said I matched the description of a robbery suspect. I told him "I just got off work" but he obviously didn't believe me. He twisted my arm behind my back, which hurt. His partner just watched. I was charged with resisting arrest.'''
        },
    ]
    
    return jsonify(examples)


if __name__ == '__main__':
    print("🚀 NNRT Web Interface starting...")
    print("   Open: http://localhost:5050")
    app.run(debug=True, port=5050)
