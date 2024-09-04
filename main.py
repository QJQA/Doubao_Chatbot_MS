import os
import logging
from flask import Flask, request, jsonify, render_template, session
from volcenginesdkarkruntime import Ark

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or 'fallback_secret_key'
logging.basicConfig(level=logging.DEBUG)

API_KEY = os.environ['ARK_API_KEY']
BOT_ID = "bot-20240825165102-pdbsl"

print(f"API_KEY: {'Set' if API_KEY else 'Not Set'}")
print(f"BOT_ID: {BOT_ID}")

client = Ark(api_key=API_KEY)

@app.route('/')
def home():
    # 初始化或重置会话
    session['messages'] = [
        {"role": "system", "content": "你是豆包，是由字节跳动开发的 AI 人工智能助手"}
    ]
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data['message']
    frontend_history = data.get('history', [])

    app.logger.debug(f"Received message: {user_message}")
    app.logger.debug(f"Received frontend history length: {len(frontend_history)}")

    # 使用前端发送的历史记录，如果没有则使用服务器端session中的记录
    messages = frontend_history if frontend_history else session.get('messages', [
        {"role": "system", "content": "你是豆包，是由字节跳动开发的 AI 人工智能助手"}
    ])

    # 添加用户的新消息
    messages.append({"role": "user", "content": user_message})

    try:
        app.logger.debug(f"Sending request to Volcengine API with {len(messages)} messages")
        completion = client.bot_chat.completions.create(
            model=BOT_ID,
            messages=messages,
            stream=True
        )

        def generate():
            app.logger.debug("Starting to generate response")
            assistant_message = {"role": "assistant", "content": ""}
            for chunk in completion:
                if chunk.choices:
                    content = chunk.choices[0].delta.content
                    assistant_message["content"] += content
                    app.logger.debug(f"Received chunk: {content}")
                    yield f"data: {content}\n\n"
                if chunk.references:
                    app.logger.debug(f"Received references: {chunk.references}")
                    yield f"data: REFERENCES: {chunk.references}\n\n"
            yield "data: [DONE]\n\n"
            app.logger.debug("Finished generating response")

            # 将助手的回复添加到消息历史
            messages.append(assistant_message)
            # 更新session中的消息历史
            session['messages'] = messages
            app.logger.debug(f"Updated session with {len(messages)} messages")

        return app.response_class(generate(), mimetype='text/event-stream')

    except Exception as e:
        app.logger.error(f"Error in chat: {str(e)}")
        return jsonify({"error": "An error occurred while processing your request."}), 500

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    session['messages'] = [
        {"role": "system", "content": "你是豆包，是由字节跳动开发的 AI 人工智能助手"}
    ]
    return jsonify({"message": "Chat history cleared"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)