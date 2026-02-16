import streamlit as st
import sqlite3
from datetime import datetime
from collections import Counter
import hashlib
import csv
import io
import os

DB_NAME = "concursos.db"
PEGADINHAS_KW = ["sempre", "nunca", "apenas", "exclusivamente", "obrigatoriamente", "julgue", "infere-se", "conclui-se", "imprescindível", "bem definido", "todo", "nenhum", "de acordo com o texto", "correto afirmar"]

def conectar():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_banco():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS usuarios (...)""")  # (mesma tabela de antes)
    cursor.execute("""CREATE TABLE IF NOT EXISTS questoes (...)""")   # (com coluna concurso)
    cursor.execute("""CREATE TABLE IF NOT EXISTS simulados (...)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS respostas_simulados (...)""")

    # Adiciona coluna concurso se não existir
    cursor.execute("PRAGMA table_info(questoes)")
    if "concurso" not in [row[1] for row in cursor.fetchall()]:
        cursor.execute("ALTER TABLE questoes ADD COLUMN concurso TEXT")

    conn.commit()

    # Questões de exemplo
    cursor.execute("SELECT COUNT(*) FROM questoes")
    if cursor.fetchone()[0] < 20:
        questoes = [
            ("CESPE", "Portugues", "2026", "INSS (Técnico e Analista)", "Julgue: A expressão 'imprescindíveis' indica que políticas são opcionais.", "certo_errado", "E", "inversão de absoluto"),
            ("CESPE", "Portugues", "2026", "Banco do Brasil (Escriturário)", "Assinale a substituição que mantém o sentido original.", "multipla", "C", "equivalência semântica"),
            ("CESPE", "Raciocinio Logico", "2026", "PRF (Policial Rodoviário Federal)", "Número de linhas da tabela-verdade para condicional.", "multipla", "C", "lógica proposicional"),
            ("FGV", "Portugues", "2020", "EBSERH", "“Uma casa com cachorro é um lar feliz”. Deduz-se que todos devem ter cachorro.", "multipla", "E", "extrapolação indevida"),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO questoes (banca, materia, ano, concurso, questao, tipo, gabarito, pegadinha) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            questoes
        )
        conn.commit()
    conn.close()

inicializar_banco()

def gerar_salt():
    return os.urandom(16).hex()

def hash_senha(senha, salt):
    return hashlib.sha256((senha + salt).encode()).hexdigest()

# ====================== LOGIN / CADASTRO ======================
def cadastrar_usuario():
    st.subheader("📝 Cadastro")
    username = st.text_input("Usuário", key="cadastro_username")
    nome = st.text_input("Nome completo", key="cadastro_nome")
    senha = st.text_input("Senha (mín. 6 caracteres)", type="password", key="cadastro_senha")
    confirmar = st.text_input("Confirmar senha", type="password", key="cadastro_confirmar")

    if st.button("Cadastrar", type="primary", key="cadastro_button"):
        if not all([username, nome, senha, confirmar]) or senha != confirmar or len(senha) < 6:
            st.error("Preencha todos os campos corretamente.")
            return
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM usuarios WHERE username = ?", (username,))
            if cursor.fetchone():
                st.error("Usuário já existe.")
                return
            salt = gerar_salt()
            senha_hash = hash_senha(senha, salt)
            cursor.execute(
                "INSERT INTO usuarios (username, senha_hash, salt, nome, data_cadastro) VALUES (?, ?, ?, ?, ?)",
                (username, senha_hash, salt, nome, datetime.now().strftime("%Y-%m-%d"))
            )
            conn.commit()
            st.success("Cadastro realizado! Faça login.")
        finally:
            conn.close()

def fazer_login():
    st.subheader("🔑 Login")
    username = st.text_input("Usuário", key="login_username")
    senha = st.text_input("Senha", type="password", key="login_senha")

    if st.button("Entrar", type="primary", key="login_button"):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, username, nome, senha_hash, salt FROM usuarios WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user and hash_senha(senha, user["salt"]) == user["senha_hash"]:
                st.session_state.usuario_id = user["id"]
                st.session_state.username = user["username"]
                st.session_state.nome = user["nome"]
                st.success(f"Bem-vindo, {user['nome']}!")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
        finally:
            conn.close()

# ====================== RESTO DO CÓDIGO (sem alterações) ======================
# (obter_lista_concursos, gerar_simulado, analisar_padroes, listar_historico, cadastrar_questao)

# ... (copie aqui todas as funções restantes exatamente como estavam na versão anterior)

# ====================== MAIN ======================
def main():
    st.set_page_config(page_title="Simulados Concursos 2026", layout="wide")
    st.title("📚 Simulados Concursos 2026")

    if "usuario_id" not in st.session_state:
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Cadastro"])
        with tab1:
            fazer_login()
        with tab2:
            cadastrar_usuario()
        return

    # (resto do menu exatamente igual à versão anterior)

if __name__ == "__main__":
    main()
