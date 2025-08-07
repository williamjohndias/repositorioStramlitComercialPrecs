from flask import Flask, request, jsonify
import psycopg2
import json
from datetime import datetime

app = Flask(__name__)

# Supabase database connection
def get_connection():
    return psycopg2.connect(
        host="precsinstance.c8p0mgum6ow9.us-east-1.rds.amazonaws.com",  # Substitua com seu host
        port=5432,
        database="dashmetas",
        user="postgres",  # Ou outro usuário que você configurou
        password="precs2025",
        sslmode= "require"
    )
     
@app.route('/webhook/', methods=['POST'])
def webhook():
    if not request.is_json:
        return jsonify({"error": "No JSON data received"}), 400

    data = request.json
    print("Webhook recebido:", data)

    try:
        # Acessa diretamente os campos
        id_negocio = data.get('id_negocio')
        proprietario = data.get('proprietario')
        data_evento = data.get('data')
        id_etapa = data.get('id_etapa')

        if not all([id_negocio, proprietario, data_evento, id_etapa]):
            return jsonify({"error": "Campos obrigatórios ausentes"}), 400

        # Converte data (se necessário)
        if isinstance(data_evento, str):
            # data_evento = data_evento.split(" ")[0]  # remove erros como "17:27 2025-06-23"
            data_evento = datetime.fromisoformat(data_evento)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO dashmetas (id_negocio, proprietario, data, id_etapa)
            VALUES (%s, %s, %s, %s)
        """, (id_negocio, proprietario, data_evento, id_etapa))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"status": "success", "message": "Dados inseridos com sucesso"}), 200

    except Exception as e:
        print(f"Erro ao processar webhook: {e}")
        return jsonify({"error": str(e)}),500


@app.route('/')
def home():
    return jsonify({"message": "Servidor de webhook ativo"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)  