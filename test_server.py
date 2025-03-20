from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return """
    <html>
    <head><title>测试服务器</title></head>
    <body>
        <h1>测试服务器正常工作!</h1>
        <p>如果您能看到此页面，说明本地服务器可以正常访问。</p>
    </body>
    </html>
    """

if __name__ == '__main__':
    # 同时在所有接口(0.0.0.0)和localhost上监听
    app.run(host='0.0.0.0', port=5000, debug=True) 