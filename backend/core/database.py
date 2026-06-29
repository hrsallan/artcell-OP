import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import hmac
from pathlib import Path
import secrets
import hashlib

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH)

"""Aqui vão informações importantíssimas enquanto a conexão ao banco de dados."""
DATABASE_HOST = os.getenv("DB_HOST", "localhost")
DATABASE_PORT = os.getenv("DB_PORT", "3306")
DATABASE_USER = os.getenv("DB_USER", "root")
DATABASE_PASSWORD = os.getenv("DB_PASSWORD", "")
DATABASE_NAME = os.getenv("DB_NAME", "artcell-db")
PASSWORD_HASH_ITERATIONS = int(os.getenv("PASSWORD_HASH_ITERATIONS", "100000"))

class DatabaseOperationError(RuntimeError):
    """Erro de infraestrutura para operações de banco de dados."""

def obter_conexao(database=None):
    """Abre a conexão com o MySQL, opcionalmente já apontando para um banco"""
    parametros = {
        "host": DATABASE_HOST,
        "port": DATABASE_PORT,
        "user": DATABASE_USER,
        "password": DATABASE_PASSWORD,
    }
    if database is not None:
        parametros["database"] = database 
    try:
        return mysql.connector.connect(**parametros)
    except Error as error:
        raise DatabaseOperationError("Falha ao abrir conexão com o MySQL.") from error

def fechar_recursos(conexao=None, cursor=None):
    """Fecha cursor e conexão, se estiverem abertos."""

    if cursor is not None:
        cursor.close()

    if conexao is not None and conexao.is_connected():
        conexao.close()

def normalizar_usuario(linha_usuario):
    """Transforma a tupla retornada pelo MySQL em dicionário."""

    if linha_usuario is None:
        return None

    return {
        "id": linha_usuario[0],
        "nome": linha_usuario[1],
        "usuario": linha_usuario[2],
        "senha": linha_usuario[3],
        "email": linha_usuario[4],
        "telefone": linha_usuario[5],
    }

def gerar_hash_senha(senha):
    """Gera um hash de senha no formato `iteracoes$salt$hash`."""

    salt = secrets.token_hex(16)
    senha_hash = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"{PASSWORD_HASH_ITERATIONS}${salt}${senha_hash}"

def verificar_hash_senha(senha, senha_hash_armazenada):
    """Compara a senha informada com o hash persistido no banco."""

    try:
        iteracoes_str, salt, senha_hash_salva = senha_hash_armazenada.split("$", 2)
        iteracoes = int(iteracoes_str)
    except (AttributeError, ValueError):
        return False

    senha_hash_calculada = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt.encode("utf-8"),
        iteracoes,
    ).hex()
    return hmac.compare_digest(senha_hash_calculada, senha_hash_salva)

    
def iniciar_db():
    """Cria o banco e a tabela principal caso ainda não existam."""
    conexao = None
    cursor = None

    try:
        conexao = obter_conexao()
        cursor = conexao.cursor()

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DATABASE_NAME}`")
        cursor.execute(f"USE `{DATABASE_NAME}`")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            usuario VARCHAR(100) NOT NULL UNIQUE,
            senha VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            telefone VARCHAR(20) NOT NULL UNIQUE
            ) ENGINE=InnoDB
        """
        )
        
    except Exception as error:
        if conexao is not None and conexao.is_connected():
            conexao.rollback()
        raise DatabaseOperationError("Falha ao incializar a estrutura do banco.") from error
    finally:
        fechar_recursos(conexao=conexao, cursor=cursor)

def consultar_usuario_por_username(usuario):
    """Busca as informações do usuário a partir do nome de acesso."""
    conexao = None
    cursor = None

    try:
        conexao = obter_conexao(DATABASE_NAME)
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT id, nome, usuario, senha, email, telefone
            FROM usuarios
            WHERE usuario = %s
            LIMIT 1
            """,
            (usuario,),
        )
        resultado = cursor.fetchone()
        return normalizar_usuario(resultado)
    except Error as error:
        raise DatabaseOperationError("Falha ao consultar usuário por nome de acesso.") from error
    finally:
        fechar_recursos(conexao=conexao, cursor=cursor)

def consultar_usuario_por_email(email):
    """Busca um usuário a partir do email."""

    conexao = None
    cursor = None

    try:
        conexao = obter_conexao(DATABASE_NAME)
        cursor = conexao.cursor()
        cursor.execute(
            """
            SELECT id, nome, usuario, senha, email, telefone
            FROM usuarios
            WHERE email = %s
            LIMIT 1
            """,
            (email,),
        )
        return normalizar_usuario(cursor.fetchone())
    except Error as error:
        raise DatabaseOperationError("Falha ao consultar usuário por e-mail.") from error
    finally:
        fechar_recursos(conexao=conexao, cursor=cursor)

def registrar_usuario(nome, usuario, senha, email, telefone):
    """Função relativa ao cadastro de novos usuários na plataforma."""
    dados_usuario = consultar_usuario_por_username(usuario)

    if dados_usuario is not None:
        return {
            "success": False,
            "message": "O nome de usuário informado já está em uso.",
            "error": "username_already_exists",
        }

    email_existente = consultar_usuario_por_email(email)
    if email_existente is not None:
        return {
            "success": False,
            "message": "O e-mail informado já está em uso.",
            "error": "email_already_exists",
        }
    
    conexao = None
    cursor = None

    try:
        conexao = obter_conexao(DATABASE_NAME)
        cursor = conexao.cursor()
        senha_hash = gerar_hash_senha(senha)

        cursor.execute(
            """
            INSERT INTO usuarios (nome, usuario, senha, email, telefone)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (nome, usuario, senha_hash, email, telefone),
        )
        conexao.commit()

        return {
            "success": True,
            "message": "Usuário registrado com sucesso.",
            "data": {
                "usuario_id": cursor.lastrowid,
                "usuario": usuario,
                "email": email,
            },
        }
    except Error as error:
        if conexao is not None and conexao.is_connected():
            conexao.rollback()
        raise DatabaseOperationError("Falha ao registrar o usuário.") from error
    finally:
        fechar_recursos(conexao=conexao, cursor=cursor)