from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json, random, uuid, time, threading

# Flask now serves frontend assets too
app = Flask(__name__, static_folder='static', static_url_path='/')
CORS(app)

# TTL (seconds) for in-memory session cache
CACHE_TTL = int(os.getenv('CACHE_TTL_SECONDS', '300'))

# -----------------------------
# In-Memory TTL Cache (No Redis)
# -----------------------------
# Structure: { key: (value, expiry_timestamp) }
_cache = {}
_cache_lock = threading.Lock()

def _set_cache(key, payload, ttl=CACHE_TTL):
    expiry = time.time() + int(ttl)
    with _cache_lock:
        _cache[key] = (payload, expiry)

def _get_cache(key):
    with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        payload, expiry = entry
        if time.time() > expiry:
            # Expired → delete + return None
            del _cache[key]
            return None
        return payload

# --------------------------------
# Load brands data
# --------------------------------
with open('brands.json','r') as f:
    BRANDS = json.load(f)

# --------------------------------
# Recommendation logic
# --------------------------------
def compute_recommendation(answers):
    score = 0
    if answers.get('strap') == 'falling':
        score += 2
    if answers.get('shape') == 'shallow':
        score += 1
    if answers.get('settle') == 'spread':
        score += 1

    if score >= 3:
        return 'Full Coverage'
    elif score == 2:
        return 'Balconette'
    elif score == 1:
        return 'T-Shirt Bra'
    else:
        return 'Regular Bra'

# --------------------------------
# API: Submit Fit Test
# --------------------------------
@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.json or {}

    # Remove PII if present
    data.pop('mobile', None)
    data.pop('phone', None)

    answers = data.get('answers', {})

    recommended = compute_recommendation(answers)

    # Pick one sample per brand
    samples = []
    for b in BRANDS:
        matching = [s for s in b['styles'] if recommended.lower().split()[0] in s['name'].lower()]
        chosen = random.choice(matching if matching else b['styles'])
        samples.append({'brand': b['brand'], 'style': chosen})

    session_id = str(uuid.uuid4())
    payload = {'recommended_category': recommended, 'samples': samples}

    # Store in in-memory TTL cache
    _set_cache(f'fit:{session_id}', json.dumps(payload), CACHE_TTL)

    return jsonify({'session_id': session_id, 'result': payload, 'ttl_seconds': CACHE_TTL})

# --------------------------------
# API: Retrieve result
# --------------------------------
@app.route('/api/result/<session_id>', methods=['GET'])
def get_result(session_id):
    raw = _get_cache(f'fit:{session_id}')
    if not raw:
        return jsonify({'error': 'session not found or expired'}), 404
    return jsonify(json.loads(raw))

# --------------------------------
# Serve SPA frontend
# --------------------------------
@app.route('/')
def index_root():
    return app.send_static_file('index.html')

@app.errorhandler(404)
def not_found(e):
    # SPA routing fallback
    try:
        return app.send_static_file('index.html')
    except Exception:
        return jsonify({'error': 'not found'}), 404

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

# --------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
