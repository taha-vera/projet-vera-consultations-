"""Phase 2 W2 — VERA Public API"""
from flask import Flask, jsonify, request
import json
import os
from datetime import datetime

app = Flask(__name__)

def load_profiles():
    path = 'vera-sib/results/phase2_statistical_profiles.json'
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {'genres': {}}

profiles_data = load_profiles()

@app.route('/api/v1/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'VERA Phase 2 API',
        'version': 'w2-launch'
    }), 200

@app.route('/api/v1/genres', methods=['GET'])
def get_genres():
    genres_list = []
    for genre, data in profiles_data.get('genres', {}).items():
        genres_list.append({
            'name': genre,
            'tracks': data.get('track_count', 0),
            'tempo': data.get('tempo', {}).get('mean', 0)
        })
    return jsonify({'genres': genres_list}), 200

@app.route('/api/v1/stats', methods=['GET'])
def get_stats():
    return jsonify({
        'total_genres': len(profiles_data.get('genres', {})),
        'privacy': 'ε-DP (ε=0.5)',
        'destruction': 'DoD 5220.22-M'
    }), 200

if __name__ == '__main__':
    print("\n✅ VERA Phase 2 W2 API Running")
    app.run(debug=False, host='127.0.0.1', port=5000)
