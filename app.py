import streamlit as st
import sqlite3
from datetime import datetime
from collections import Counter
import random
import hashlib
import csv
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            nome TEXT,
            data_cadastro TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            banca TEXT NOT NULL,
            materia TEXT NOT NULL,
            ano TEXT,
            questao TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL,
            gabarito TEXT NOT NULL,
            pegadinha TEXT
        )
    """)
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
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM questoes")
    if cursor.fetchone()[0] < 20:
        questoes = [
            ("CESPE", "Portugues", "2026", "Julgue: A expressão 'imprescindíveis' indica que políticas são opcionais.", "certo_errado", "E", "inversão de absoluto"),
            ("CESPE", "Portugues", "2026", "Assinale a substituição que mantém o sentido original.", "multipla", "C", "equivalência semântica"),
            ("CESPE", "Raciocinio Logico", "2026", "Número de linhas da tabela-verdade para condicional.", "multipla", "C", "lógica proposicional"),
            ("FGV", "Portugues", "2020", "“Uma casa com cachorro é um lar feliz”. Deduz-se que todos devem ter cachorro.", "multipla", "E", "extrapolação indevida"),
        ]
        cursor.executemany("INSERT OR IGNORE INTO questoes (banca, materia, ano, questao, tipo, gabarito, pegadinha) VALUES (?, ?, ?, ?, ?, ?, ?)", questoes)
        conn.commit()
    conn.close()

inicializar_banco()

def gerar_salt():
    return os.urandom(16).hex()

def hash_senha(senha, salt):
    return hashlib.sha256((senha + salt).encode()).hexdigest()

def cadastrar_usuario():
    st.subheader("📝 Cadastro")
    username = st.text_input("Usuário")
    nome = st.text_input("Nome")
    senha = st.text_input("Senha (mín. 6 chars)", type="password")
    confirmar = st.text_input("Confirmar", type="password")
    if st.button("Cadastrar"):
        if senha != confirmar or len(senha) < 6 or not username or not nome:
            st.error("Verifique os campos.")
            return
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM usuarios WHERE username = ?", (username,))
            if cursor.fetchone():
                st.error("Usuário existe.")
                return
            salt = gerar_salt()
            senha_hash = hash_senha(senha, salt)
            cursor.execute("INSERT INTO usuarios (username, senha_hash, salt, nome, data_cadastro) VALUES (?, ?, ?, ?, ?)", (username, senha_hash, salt, nome, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            st.success("Cadastrado!")
        except Exception as e:
            st.error(f"Erro: {e}")
        finally:
            conn.close()

def fazer_login():
    st.subheader("🔑 Login")
    username = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, username, nome, senha_hash, salt FROM usuarios WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user and hash_senha(senha, user['salt']) == user['senha_hash']:
                st.session_state.usuario_id = user['id']
                st.session_state.username = user['username']
                st.session_state.nome = user['nome']
                st.success(f"Bem-vindo, {user['nome']}!")
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
        except Exception as e:
            st.error(f"Erro: {e}")
        finally:
            conn.close()

@st.cache
def obter_lista_concursos():
    return [
        {"nome": "INSS (Técnico e Analista)", "status": "Previsto/Autorizado", "banca": "CESPE/CEBRASPE", "vagas": "~8.500", "salario": "até R$ 9.300"},
        {"nome": "IBGE (Temporários Censo)", "status": "Autorizado", "banca": "a definir", "vagas": "39.108", "salario": "variável"},
        {"nome": "Banco do Brasil (Escriturário)", "status": "Previsto", "banca": "CESPE/CEBRASPE", "vagas": "7.200+", "salario": "R$ 5.948+"},
        {"nome": "PRF (Policial Rodoviário Federal)", "status": "Previsto", "banca": "CESPE/CEBRASPE", "vagas": "511", "salario": "R$ 12.253+"},
        {"nome": "AGU (Advocacia-Geral da União)", "status": "Previsto", "banca": "CESPE/CEBRASPE", "vagas": "403+", "salario": "até R$ 21.000"},
        {"nome": "Câmara dos Deputados", "status": "Previsto", "banca": "CESPE ou FGV", "vagas": "várias", "salario": "até R$ 30.000+"},
        {"nome": "EBSERH", "status": "Previsto", "banca": "FGV", "vagas": "várias", "salario": "até R$ 18.000+"},
    ]

def gerar_simulado(banca, materia, usuario_id, concurso):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM questoes WHERE banca = ? AND materia = ? ORDER BY RANDOM() LIMIT 10", (banca, materia))
        questoes = cursor.fetchall()
        if not questoes:
            st.error("Nenhuma questão encontrada.")
            return
        cursor.execute("INSERT INTO simulados (usuario_id, data, concurso, banca, materia) VALUES (?, ?, ?, ?, ?)", (usuario_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), concurso, banca, materia))
        simulado_id = cursor.lastrowid
        respostas = []
        pontuacao = 0
        for q in questoes:
            st.write(f"**Questão:** {q['questao']}")
            if q['tipo'] == "certo_errado":
                resposta = st.radio(f"Resposta {q['id']}", ["C", "E"], key=f"q_{q['id']}")
            else:
                resposta = st.selectbox(f"Resposta {q['id']}", ["A", "B", "C", "D", "E"], key=f"q_{q['id']}")
            correto = 1 if resposta == q['gabarito'] else 0
            pontuacao += correto
            respostas.append((simulado_id, q['id'], resposta, correto))
        if st.button("Finalizar"):
            cursor.executemany("INSERT INTO respostas_simulados (simulado_id, questao_id, resposta_usuario, correto) VALUES (?, ?, ?, ?)", respostas)
            nota = (pontuacao / len(questoes)) * 100
            cursor.execute("UPDATE simulados SET nota = ? WHERE id = ?", (nota, simulado_id))
            conn.commit()
            st.success(f"Nota: {nota:.2f}%")
            st.rerun()
    except Exception as e:
        st.error(f"Erro: {e}")
    finally:
        conn.close()

def analisar_padroes(usuario_id):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT q.questao, q.pegadinha, r.resposta_usuario, q.gabarito
            FROM respostas_simulados r
            JOIN questoes q ON r.questao_id = q.id
            WHERE r.simulado_id IN (SELECT id FROM simulados WHERE usuario_id = ?) AND r.correto = 0
        """, (usuario_id,))
        erros = cursor.fetchall()
        if not erros:
            st.write("Nenhum erro.")
            return
        pegadinhas = Counter()
        for erro in erros:
            if erro['pegadinha']:
                pegadinhas[erro['pegadinha']] += 1
            for kw in PEGADINHAS_KW:
                if kw.lower() in erro['questao'].lower():
                    pegadinhas[kw] += 1
        st.bar_chart(dict(pegadinhas.most_common(5)))
    except Exception as e:
        st.error(f"Erro: {e}")
    finally:
        conn.close()

def listar_historico(usuario_id):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM simulados WHERE usuario_id = ? ORDER BY data DESC", (usuario_id,))
        simulados = cursor.fetchall()
        if not simulados:
            st.write("Nenhum simulado.")
            return
        for sim in simulados:
            st.write(f"Data: {sim['data']} | Concurso: {sim['concurso']} | Nota: {sim['nota']:.2f}%")
            if st.button(f"Deletar {sim['id']}", key=f"del_{sim['id']}"):
                cursor.execute("DELETE FROM simulados WHERE id = ?", (sim['id'],))
                cursor.execute("DELETE FROM respostas_simulados WHERE simulado_id = ?", (sim['id'],))
                conn.commit()
                st.success("Deletado!")
                st.rerun()
        if st.button("Exportar CSV"):
            with open("historico.csv", "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Data", "Concurso", "Banca", "Matéria", "Nota"])
                for sim in simulados:
                    writer.writerow([sim['data'], sim['concurso'], sim['banca'], sim['materia'], sim['nota']])
            st.success("Exportado!")
    except Exception as e:
        st.error(f"Erro: {e}")
    finally:
        conn.close()

def cadastrar_questao():
    st.subheader("➕ Cadastrar Questão")
    banca = st.selectbox("Banca", ["CESPE", "FGV"])
    materia = st.selectbox("Matéria", ["Portugues", "Raciocinio Logico"])
    ano = st.text_input("Ano")
    questao = st.text_area("Questão")
    tipo = st.selectbox("Tipo", ["certo_errado", "multipla"])
    gabarito = st.selectbox("Gabarito", ["A", "B", "C", "D", "E"])
    pegadinha = st.text_input("Pegadinha")
    if st.button("Cadastrar"):
        if not questao:
            st.error("Preencha a questão.")
            return
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO questoes (banca, materia, ano, questao, tipo, gabarito, pegadinha) VALUES (?, ?, ?, ?, ?, ?, ?)", (banca, materia, ano, questao, tipo, gabarito, pegadinha))
            conn.commit()
            st.success("Cadastrada!")
        except sqlite3.IntegrityError:
            st.error("Questão duplicada.")
        except Exception as e:
            st.error(f"Erro: {e}")
        finally:
            conn.close()

def main():
    st.set_page_config(page_title="App Concursos 2026", layout="wide")
    st.title("📚 App Concursos 2026")
    if 'usuario_id' not in st.session_state:
        tab1, tab2 = st.tabs(["Login", "Cadastro"])
        with tab1:
            fazer_login()
        with tab2:
            cadastrar_usuario()
        return
    st.sidebar.success(f"Olá, {st.session_state.nome}!")
    menu = st.sidebar.selectbox("Menu", ["🏠 Início", "📝 Simulado", "📊 Análise", "📋 Histórico", "➕ Cadastrar", "🚪 Sair"])
    if menu == "🚪 Sair":
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
    elif menu == "🏠 Início":
        st.write("Bem-vindo!")
        concursos = obter_lista_concursos()
        st.subheader("Concursos 2026")
        for c in concursos:
            st.write(f"**{c['nome']}** - {c['status']} | {c['banca']} | {c['vagas']} | {c['salario']}")
    elif menu == "📝 Simulado":
        st.header("Gerar Simulado")
        concursos = obter_lista_concursos()
        concurso = st.selectbox("Concurso", [c["nome"] for c in concursos])
        info = next(c for c in concursos if c["nome"] == concurso)
        st.info(f"{info['status']} | {info['banca']}")
        banca = st.selectbox("Banca", ["CESPE", "FGV"])
        materia = st.selectbox("Matéria", ["Portugues", "Raciocinio Logico"])
        if st.button("Gerar"):
            with st.spinner("Gerando..."):
                gerar_simulado(banca, materia, st.session_state.usuario_id, concurso)
    elif menu == "📊 Análise":
        st.header("Análise de Padrões")
        analisar_padroes(st.session_state.usuario_id)
    elif menu == "📋 Histórico":
        st.header("Histórico")
        listar_historico(st.session_state.usuario_id)
    elif menu == "➕ Cadastrar":
        cadastrar_questao()

if __name__ == "__main__":
    main()
