"""
ICHC - Sistema de Lançamento de Auditorias ONA 2026
Ferramenta para auditoras lançarem avaliações in loco e baixarem Excel pronto.
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime, date
from io import BytesIO
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO
# ============================================================
st.set_page_config(
    page_title="ICHC - Auditoria ONA 2026",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paleta institucional ICHC (azul)
COR_PRIMARIA = "#003366"
COR_SECUNDARIA = "#0066CC"

st.markdown(f"""
<style>
    .main-header {{
        background: linear-gradient(90deg, {COR_PRIMARIA} 0%, {COR_SECUNDARIA} 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1.5rem;
    }}
    .main-header h1 {{
        margin: 0;
        font-size: 1.8rem;
    }}
    .main-header p {{
        margin: 0.3rem 0 0 0;
        opacity: 0.9;
    }}
    .req-card {{
        background: #f8f9fa;
        border-left: 4px solid {COR_SECUNDARIA};
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 0.5rem;
    }}
    .progress-info {{
        background: #e8f4fd;
        padding: 0.8rem;
        border-radius: 5px;
        margin: 1rem 0;
    }}
    div[data-testid="stMetricValue"] {{
        font-size: 1.3rem;
    }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# CARREGAMENTO DE DADOS
# ============================================================
BASE_DIR = Path(__file__).parent

@st.cache_data
def carregar_requisitos():
    df = pd.read_csv(BASE_DIR / "requisitos_2026.csv")
    df = df.dropna(subset=["requisito"])
    df["subsecao"] = df["subsecao"].astype(str)
    return df

@st.cache_data
def carregar_nomes_subsecoes():
    with open(BASE_DIR / "nomes_subsecoes.json", "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def carregar_setores():
    with open(BASE_DIR / "setores.json", "r", encoding="utf-8") as f:
        return json.load(f)

requisitos = carregar_requisitos()
nomes_sub = carregar_nomes_subsecoes()
setores_lista = carregar_setores()

def rotulo_subsecao(codigo):
    nome = nomes_sub.get(codigo, "")
    if nome:
        return f"{codigo} - {nome}"
    return codigo

# ============================================================
# STATE
# ============================================================
if "etapa" not in st.session_state:
    st.session_state.etapa = 1
if "dados_auditoria" not in st.session_state:
    st.session_state.dados_auditoria = {}
if "subsecoes_selecionadas" not in st.session_state:
    st.session_state.subsecoes_selecionadas = []
if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}
if "indice_atual" not in st.session_state:
    st.session_state.indice_atual = 0

# ============================================================
# HEADER
# ============================================================
st.markdown(f"""
<div class="main-header">
    <h1>🏥 Auditoria Interna ONA 2026</h1>
    <p>Instituto Central · Hospital das Clínicas FMUSP · SEIG</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR — progresso e navegação
# ============================================================
with st.sidebar:
    st.markdown("### 📋 Etapas")
    etapas_nomes = {
        1: "1. Identificação",
        2: "2. Seleção de subseções",
        3: "3. Avaliação dos requisitos",
        4: "4. Revisão e download",
    }
    for n, nome in etapas_nomes.items():
        if n == st.session_state.etapa:
            st.markdown(f"**▶ {nome}**")
        elif n < st.session_state.etapa:
            st.markdown(f"✅ {nome}")
        else:
            st.markdown(f"⏳ {nome}")

    st.divider()

    if st.session_state.etapa >= 3 and st.session_state.subsecoes_selecionadas:
        total_req = len(requisitos[requisitos["subsecao"].isin(st.session_state.subsecoes_selecionadas)])
        avaliados = sum(1 for v in st.session_state.avaliacoes.values() if v.get("avaliacao"))
        st.metric("Progresso", f"{avaliados} / {total_req}")
        if total_req > 0:
            st.progress(avaliados / total_req)

    st.divider()
    if st.button("🔄 Reiniciar auditoria", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ============================================================
# ETAPA 1 — IDENTIFICAÇÃO
# ============================================================
if st.session_state.etapa == 1:
    st.subheader("📝 Identificação da auditoria")
    st.caption("Preencha os dados básicos antes de iniciar a avaliação.")

    col1, col2 = st.columns(2)
    with col1:
        data_aud = st.date_input("Data da auditoria", value=date.today(), format="DD/MM/YYYY")
        auditor_lider = st.text_input("Auditor(a) líder *", placeholder="Nome completo")
        auditor_aux = st.text_input("Auditor(a) auxiliar", placeholder="Nome completo (opcional)")
    with col2:
        # Setor: dropdown com opção de digitar novo
        modo_setor = st.radio("Setor auditado", ["Selecionar da lista", "Digitar novo"], horizontal=True)
        if modo_setor == "Selecionar da lista":
            setor = st.selectbox("Selecione o setor *", [""] + setores_lista, format_func=lambda x: x if x else "— escolha —")
        else:
            setor = st.text_input("Digite o nome do setor *", placeholder="Ex: UI Cardiologia")

        numero_rel = st.text_input("Nº do relatório", placeholder="Opcional")
        participantes = st.text_area("Participantes da auditoria", placeholder="Liste os profissionais entrevistados/presentes", height=80)

    st.markdown("")
    if st.button("Continuar →", type="primary", use_container_width=True):
        if not auditor_lider or not setor:
            st.error("⚠️ Preencha pelo menos: auditor líder e setor.")
        else:
            st.session_state.dados_auditoria = {
                "data_auditoria": data_aud.strftime("%d/%m/%Y"),
                "auditor_lider": auditor_lider,
                "auditor_auxiliar": auditor_aux,
                "area_auditada": setor,
                "aba_setor": setor,
                "numero_relatorio": numero_rel,
                "participantes": participantes,
                "ciclo": "2026",
            }
            st.session_state.etapa = 2
            st.rerun()

# ============================================================
# ETAPA 2 — SELEÇÃO DE SUBSEÇÕES
# ============================================================
elif st.session_state.etapa == 2:
    st.subheader("📚 Quais subseções serão avaliadas?")
    st.caption("Marque as subseções da norma ONA/OPSS 2026 aplicáveis ao setor. Só os requisitos das subseções marcadas serão exibidos.")

    subsecoes_disponiveis = sorted(requisitos["subsecao"].unique(),
                                    key=lambda x: tuple(int(p) if p.isdigit() else 0 for p in x.split(".")))

    # Agrupar por seção
    agrupado = {"Seção 2 — Atenção ao Paciente": [],
                "Seção 3 — Apoio Diagnóstico e Terapêutico": [],
                "Seção 4 — Apoio Logístico e Infraestrutura": []}
    for s in subsecoes_disponiveis:
        if s.startswith("2."):
            agrupado["Seção 2 — Atenção ao Paciente"].append(s)
        elif s.startswith("3."):
            agrupado["Seção 3 — Apoio Diagnóstico e Terapêutico"].append(s)
        elif s.startswith("4."):
            agrupado["Seção 4 — Apoio Logístico e Infraestrutura"].append(s)

    selecionadas = []
    for secao, lista in agrupado.items():
        if not lista:
            continue
        with st.expander(f"**{secao}** ({len(lista)} subseções)", expanded=True):
            cols = st.columns(2)
            for i, s in enumerate(lista):
                n_req = len(requisitos[requisitos["subsecao"] == s])
                with cols[i % 2]:
                    if st.checkbox(f"{rotulo_subsecao(s)} ({n_req} req.)",
                                   key=f"sub_{s}",
                                   value=s in st.session_state.subsecoes_selecionadas):
                        selecionadas.append(s)

    st.session_state.subsecoes_selecionadas = selecionadas

    if selecionadas:
        total = len(requisitos[requisitos["subsecao"].isin(selecionadas)])
        st.markdown(f"""
        <div class="progress-info">
        ✅ <b>{len(selecionadas)} subseção(ões) selecionada(s)</b> — total de <b>{total} requisitos</b> para avaliar.
        </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Voltar"):
            st.session_state.etapa = 1
            st.rerun()
    with col2:
        if st.button("Iniciar avaliação →", type="primary", use_container_width=True, disabled=not selecionadas):
            st.session_state.etapa = 3
            st.session_state.indice_atual = 0
            st.rerun()

# ============================================================
# ETAPA 3 — AVALIAÇÃO REQUISITO A REQUISITO
# ============================================================
elif st.session_state.etapa == 3:
    # Filtrar requisitos das subseções escolhidas
    req_atuais = requisitos[requisitos["subsecao"].isin(st.session_state.subsecoes_selecionadas)].reset_index(drop=True)
    req_atuais = req_atuais.sort_values(["subsecao", "item"]).reset_index(drop=True)
    total_req = len(req_atuais)

    if total_req == 0:
        st.warning("Nenhum requisito encontrado.")
        st.stop()

    idx = st.session_state.indice_atual
    idx = max(0, min(idx, total_req - 1))
    req = req_atuais.iloc[idx]
    chave = f"{req['subsecao']}__{req['item']}"

    # Cabeçalho com progresso
    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        st.subheader(f"📋 {rotulo_subsecao(req['subsecao'])}")
    with col_b:
        st.metric("Requisito", f"{idx+1} de {total_req}")
    with col_c:
        avaliados = sum(1 for v in st.session_state.avaliacoes.values() if v.get("avaliacao"))
        st.metric("Avaliados", f"{avaliados} de {total_req}")

    st.progress((idx+1) / total_req)

    # Navegação rápida
    with st.expander("🔍 Pular para outro requisito"):
        opcoes_nav = [f"{i+1}. [{r['subsecao']}] item {r['item']} — {str(r['requisito'])[:60]}..."
                      for i, r in req_atuais.iterrows()]
        sel = st.selectbox("Ir para:", opcoes_nav, index=idx)
        novo_idx = opcoes_nav.index(sel)
        if novo_idx != idx:
            st.session_state.indice_atual = novo_idx
            st.rerun()

    st.divider()

    # Card do requisito
    st.markdown(f"""
    <div class="req-card">
        <p style="margin:0;font-size:0.85rem;color:#666;"><b>Item {req['item']}</b></p>
        <p style="margin:0.3rem 0 0 0;font-size:1.05rem;"><b>{req['requisito']}</b></p>
    </div>
    """, unsafe_allow_html=True)

    if pd.notna(req.get("orientacoes")) and str(req["orientacoes"]).strip():
        with st.expander("📖 Orientações"):
            st.write(req["orientacoes"])

    if pd.notna(req.get("sugestao_evidencia")) and str(req["sugestao_evidencia"]).strip():
        with st.expander("📎 Sugestão de evidência"):
            st.write(req["sugestao_evidencia"])

    st.markdown("### Avaliação")

    # Recupera valor anterior se houver
    aval_anterior = st.session_state.avaliacoes.get(chave, {})

    opcoes_aval = {
        "C": "✅ Conforme (C)",
        "PC": "🟡 Parcialmente Conforme (PC)",
        "NC": "❌ Não Conforme (NC)",
        "S": "⭐ Supera (S)",
        "NA": "➖ Não se Aplica (NA)",
    }

    aval_atual = aval_anterior.get("avaliacao", "")
    indice_aval = list(opcoes_aval.keys()).index(aval_atual) if aval_atual in opcoes_aval else None

    nova_aval = st.radio(
        "Status:",
        options=list(opcoes_aval.keys()),
        format_func=lambda k: opcoes_aval[k],
        horizontal=True,
        index=indice_aval,
        key=f"radio_{chave}",
    )

    observacao = st.text_area(
        "Observação / Evidência verificada",
        value=aval_anterior.get("observacao", ""),
        placeholder="Descreva o que foi observado, evidências verificadas, conversa com profissionais...",
        height=90,
        key=f"obs_{chave}",
    )

    plano_acao = ""
    if nova_aval in ("NC", "PC"):
        plano_acao = st.text_area(
            "Plano de ação sugerido (para NC e PC)",
            value=aval_anterior.get("plano_acao", ""),
            placeholder="O que precisa ser feito para corrigir / atingir conformidade?",
            height=80,
            key=f"plano_{chave}",
        )

    # Salvar automático
    if nova_aval:
        st.session_state.avaliacoes[chave] = {
            "subsecao": req["subsecao"],
            "item": req["item"],
            "requisito": req["requisito"],
            "orientacoes": req.get("orientacoes", ""),
            "sugestao_evidencia": req.get("sugestao_evidencia", ""),
            "avaliacao": nova_aval,
            "observacao": observacao,
            "plano_acao": plano_acao,
        }

    st.divider()

    # Navegação
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    with col1:
        if st.button("← Subseções"):
            st.session_state.etapa = 2
            st.rerun()
    with col2:
        if st.button("⬅ Anterior", disabled=idx == 0):
            st.session_state.indice_atual = idx - 1
            st.rerun()
    with col3:
        if st.button("Próximo ➡", disabled=idx == total_req - 1):
            st.session_state.indice_atual = idx + 1
            st.rerun()
    with col4:
        if st.button("Concluir e revisar 🏁", type="primary", use_container_width=True):
            st.session_state.etapa = 4
            st.rerun()

# ============================================================
# ETAPA 4 — REVISÃO E DOWNLOAD
# ============================================================
elif st.session_state.etapa == 4:
    st.subheader("✅ Revisão e download")
    st.caption("Confira o resumo abaixo e baixe o Excel para enviar à SEIG.")

    req_atuais = requisitos[requisitos["subsecao"].isin(st.session_state.subsecoes_selecionadas)]
    total_req = len(req_atuais)
    avaliados = sum(1 for v in st.session_state.avaliacoes.values() if v.get("avaliacao"))
    nao_avaliados = total_req - avaliados

    # Resumo
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total de requisitos", total_req)
    with col2: st.metric("Avaliados", avaliados)
    with col3: st.metric("Pendentes", nao_avaliados)
    with col4:
        if avaliados > 0:
            pct = avaliados / total_req * 100
            st.metric("Conclusão", f"{pct:.1f}%")

    if nao_avaliados > 0:
        st.warning(f"⚠️ {nao_avaliados} requisito(s) ainda não foram avaliados. Você pode baixar mesmo assim — eles ficarão em branco.")

    # Contagem por status
    contagem = {"C": 0, "PC": 0, "NC": 0, "S": 0, "NA": 0}
    for v in st.session_state.avaliacoes.values():
        a = v.get("avaliacao")
        if a in contagem:
            contagem[a] += 1

    st.markdown("### Distribuição")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric("✅ Conforme", contagem["C"])
    with c2: st.metric("🟡 Parc. Conf.", contagem["PC"])
    with c3: st.metric("❌ Não Conf.", contagem["NC"])
    with c4: st.metric("⭐ Supera", contagem["S"])
    with c5: st.metric("➖ N/A", contagem["NA"])

    # Conformidade
    avaliados_validos = contagem["C"] + contagem["PC"] + contagem["NC"] + contagem["S"]
    if avaliados_validos > 0:
        conf_pct = (contagem["C"] + contagem["S"]) / avaliados_validos * 100
        st.markdown(f"""
        <div class="progress-info">
        📊 <b>Taxa de conformidade (C + S) sobre avaliados: {conf_pct:.1f}%</b>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Gerar Excel
    def gerar_excel():
        dados = st.session_state.dados_auditoria
        req_atuais_sort = req_atuais.sort_values(["subsecao", "item"]).reset_index(drop=True)

        linhas = []
        for _, req in req_atuais_sort.iterrows():
            chave = f"{req['subsecao']}__{req['item']}"
            av = st.session_state.avaliacoes.get(chave, {})
            linhas.append({
                "arquivo_origem": "App_Auditoria_ONA_2026",
                "ciclo": "2026",
                "Ano": 2026,
                "aba_setor": dados.get("aba_setor", ""),
                "area_auditada": dados.get("area_auditada", ""),
                "data_auditoria": dados.get("data_auditoria", ""),
                "numero_relatorio": dados.get("numero_relatorio", ""),
                "auditor_lider": dados.get("auditor_lider", ""),
                "auditor_auxiliar": dados.get("auditor_auxiliar", ""),
                "participantes": dados.get("participantes", ""),
                "subsecao": req["subsecao"],
                "item": req["item"],
                "requisito": req["requisito"],
                "Chave_Requisito": f"{req['item']} | {req['requisito']}",
                "orientacoes": req.get("orientacoes", ""),
                "sugestao_evidencia": req.get("sugestao_evidencia", ""),
                "avaliacao": av.get("avaliacao", ""),
                "Status": {
                    "C": "Conforme", "PC": "Parcialmente Conforme",
                    "NC": "Não Conforme", "S": "Supera", "NA": "Não Se Aplica"
                }.get(av.get("avaliacao", ""), "Não Avaliado"),
                "observacao": av.get("observacao", ""),
                "plano_acao": av.get("plano_acao", ""),
            })

        df_resultado = pd.DataFrame(linhas)

        # Cabeçalho institucional
        cabecalho = pd.DataFrame({
            "Campo": ["Instituição", "Setor / Área", "Data", "Auditor líder",
                     "Auditor auxiliar", "Nº relatório", "Participantes",
                     "Ciclo", "Subseções avaliadas", "Total de requisitos", "Requisitos avaliados"],
            "Valor": ["ICHC - HC-FMUSP",
                     dados.get("area_auditada", ""),
                     dados.get("data_auditoria", ""),
                     dados.get("auditor_lider", ""),
                     dados.get("auditor_auxiliar", ""),
                     dados.get("numero_relatorio", ""),
                     dados.get("participantes", ""),
                     "2026",
                     ", ".join(st.session_state.subsecoes_selecionadas),
                     total_req,
                     avaliados],
        })

        resumo_sub = df_resultado.groupby("subsecao").agg(
            total=("avaliacao", "count"),
            conforme=("avaliacao", lambda x: (x == "C").sum()),
            parcial=("avaliacao", lambda x: (x == "PC").sum()),
            nao_conforme=("avaliacao", lambda x: (x == "NC").sum()),
            supera=("avaliacao", lambda x: (x == "S").sum()),
            na=("avaliacao", lambda x: (x == "NA").sum()),
            nao_avaliado=("avaliacao", lambda x: (x == "").sum()),
        ).reset_index()
        resumo_sub["conformidade_pct"] = (
            (resumo_sub["conforme"] + resumo_sub["supera"]) /
            (resumo_sub["total"] - resumo_sub["na"] - resumo_sub["nao_avaliado"]).replace(0, 1) * 100
        ).round(1)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            cabecalho.to_excel(writer, sheet_name="Identificação", index=False)
            df_resultado.to_excel(writer, sheet_name="Avaliação", index=False)
            resumo_sub.to_excel(writer, sheet_name="Resumo_por_subsecao", index=False)
        buffer.seek(0)
        return buffer

    # Nome do arquivo
    dados = st.session_state.dados_auditoria
    setor_safe = dados.get("aba_setor", "Setor").replace(" ", "_").replace("/", "-")[:30]
    data_safe = dados.get("data_auditoria", "").replace("/", "-")
    nome_arquivo = f"Auditoria_ONA_2026_{setor_safe}_{data_safe}.xlsx"

    excel_bytes = gerar_excel()

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Voltar à avaliação"):
            st.session_state.etapa = 3
            st.rerun()
    with col2:
        st.download_button(
            label="📥 Baixar Excel da auditoria",
            data=excel_bytes,
            file_name=nome_arquivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )

    # Tabela com pendentes / problemas
    st.divider()
    if contagem["NC"] > 0 or contagem["PC"] > 0:
        with st.expander(f"📋 Ver não-conformidades e plano de ação ({contagem['NC'] + contagem['PC']} itens)"):
            problemas = []
            for chave, v in st.session_state.avaliacoes.items():
                if v.get("avaliacao") in ("NC", "PC"):
                    problemas.append({
                        "Subseção": v["subsecao"],
                        "Item": v["item"],
                        "Status": v["avaliacao"],
                        "Requisito": v["requisito"][:80] + "...",
                        "Observação": v.get("observacao", "")[:80],
                        "Plano de ação": v.get("plano_acao", "")[:80],
                    })
            st.dataframe(pd.DataFrame(problemas), use_container_width=True, hide_index=True)
