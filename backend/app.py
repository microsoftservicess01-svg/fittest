
from flask import Flask, request, jsonify
from flask_cors import CORS
import redis, os, json, random, uuid

app = Flask(__name__)
CORS(app)

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
CACHE_TTL = int(os.getenv('CACHE_TTL_SECONDS', '300'))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

with open('brands.json','r') as f:
    BRANDS = json.load(f)

def compute_recommendation(answers):
    score = 0
    if answers.get('strap') == 'falling':
        score += 2
    if answers.get('shape') == 'shallow':
        score += 1
    if answers.get('settle') == 'spread':
        score += 1
    if score >= 3:
        category = 'Full Coverage'
    elif score == 2:
        category = 'Balconette'
    elif score == 1:
        category = 'T-Shirt Bra'
    else:
        category = 'Regular Bra'
    return category

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.json or {}
    # remove PII
    data.pop('mobile', None); data.pop('phone', None)
    answers = data.get('answers', {})
    recommended_category = compute_recommendation(answers)
    samples = []
    for b in BRANDS:
        matching = [s for s in b.get('styles', []) if recommended_category.lower().split()[0] in s.get('name','').lower()]
        if not matching:
            chosen = random.choice(b.get('styles', []))
        else:
            chosen = random.choice(matching)
        samples.append({'brand': b['brand'], 'style': chosen})
    session_id = str(uuid.uuid4())
    payload = {'recommended_category': recommended_category, 'samples': samples}
    r.setex(f'fit:{session_id}', CACHE_TTL, json.dumps(payload))
    return jsonify({'session_id': session_id, 'result': payload, 'ttl_seconds': CACHE_TTL})

@app.route('/api/result/<session_id>', methods=['GET'])
def get_result(session_id):
    key = f'fit:{session_id}'
    raw = r.get(key)
    if not raw:
        return jsonify({'error': 'session not found or expired'}), 404
    return jsonify(json.loads(raw))

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status':'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
