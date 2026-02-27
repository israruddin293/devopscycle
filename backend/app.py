from flask import Flask, jsonify
import redis
import os
import json

app = Flask(__name__)

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')

# Initialize Redis connection
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
    socket_connect_timeout=5
)

@app.route('/health')
def health():
    try:
        redis_client.ping()
        redis_status = 'connected'
    except Exception as e:
        redis_status = f'disconnected: {str(e)}'
    
    return jsonify({
        'status': 'healthy',
        'service': 'backend',
        'redis': redis_status
    }), 200

@app.route('/api/data', methods=['GET'])
def get_data():
    try:
        # Try to get data from Redis
        data = redis_client.get('sample_data')
        
        if data is None:
            # Initialize sample data
            sample_data = {
                'message': 'Hello from Backend API',
                'version': '1.0.0',
                'environment': os.getenv('ENVIRONMENT', 'production')
            }
            redis_client.set('sample_data', json.dumps(sample_data))
            data = json.dumps(sample_data)
        
        return jsonify({
            'success': True,
            'data': json.loads(data),
            'source': 'redis'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data/update', methods=['POST'])
def update_data():
    try:
        new_data = {
            'message': 'Updated data',
            'timestamp': str(os.times())
        }
        redis_client.set('sample_data', json.dumps(new_data))
        return jsonify({
            'success': True,
            'message': 'Data updated successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
