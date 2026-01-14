"""
NNRT Web API — Flask backend for the web interface.

Provides REST endpoints for:
- /api/transform — Transform narrative text
- /api/transform-stream — Transform with real-time streaming logs (SSE)
- /api/history — Get/save transformation history
- /api/examples — Sample narratives for testing
"""

import json
import os
import signal
import subprocess
import sys
import time
import logging
import queue
import threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS

from nnrt.core.context import TransformRequest
from nnrt.core.engine import Engine
from nnrt.cli.main import setup_default_pipeline, setup_raw_pipeline, setup_structured_only_pipeline
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
    mode = data.get('mode', 'prose')  # prose, structured, raw
    no_prose = data.get('no_prose', False)  # Fast mode - skip prose rendering
    
    if not text.strip():
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        # Set LLM mode based on request
        if use_llm:
            os.environ['NNRT_USE_LLM'] = '1'
        else:
            os.environ.pop('NNRT_USE_LLM', None)
        
        # Create a fresh engine for each request to handle mode changes
        engine = Engine()
        
        # Select pipeline based on mode
        if mode == 'raw':
            setup_raw_pipeline(engine)
            pipeline_id = 'raw'
        elif no_prose or mode == 'structured':
            setup_structured_only_pipeline(engine)
            pipeline_id = 'structured_only'
        else:
            setup_default_pipeline(engine)
            pipeline_id = 'default'
        
        request_obj = TransformRequest(text=text)
        
        import time
        start_time = time.time()
        result = engine.transform(request_obj, pipeline_id)
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
        
        # Build atomic statements from result
        atomic_statements_output = []
        for stmt in result.atomic_statements:
            stmt_type = stmt.type_hint.value if hasattr(stmt.type_hint, 'value') else str(stmt.type_hint)
            atomic_statements_output.append({
                'id': stmt.id,
                'type': stmt_type,
                'text': stmt.text,
                'segment_id': stmt.segment_id,
                'confidence': stmt.confidence,
                'clause_type': stmt.clause_type,
                'connector': stmt.connector,
                'derived_from': stmt.derived_from,
                'flags': stmt.flags,
            })
        
        # Convert to dict with comprehensive structure
        output = {
            'id': str(uuid4())[:8],
            'timestamp': datetime.now().isoformat(),
            'status': result.status.value,
            'input': text,
            'rendered_text': result.rendered_text if not no_prose else None,
            'statements': [s.model_dump() for s in structured.statements],
            
            # NEW: Atomic statements from decomposition
            'atomic_statements': atomic_statements_output,
            
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
                'atomic_statements': len(atomic_statements_output),
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
                'pipeline': pipeline_id,
                'mode': mode,
                'no_prose': no_prose,
                'llm_mode': use_llm,
                'version': '0.3.0',
            },
            
            # Extracted metadata (from content)
            'extracted': identifiers_by_type,
        }
        
        return jsonify(output)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Streaming Transform (SSE)
# =============================================================================

class LogCapture(logging.Handler):
    """Custom logging handler that captures logs to a queue."""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        self.setFormatter(logging.Formatter('%(message)s'))
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put({
                'type': 'log',
                'level': record.levelname.lower(),
                'message': msg,
                'timestamp': datetime.now().isoformat()
            })
        except Exception:
            pass


@app.route('/api/transform-stream', methods=['POST'])
def transform_stream():
    """Transform with real-time streaming logs via Server-Sent Events."""
    data = request.json
    text = data.get('text', '')
    use_llm = data.get('use_llm', False)
    mode = data.get('mode', 'prose')
    no_prose = data.get('no_prose', False)
    
    if not text.strip():
        return jsonify({'error': 'No text provided'}), 400
    
    def generate():
        log_queue = queue.Queue()
        
        # Set up log capture
        nnrt_logger = logging.getLogger('nnrt')
        handler = LogCapture(log_queue)
        handler.setLevel(logging.INFO)
        nnrt_logger.addHandler(handler)
        
        result_holder = {'result': None, 'error': None}
        
        def run_transform():
            try:
                # Set LLM mode
                if use_llm:
                    os.environ['NNRT_USE_LLM'] = '1'
                else:
                    os.environ.pop('NNRT_USE_LLM', None)
                
                engine = Engine()
                
                # Select pipeline
                if mode == 'raw':
                    setup_raw_pipeline(engine)
                    pipeline_id = 'raw'
                elif no_prose or mode == 'structured':
                    setup_structured_only_pipeline(engine)
                    pipeline_id = 'structured_only'
                else:
                    setup_default_pipeline(engine)
                    pipeline_id = 'default'
                
                log_queue.put({'type': 'log', 'level': 'info', 'message': f'Pipeline: {pipeline_id}', 'timestamp': datetime.now().isoformat()})
                
                request_obj = TransformRequest(text=text)
                log_queue.put({'type': 'log', 'level': 'info', 'message': f'Processing {len(text)} characters...', 'timestamp': datetime.now().isoformat()})
                
                result = engine.transform(request_obj, pipeline_id)
                result_holder['result'] = result
                
                log_queue.put({'type': 'log', 'level': 'info', 'message': f'Transform complete: {result.status.value}', 'timestamp': datetime.now().isoformat()})
                
            except Exception as e:
                import traceback
                result_holder['error'] = str(e)
                log_queue.put({'type': 'error', 'message': str(e), 'timestamp': datetime.now().isoformat()})
                traceback.print_exc()
            finally:
                log_queue.put({'type': 'done'})
        
        # Start transform in background thread
        thread = threading.Thread(target=run_transform)
        thread.start()
        
        # Stream logs as they arrive
        while True:
            try:
                item = log_queue.get(timeout=30)  # 30 second timeout
                
                if item['type'] == 'done':
                    break
                
                yield f"data: {json.dumps(item)}\n\n"
                
            except queue.Empty:
                # Send keepalive
                yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
        
        # Wait for thread to finish
        thread.join(timeout=5)
        
        # Remove handler
        nnrt_logger.removeHandler(handler)
        
        # Send final result
        if result_holder['error']:
            yield f"data: {json.dumps({'type': 'error', 'message': result_holder['error']})}\n\n"
        elif result_holder['result']:
            result = result_holder['result']
            structured = build_structured_output(result, text)
            
            # Build atomic statements
            atomic_statements_output = []
            for stmt in result.atomic_statements:
                stmt_type = stmt.type_hint.value if hasattr(stmt.type_hint, 'value') else str(stmt.type_hint)
                atomic_statements_output.append({
                    'id': stmt.id,
                    'type': stmt_type,
                    'text': stmt.text,
                    'segment_id': stmt.segment_id,
                    'confidence': stmt.confidence,
                    'clause_type': stmt.clause_type,
                    'connector': stmt.connector,
                    'derived_from': stmt.derived_from,
                    'flags': stmt.flags,
                })
            
            output = {
                'type': 'result',
                'id': str(uuid4())[:8],
                'timestamp': datetime.now().isoformat(),
                'status': result.status.value,
                'input': text,
                'rendered_text': result.rendered_text if not no_prose else None,
                'statements': [s.model_dump() for s in structured.statements],
                'atomic_statements': atomic_statements_output,
                'entities': [e.model_dump() for e in structured.entities],
                'events': [e.model_dump() for e in structured.events],
                'uncertainties': [u.model_dump() for u in structured.uncertainties],
                'diagnostics': [
                    {'level': d.level, 'code': d.code, 'message': d.message}
                    for d in result.diagnostics
                ],
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
                'stats': {
                    'segments': len(result.segments),
                    'statements': len(structured.statements),
                    'atomic_statements': len(atomic_statements_output),
                    'entities': len(structured.entities),
                    'events': len(structured.events),
                },
                'metadata': {
                    'request_id': str(uuid4()),
                    'pipeline': mode,
                    'no_prose': no_prose,
                    'llm_mode': use_llm,
                    'version': '0.3.0',
                },
            }
            yield f"data: {json.dumps(output)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


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
