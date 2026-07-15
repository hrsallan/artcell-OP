from flask import Flask, jsonify, request
from http import HTTPStatus
from dotenv import load_dotenv
from pathlib import Path
import os

"""Carrega o arquivo .env e as variáveis necessárias para o funcionamento do sistema."""
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)
REGITSER_SENHA = os.getenv("REGITSER_PASSWORD", "")

app = Flask(__name__)

def criar_resposta(success, message, status_code, data=None, error=None):
    """Monta o payload JSON padrão da API."""
    corpo = {
        "success": success,
        "message": message,
    }

    if data is not None:
        corpo["data"] = data

    if error is not None:
        corpo["error"] = error

    return jsonify(corpo), status_code

def obter_json_requisicao():
    """Retorna o corpo JSON da requisição ou um dicionário vazio."""
    return request.get_json(silent=True) or {}

@app.route("/api/ping", methods=["GET"])
def ping_pong():
    """Endpoint simples para validar se a API está disponível."""
    return criar_resposta(
        success=True,
        message="API em execução.",
        status_code=HTTPStatus.OK,
        data={"status": "pong"},
    )

# Ainda não acabei a função de register
@app.route("/api/register", methods=["POST"])
def registrar_usuario():
    """Registra o usuário! Necessita de uma senha de cadastro."""

    dados = obter_json_requisicao()

    nome = dados.get("nome", "").strip()
    usuario = dados.get("usuario", "").strip()
    senha = dados.get("senha", "")
    email = dados.get("email", "").strip()
    telefone = dados.get("telefone", "").strip()
    senha_cadastro = dados.get("cadastro", "").strip()
    
    if not all([nome,usuario,senha,email,telefone,senha_cadastro]):
        return criar_resposta(
            success=False,
            message="Todos os campos são obrigatórios! Tente novamente.",
            status_code=HTTPStatus.BAD_REQUEST,
            error="validation_error",
        )
    
    if senha_cadastro != REGITSER_SENHA:
        return criar_resposta(
            success=False,
            message="Senha de cadastro incorreta! Tente novamente.",
            status_code=HTTPStatus.UNAUTHORIZED,
            error="unauthorized_error",
        )
    
if __name__ == "__main__":
    app.run(debug=True)