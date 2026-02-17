import streamlit as st
import sqlite3
from datetime import datetime
from collections import Counter
import hashlib
import csv
import io
import os
import pandas as pd
import secrets
import string

DB_NAME = "concursos.db"
PEGADINHAS_KW = ["sempre", "nunca", "apenas", "exclusivamente", "obrigatoriamente", "julgue", "infere-se", "conclui-se", "imprescindível", "bem definido", "todo", "nenhum", "de acordo com o texto", "correto afirmar"]

def conectar():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_banco():
    conn = conectar()
    cursor = conn.cursor()

    # Usuários (com e-mail)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            nome TEXT,
            email TEXT UNIQUE,
            data_cadastro TEXT
        )
    """)

    # Adiciona coluna email se não existir
    cursor.execute("PRAGMA table_info(usuarios)")
    if "email" not in [row[1] for row in cursor.fetchall()]:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN email TEXT UNIQUE")

    # Questões
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            banca TEXT NOT NULL,
            materia TEXT NOT NULL,
            ano TEXT,
            concurso TEXT,
            questao TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL,
            gabarito TEXT NOT NULL,
            pegadinha TEXT
        )
    """)
    cursor.execute("PRAGMA table_info(questoes)")
    if "concurso" not in [row[1] for row in cursor.fetchall()]:
        cursor.execute("ALTER TABLE questoes ADD COLUMN concurso TEXT")

    # Simulados e respostas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            data TEXT NOT NULL,
            concurso TEXT,
            banca TEXT NOT NULL,
            materia TEXT NOT NULL,
            nota REAL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS respostas_simulados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            simulado_id INTEGER,
            questao_id INTEGER,
            resposta_usuario TEXT,
            correto INTEGER,
            FOREIGN KEY (simulado_id) REFERENCES simulados(id),
            FOREIGN KEY (questao_id) REFERENCES questoes(id)
        )
    """)

    # Matérias
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            concurso TEXT
        )
    """)
    materias_iniciais = [
        ("Português", "INSS (Técnico e Analista)"), ("Raciocínio Lógico", "INSS (Técnico e Analista)"),
        ("Direito Constitucional", "PRF"), ("Direito Administrativo", "AGU"),
        ("Informática", "Banco do Brasil"), ("Atualidades", "Todos"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO materias (nome, concurso) VALUES (?, ?)", materias_iniciais)

    # Questões de exemplo
    cursor.execute("SELECT COUNT(*) FROM questoes")
    if cursor.fetchone()[0] < 20:
        questoes = [
            ("CESPE", "Portugues", "2026", "INSS (Técnico e Analista)", "Julgue: A expressão 'imprescindíveis' indica que políticas são opcionais.", "certo_errado", "E", "inversão de absoluto"),
            ("CESPE", "Portugues", "2026", "Banco do Brasil (Escriturário)", "Assinale a substituição que mantém o sentido original.", "multipla", "C", "equivalência semântica"),
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

# ====================== RECUPERAR SENHA ======================
def recuperar_senha():
    st.subheader("🔑 Esqueci minha senha")
    username = st.text_input("Usuário", key="rec_username")
    email = st.text_input("E-mail cadastrado", key="rec_email")

    if st.button("Gerar nova senha temporária", type="primary", key="rec_button"):
        if not username or not email:
            st.error("Preencha usuário e e-mail.")
            return
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE username = ? AND email = ?", (username, email))
        user = cursor.fetchone()
        if not user:
            st.error("Usuário ou e-mail não encontrado.")
            conn.close()
            return

        nova_senha = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        salt = gerar_salt()
        senha_hash = hash_senha(nova_senha, salt)

        cursor.execute("UPDATE usuarios SET senha_hash = ?, salt = ? WHERE id = ?", (senha_hash, salt, user["id"]))
        conn.commit()
        conn.close()

        st.success(f"✅ Nova senha: **{nova_senha}**")
        st.info("Guarde essa senha!")
        st.rerun()

# ====================== CADASTRO ======================
def cadastrar_usuario():
    st.subheader("📝 Cadastro")
    username = st.text_input("Usuário", key="cadastro_username")
    nome = st.text_input("Nome completo", key="cadastro_nome")
    email = st.text_input("E-mail", key="cadastro_email")
    senha = st.text_input("Senha (mín. 6 chars)", type="password", key="cadastro_senha")
    confirmar = st.text_input("Confirmar senha", type="password", key="cadastro_confirmar")

    if st.button("Cadastrar", type="primary", key="cadastro_button"):
        if not all([username, nome, email, senha, confirmar]) or senha != confirmar or len(senha) < 6:
            st.error("Preencha todos os campos corretamente.")
            return
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM usuarios WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                st.error("Usuário ou e-mail já cadastrado.")
                return
            salt = gerar_salt()
            senha_hash = hash_senha(senha, salt)
            cursor.execute(
                "INSERT INTO usuarios (username, senha_hash, salt, nome, email, data_cadastro) VALUES (?, ?, ?, ?, ?, ?)",
                (username, senha_hash, salt, nome, email, datetime.now().strftime("%Y-%m-%d"))
            )
            conn.commit()
            st.success("Cadastro realizado! Faça login.")
        finally:
            conn.close()

# ====================== LOGIN ======================
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
                st.error("Credenciais inválidas.")
        finally:
            conn.close()

# ====================== CONCURSOS E MATÉRIAS ======================
@st.cache_data
def obter_lista_concursos():
    return [ ... ]  # (mesma lista de antes)

def obter_materias(concurso=None):
    conn = conectar()
    cursor = conn.cursor()
    if concurso and concurso != "Geral":
        cursor.execute("SELECT nome FROM materias WHERE concurso = ? OR concurso = 'Todos'", (concurso,))
    else:
        cursor.execute("SELECT nome FROM materias")
    return [row["nome"] for row in cursor.fetchall()]

# ====================== SIMULADO ======================
def gerar_simulado(banca, materia, usuario_id, concurso):
    # (mesma função de antes – sem alteração)
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM questoes 
            WHERE banca = ? AND materia = ? 
              AND (concurso = ? OR concurso IS NULL OR concurso = 'Geral')
            ORDER BY RANDOM() LIMIT 10
        """, (banca, materia, concurso))
        questoes = cursor.fetchall()

        if not questoes:
            st.error("Nenhuma questão encontrada.")
            return

        cursor.execute("INSERT INTO simulados (usuario_id, data, concurso, banca, materia) VALUES (?, ?, ?, ?, ?)",
                       (usuario_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), concurso, banca, materia))
        simulado_id = cursor.lastrowid
        conn.commit()

        st.subheader(f"Simulado – {concurso}")
        respostas = []
        pontuacao = 0

        for idx, q in enumerate(questoes, 1):
            st.markdown(f"**Questão {idx} de 10**")
            st.write(q["questao"])

            if q["tipo"] == "certo_errado":
                resposta = st.radio("C = Certo / E = Errado", ["C", "E"], key=f"q_{q['id']}", horizontal=True)
            else:
                resposta = st.selectbox("Escolha:", ["A", "B", "C", "D", "E"], key=f"q_{q['id']}")

            correto = 1 if resposta == q["gabarito"] else 0
            pontuacao += correto
            respostas.append((simulado_id, q["id"], resposta, correto))

        if st.button("Finalizar Simulado", type="primary", key="finalizar_simulado"):
            cursor.executemany("INSERT INTO respostas_simulados (...) VALUES (?, ?, ?, ?)", respostas)
            nota = (pontuacao / len(questoes)) * 100
            cursor.execute("UPDATE simulados SET nota = ? WHERE id = ?", (nota, simulado_id))
            conn.commit()
            st.success(f"Nota: **{nota:.2f}%**")
            st.balloons()
            st.rerun()
    finally:
        conn.close()

# ====================== ANÁLISE, HISTÓRICO, CADASTRAR ======================
# (as funções analisar_padroes, listar_historico permanecem iguais à versão anterior)

def analisar_padroes(usuario_id):
    # (código idêntico ao anterior)
    pass  # ← cole aqui a função completa da versão anterior

def listar_historico(usuario_id):
    # (código idêntico ao anterior)
    pass

def cadastrar_questao():
    st.subheader("➕ Cadastrar Nova Questão")
    concursos = obter_lista_concursos()
    concurso = st.selectbox("Concurso", [c["nome"] for c in concursos] + ["Geral"], key="questao_concurso")

    banca = st.selectbox("Banca", ["CESPE", "FGV"], key="questao_banca")
    materia = st.selectbox("Matéria", obter_materias(concurso), key="questao_materia")
    ano = st.text_input("Ano", key="questao_ano")
    questao = st.text_area("Questão completa", key="questao_texto")
    tipo = st.selectbox("Tipo", ["certo_errado", "multipla"], key="questao_tipo")

    gab_options = ["C", "E"] if tipo == "certo_errado" else ["A", "B", "C", "D", "E"]
    gabarito = st.selectbox("Gabarito", gab_options, key="questao_gabarito")
    pegadinha = st.text_input("Pegadinha (opcional)", key="questao_pegadinha")

    # IMPORT CSV
    uploaded = st.file_uploader("Importar CSV de questões", type=["csv"], key="import_csv")
    if uploaded and st.button("Importar CSV agora"):
        df = pd.read_csv(uploaded)
        conn = conectar()
        df.to_sql("questoes", conn, if_exists="append", index=False)
        st.success(f"{len(df)} questões importadas!")
        conn.close()

    if st.button("Cadastrar Questão", type="primary", key="cadastrar_questao_button"):
        if not questao:
            st.error("Preencha a questão.")
            return
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO questoes (banca, materia, ano, concurso, questao, tipo, gabarito, pegadinha) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (banca, materia, ano, concurso, questao, tipo, gabarito, pegadinha)
            )
            conn.commit()
            st.success("Questão cadastrada!")
        except sqlite3.IntegrityError:
            st.error("Questão duplicada.")
        finally:
            conn.close()

# ====================== MAIN ======================
def main():
    st.set_page_config(page_title="Simulados Concursos 2026", layout="wide")
    st.title("📚 Simulados Concursos 2026")

    if "usuario_id" not in st.session_state:
        tab1, tab2, tab3 = st.tabs(["🔑 Login Tradicional", "📝 Cadastro", "🌐 Login Social"])
        with tab1:
            fazer_login()
            with st.expander("Esqueci minha senha"):
                recuperar_senha()
        with tab2:
            cadastrar_usuario()
        with tab3:
            st.subheader("Login com Google")
            if st.button("Continuar com Google", type="primary", use_container_width=True, key="google_btn"):
                st.login("google")   # ← configure secrets.toml
            st.info("Facebook/Instagram → posso adicionar com Firebase depois.")

        return

    st.sidebar.success(f"Olá, {st.session_state.nome}!")

    menu = st.sidebar.selectbox("Menu", ["🏠 Início", "📝 Gerar Simulado", "📊 Análise", "📋 Histórico", "➕ Cadastrar", "🚪 Sair"])

    if menu == "🚪 Sair":
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    elif menu == "🏠 Início":
        st.write("Bem-vindo!")
        concursos = obter_lista_concursos()
        for c in concursos:
            st.write(f"**{c['nome']}** – {c['status']} | {c['banca']}")

        st.subheader("📱 Versão Mobile (Android + iOS)")
        st.info("Este app é PWA!\n\n"
                "Abra no celular → Menu do navegador → 'Adicionar à tela inicial'\n\n"
                "Android → vira app nativo\n"
                "iOS → funciona como app\n\n"
                "Quer APK .apk? Acesse https://pwabuilder.com e cole a URL do seu app.")

    elif menu == "📝 Gerar Simulado":
        st.header("Gerar Simulado")
        concursos = obter_lista_concursos()
        concurso_nome = st.selectbox("Concurso", [c["nome"] for c in concursos], key="simulado_concurso")
        info = next(c for c in concursos if c["nome"] == concurso_nome)
        st.info(f"Status: {info['status']} | Banca: {info['banca']}")

        banca_options = ["CESPE"] if "CESPE" in info["banca"] else ["FGV"]
        banca = st.selectbox("Banca", banca_options, key="simulado_banca")
        materia = st.selectbox("Matéria", obter_materias(concurso_nome), key="simulado_materia")

        if st.button("Gerar Simulado", type="primary", key="gerar_button"):
            with st.spinner("Gerando..."):
                gerar_simulado(banca, materia, st.session_state.usuario_id, concurso_nome)

    elif menu == "📊 Análise":
        analisar_padroes(st.session_state.usuario_id)
    elif menu == "📋 Histórico":
        listar_historico(st.session_state.usuario_id)
    elif menu == "➕ Cadastrar":
        cadastrar_questao()

if __name__ == "__main__":
    main()
