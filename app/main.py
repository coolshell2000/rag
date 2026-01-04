from flask import Flask, jsonify, render_template
import os

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>欢迎来到TAOTAO应用!</h1>
    <p>这是一个可部署的Flask应用示例。</p>
    <a href="/api/status">查看API状态</a> | 
    <a href="/health">健康检查</a>
    '''

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'success',
        'message': 'Flask API is running!',
        'environment': os.getenv('ENVIRONMENT', 'unknown')
    })

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

