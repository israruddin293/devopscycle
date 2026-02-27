from flask import Flask, render_template, jsonify
import requests
import os

app = Flask(__name__)

BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:5000')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'frontend'}), 200

@app.route('/backend-status')
def backend_status():
    try:
        response = requests.get(f'{BACKEND_URL}/health', timeout=5)
        return jsonify({
            'backend_status': 'healthy' if response.status_code == 200 else 'unhealthy',
            'backend_data': response.json()
        }), 200
    except Exception as e:
        return jsonify({
            'backend_status': 'unreachable',
            'error': str(e)
        }), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
