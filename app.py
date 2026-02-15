import streamlit as st
import random
from datetime import datetime

st.set_page_config(page_title="App Concursos 2026 - Gilson", layout="wide")
st.title("App de Estudos para Concursos 2026")
st.write("Bem-vindo, Gilson Ferreira (@gilsonzurc)!")

# Questões fixas no código (para evitar arquivo .db pesado)
questoes = [
    {"banca": "CESPE", "materia": "Portugues", "questao": "Julgue: 'imprescindíveis' indica opcionalidade.", "gabarito": "E"},
    {"banca": "CESPE", "materia": "Portugues", "questao": "Substituição que mantém sentido.", "gabarito": "C"},
    {"banca": "FGV", "materia": "Portugues", "questao": "“Casa com cachorro = lar feliz”. Todos devem ter?", "gabarito": "E"},
    {"banca": "CESPE", "materia": "Raciocinio Logico", "questao": "Linhas da tabela-verdade para condicional.", "gabarito": "C"},
    # Adicione mais questões aqui conforme quiser
]

menu = st.sidebar.selectbox("Menu", ["Início", "Simulado", "Cadastrar Questão"])

if menu == "Início":
    st.write("Escolha uma opção no menu lateral para começar!")

elif menu == "Simulado":
    st.subheader("Simulado Rápido")
    banca = st.selectbox("Banca", ["CESPE", "FGV"])
    materia = st.selectbox("Matéria", ["Portugues", "Raciocinio Logico"])

    if st.button("Gerar Simulado"):
        qs_filtradas = [q for q in questoes if q["banca"] == banca and q["materia"] == materia]
        if not qs_filtradas:
            st.warning("Sem questões para essa combinação ainda.")
        else:
            selecionadas = random.sample(qs_filtradas, min(5, len(qs_filtradas)))
            for i, q in enumerate(selecionadas, 1):
                st.write(f"**Q{i}:** {q['questao']}")
                resp = st.radio("Resposta", ["A", "B", "C", "D", "E"], key=f"q{i}")
                if st.button(f"Confirmar Q{i}", key=f"btn{i}"):
                    if resp == q['gabarito']:
                        st.success("Correto!")
                    else:
                        st.error(f"Errado! Gabarito: {q['gabarito']}")

elif menu == "Cadastrar Questão":
    st.subheader("Adicionar Nova Questão (será salva no código depois)")
    banca = st.selectbox("Banca", ["CESPE", "FGV"])
    materia = st.selectbox("Matéria", ["Portugues", "Raciocinio Logico"])
    questao = st.text_area("Enunciado completo")
    gabarito = st.text_input("Gabarito (ex: C, E)")
    if st.button("Salvar (copie para o código)"):
        if questao and gabarito:
            st.success("Questão pronta! Copie e cole no código app.py na lista 'questoes'.")
            st.code(f'{{"banca": "{banca}", "materia": "{materia}", "questao": "{questao}", "gabarito": "{gabarito}"}},')
        else:
            st.error("Preencha todos os campos.")
