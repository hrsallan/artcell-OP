from flask import Flask, jsonify, request
from http import HTTPStatus
from dotenv import load_dotenv
from pathlib import Path
import os
from core.database import (
    registrar_usuario,
    autenticar_usuario,
    DatabaseOperationError
)

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

@app.route("/api/register", methods=["POST"])
def register_usuario():
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
    
    try:
        resultado = registrar_usuario(
            nome=nome,
            usuario=usuario,
            senha=senha,
            email=email,
            telefone=telefone,
        )

    except DatabaseOperationError:
        return criar_resposta(
            success=False,
            message="Não foi possível concluir o cadastro no momento.",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error="database_error",
        )

    if not resultado["success"]:
        return criar_resposta(
            success=False,
            message=resultado["message"],
            status_code=HTTPStatus.CONFLICT,
            error=resultado["error"],
        )

    return criar_resposta(
        success=True,
        message=resultado["message"],
        status_code=HTTPStatus.CREATED,
        data=resultado["data"],
    )

# Falta a definição de um limite de tentativas + verificação conta ativa + geração do token jwt
@app.route("/api/login", methods=["POST"])
def login():
    dados = obter_json_requisicao()
    usuario = dados.get("usuario", "").strip()
    senha = dados.get("senha", "")

    if not all ([usuario, senha]):
        return criar_resposta(
            success=False,
            message="Todos os campos são obrigatórios! Tente novamente.",
            status_code=HTTPStatus.BAD_REQUEST,
            error="validation_error",
        )
    
    try:
        resultado = autenticar_usuario(usuario=usuario, senha=senha)
    except DatabaseOperationError:
        return criar_resposta(
            success=False,
            message="Não foi possível processar o login no momento.",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error="database_error",
        )

    if not resultado["success"]:
        return criar_resposta(
            success=False,
            message=resultado["message"],
            status_code=HTTPStatus.UNAUTHORIZED,
            error=resultado["error"],
        )
    
    dados_usuario = resultado["data"]

    return criar_resposta(
        success=True,
        message=resultado["message"],
        status_code=HTTPStatus.OK,
        data=dados_usuario,
    )

if __name__ == "__main__":
    app.run(debug=True)