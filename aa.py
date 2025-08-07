from flask import Flask, request, jsonify

app = Flask(__name__)

# Endpoint para receber webhooks
@app.route('/webhook/', methods=['POST'])
def webhook():
    if not request.is_json:
        return jsonify({"error": "No JSON data received"}), 400
    
    data = request.json
    print("Webhook recebido:", data)

    try:
        event_type = data.get('event', 'unknown')
        payload = data.get('payload', {})
        print(f"Evento: {event_type}, Payload: {payload}")

        return jsonify({"status": "success", "message": "Webhook recebido com sucesso"}), 200
    except Exception as e:
        print(f"Erro ao processar webhook: {e}")
        return jsonify({"error": "Erro ao processar webhook"}), 500

# Rota de teste
@app.route('/')
def home():
    return jsonify({"message": "Servidor de webhook está ativo!"})

if __name__ == '__main__':  # CORRETO: dois underlines __main_
    app.run(host='0.0.0.0', port=8000, debug=True)