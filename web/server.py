"""
NNRT Web API — Flask backend for the web interface.

Provides REST endpoints for:
- /api/transform — Transform narrative text
- /api/history — Get/save transformation history
- /api/examples — Sample narratives for testing
"""

import json
import os
import signal
import subprocess
import sys
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
    use_llm = data.get('use_llm', False)
    
    if not text.strip():
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        # Set LLM mode based on request
        if use_llm:
            os.environ['NNRT_USE_LLM'] = '1'
        else:
            os.environ.pop('NNRT_USE_LLM', None)
        
        engine = get_engine()
        request_obj = TransformRequest(text=text)
        
        import time
        start_time = time.time()
        result = engine.transform(request_obj)
        processing_time_ms = round((time.time() - start_time) * 1000)
        
        # Build structured output
        structured = build_structured_output(result, text)
        
        # Organize identifiers by type for easy consumption
        identifiers_by_type = {}
        for ident in result.identifiers:
            type_key = ident.type.value if hasattr(ident.type, 'value') else str(ident.type)
            if type_key not in identifiers_by_type:
                identifiers_by_type[type_key] = []
            identifiers_by_type[type_key].append({
                'id': ident.id,
                'value': ident.value,
                'original_text': ident.original_text,
                'confidence': ident.confidence,
                'source_segment': ident.source_segment_id,
            })
        
        # Convert to dict with comprehensive structure
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
            
            # Identifiers extracted from the narrative
            'identifiers': [
                {
                    'id': ident.id,
                    'type': ident.type.value if hasattr(ident.type, 'value') else str(ident.type),
                    'value': ident.value,
                    'original_text': ident.original_text,
                    'confidence': ident.confidence,
                }
                for ident in result.identifiers
            ],
            
            # Stats
            'stats': {
                'segments': len(result.segments),
                'statements': len(structured.statements),
                'entities': len(structured.entities),
                'events': len(structured.events),
                'transformations': sum(len(s.transformations) for s in structured.statements),
                'identifiers': len(result.identifiers),
            },
            
            # Metadata header (request info)
            'metadata': {
                'request_id': request_obj.request_id,
                'processing_time_ms': processing_time_ms,
                'input_length': len(text),
                'output_length': len(result.rendered_text or ''),
                'pipeline': 'default',
                'llm_mode': use_llm,
                'version': '0.1.0-pre-alpha',
            },
            
            # Extracted metadata (from content)
            'extracted': identifiers_by_type,
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
    """Get example narratives for testing from examples.json."""
    examples_file = Path(__file__).parent / 'examples.json'
    
    try:
        with open(examples_file, 'r') as f:
            examples = json.load(f)
        return jsonify(examples)
    except FileNotFoundError:
        # Fallback if file is missing
        return jsonify([
            {
                'id': 'simple_1',
                'name': 'Simple Statement',
                'category': 'Simple',
                'text': 'The officer deliberately grabbed my arm.'
            }
        ])
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid examples.json: {e}'}), 500


def kill_existing_server(port: int = 5050) -> bool:
    """
    Kill any existing process listening on the specified port.
    Returns True if a process was killed, False otherwise.
    """
    try:
        # Find PIDs listening on this port
        result = subprocess.run(
            ['lsof', '-t', '-i', f':{port}'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            current_pid = str(os.getpid())
            
            for pid in pids:
                pid = pid.strip()
                if pid and pid != current_pid:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"   Killed existing process on port {port} (PID {pid})")
                    except (ProcessLookupError, PermissionError):
                        pass
            
            # Give processes time to die
            import time
            time.sleep(0.5)
            return True
            
    except FileNotFoundError:
        # lsof not available, try alternative
        pass
    except Exception as e:
        print(f"   Warning: Could not check for existing server: {e}")
    
    return False


if __name__ == '__main__':
    print("🚀 NNRT Web Interface starting...")
    
    # Auto-kill any existing server on this port
    kill_existing_server(5050)
    
    print("   Open: http://localhost:5050")
    # Note: use_reloader=False prevents terminal signal issues (SIGTSTP)
    # that can occur with Flask's stat reloader in some environments
    app.run(debug=True, port=5050, use_reloader=False)
