import streamlit as st
import random

st.set_page_config(page_title="App Concursos 2026 - Gilson", layout="wide")
st.title("App de Estudos para Concursos 2026")
st.write("Bem-vindo, Gilson Ferreira (@gilsonzurc)!")

# Questões fixas no código (adicionadas manualmente ou via menu local)
questoes = [
    {"banca": "CESPE", "materia": "Portugues", "questao": "Julgue: A expressão 'imprescindíveis' indica que políticas são opcionais.", "gabarito": "E"},
    {"banca": "CESPE", "materia": "Portugues", "questao": "Assinale a substituição que mantém o sentido original.", "gabarito": "C"},
    {"banca": "CESPE", "materia": "Raciocinio Logico", "questao": "Linhas da tabela-verdade para condicional.", "gabarito": "C"},
    {"banca": "FGV", "materia": "Portugues", "questao": "“Casa com cachorro = lar feliz”. Todos devem ter cachorro.", "gabarito": "E"},
    {"banca": "FGV", "materia": "Raciocinio Logico", "questao": "Sigla CODEBA embaralhada. Qual a 6ª letra?", "gabarito": "D"},
    # Adicione mais questões aqui conforme quiser
]

# Menu simples
menu = st.sidebar.selectbox("Menu", ["Início", "Simulado", "Cadastrar Questão (copie para código)"])

if menu == "Início":
    st.write("Escolha uma opção no menu lateral. O app está leve para deploy na Vercel!")

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

elif menu == "Cadastrar Questão (copie para código)":
    st.subheader("Adicionar Nova Questão (para adicionar no código)")
    banca = st.selectbox("Banca", ["CESPE", "FGV"])
    materia = st.selectbox("Matéria", ["Portugues", "Raciocinio Logico"])
    questao = st.text_area("Enunciado completo")
    gabarito = st.text_input("Gabarito (ex: C, E)")
    if st.button("Gerar código para colar"):
        if questao and gabarito:
            st.code(f'{{"banca": "{banca}", "materia": "{materia}", "questao": "{questao}", "gabarito": "{gabarito}"}},')
            st.info("Copie essa linha e cole na lista 'questoes' no app.py. Depois redeploy!")
        else:
            st.error("Preencha os campos.")