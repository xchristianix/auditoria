"""
ICHC - Sistema de Lançamento de Auditorias ONA 2026
Ferramenta para auditoras lançarem avaliações in loco e baixarem Excel pronto.
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import base64
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

COR_PRIMARIA = "#003366"
COR_SECUNDARIA = "#0066CC"
COR_CORE = "#D32F2F"

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
    .req-card-core {{
        background: #fff5f5;
        border-left: 4px solid {COR_CORE};
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 0.5rem;
    }}
    .badge-core {{
        background: {COR_CORE};
        color: white;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-right: 8px;
    }}
    .badge-n2 {{
        background: #1976D2;
        color: white;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-right: 8px;
    }}
    .badge-n3 {{
        background: #7B1FA2;
        color: white;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-right: 8px;
    }}
    .progress-info {{
        background: #e8f4fd;
        padding: 0.8rem;
        border-radius: 5px;
        margin: 1rem 0;
    }}
    .save-info {{
        background: #f0f9f0;
        padding: 0.6rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        font-size: 0.85rem;
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
    df["nivel"] = df["nivel"].fillna(1).astype(int)
    return df

@st.cache_data
def carregar_nomes_subsecoes():
    with open(BASE_DIR / "nomes_subsecoes.json", "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def carregar_setores():
    with open(BASE_DIR / "setores.json", "r", encoding="utf-8") as f:
        raw = json.load(f)
    # Compatibilidade: aceita lista de strings (formato antigo) ou de dicts (formato novo)
    normalizado = []
    for item in raw:
        if isinstance(item, dict):
            normalizado.append(item)
        else:
            # string solta → vira dict com agrupador "Outros"
            normalizado.append({
                "nome": str(item),
                "tipo": "",
                "agrupador": "OUTROS",
                "grupo_operacional": "",
            })
    return normalizado

requisitos = carregar_requisitos()
nomes_sub = carregar_nomes_subsecoes()
setores_lista = carregar_setores()

setores_por_agrupador = {}
for s in setores_lista:
    ag = s.get("agrupador", "Outros") if isinstance(s, dict) else "Outros"
    setores_por_agrupador.setdefault(ag, []).append(s)
agrupadores_disponiveis = sorted(setores_por_agrupador.keys())

def rotulo_subsecao(codigo):
    nome = nomes_sub.get(codigo, "")
    if nome:
        return f"{codigo} - {nome}"
    return codigo

def rotulo_nivel(n):
    if n == 1:
        return '<span class="badge-core">🔴 CORE (N1)</span>'
    elif n == 2:
        return '<span class="badge-n2">N2</span>'
    elif n == 3:
        return '<span class="badge-n3">N3</span>'
    return ""

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
if "ultima_alteracao" not in st.session_state:
    st.session_state.ultima_alteracao = None

# ============================================================
# FUNÇÕES DE SALVAR/CARREGAR PROGRESSO
# ============================================================
def gerar_backup_json():
    """Serializa todo o estado atual para JSON"""
    backup = {
        "versao": "1.0",
        "timestamp": datetime.now().isoformat(),
        "etapa": st.session_state.etapa,
        "dados_auditoria": st.session_state.dados_auditoria,
        "subsecoes_selecionadas": st.session_state.subsecoes_selecionadas,
        "avaliacoes": st.session_state.avaliacoes,
        "indice_atual": st.session_state.indice_atual,
    }
    return json.dumps(backup, ensure_ascii=False, indent=2).encode("utf-8")

def carregar_backup_json(arquivo):
    """Restaura estado a partir de JSON"""
    try:
        backup = json.load(arquivo)
        st.session_state.etapa = backup.get("etapa", 1)
        st.session_state.dados_auditoria = backup.get("dados_auditoria", {})
        st.session_state.subsecoes_selecionadas = backup.get("subsecoes_selecionadas", [])
        st.session_state.avaliacoes = backup.get("avaliacoes", {})
        st.session_state.indice_atual = backup.get("indice_atual", 0)
        st.session_state.ultima_alteracao = datetime.now()
        return True, backup.get("timestamp", "?")
    except Exception as e:
        return False, str(e)

def marcar_alteracao():
    st.session_state.ultima_alteracao = datetime.now()

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
# SIDEBAR
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

    # Progresso de avaliação
    if st.session_state.etapa >= 3 and st.session_state.subsecoes_selecionadas:
        total_req = len(requisitos[requisitos["subsecao"].isin(st.session_state.subsecoes_selecionadas)])
        avaliados = sum(1 for v in st.session_state.avaliacoes.values() if v.get("avaliacao"))
        st.metric("Progresso", f"{avaliados} / {total_req}")
        if total_req > 0:
            st.progress(avaliados / total_req)

    st.divider()

    # 💾 Salvar progresso (sempre disponível)
    st.markdown("### 💾 Salvamento")
    st.caption("Auto-save ativo no navegador a cada alteração. Útil se a internet cair ou a aba fechar.")

    if st.session_state.ultima_alteracao:
        hora = st.session_state.ultima_alteracao.strftime("%H:%M:%S")
        st.markdown(f"<div class='save-info'>🕒 Última alteração: {hora}</div>", unsafe_allow_html=True)

    setor_nome = st.session_state.dados_auditoria.get("aba_setor", "auditoria")
    setor_safe = setor_nome.replace(" ", "_").replace("/", "-")[:30]
    nome_backup = f"backup_ONA_{setor_safe}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

    backup_bytes = gerar_backup_json()

    st.download_button(
        "📥 Baixar backup agora (.json)",
        data=backup_bytes,
        file_name=nome_backup,
        mime="application/json",
        use_container_width=True,
        help="Salve este arquivo no computador. Pode retomar carregando ele depois.",
    )

    # 🔄 AUTO-SAVE INVISÍVEL EM LOCALSTORAGE
    # A cada rerun, escreve o estado no localStorage do navegador.
    backup_b64 = base64.b64encode(backup_bytes).decode("ascii")
    components.html(f"""
    <script>
      try {{
        const data = atob("{backup_b64}");
        localStorage.setItem("ona_auditoria_autosave", data);
        localStorage.setItem("ona_auditoria_autosave_ts", new Date().toISOString());
      }} catch(e) {{ console.error('autosave erro', e); }}
    </script>
    """, height=0)

    # 📥 Botão para recuperar o auto-save (caso usuária perca a sessão)
    components.html("""
    <div style="margin-top:8px;">
      <button onclick="
        const data = localStorage.getItem('ona_auditoria_autosave');
        const ts = localStorage.getItem('ona_auditoria_autosave_ts');
        if (!data) { alert('Nenhum auto-save encontrado neste navegador.'); return; }
        const blob = new Blob([data], {type:'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const tsClean = (ts || new Date().toISOString()).slice(0,16).replace(/[:T]/g,'-');
        a.download = 'autosave_ONA_' + tsClean + '.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      " style="
        width:100%;
        padding:8px 12px;
        background:#0066CC;
        color:white;
        border:none;
        border-radius:6px;
        cursor:pointer;
        font-size:14px;
        font-family:inherit;
      ">🔄 Recuperar auto-save do navegador</button>
      <div style="margin-top:4px;font-size:11px;color:#666;line-height:1.3;">
        Se você perdeu a sessão, clique aqui para baixar o último estado salvo automaticamente, depois carregue abaixo.
      </div>
    </div>
    """, height=90)

    # 📤 Carregar backup
    with st.expander("📤 Carregar backup existente"):
        arq_backup = st.file_uploader("Selecione um arquivo .json", type=["json"], key="upload_backup")
        if arq_backup is not None:
            if st.button("Restaurar este backup", type="primary", use_container_width=True):
                ok, info = carregar_backup_json(arq_backup)
                if ok:
                    st.success(f"✅ Backup de {info} restaurado!")
                    st.rerun()
                else:
                    st.error(f"❌ Erro ao carregar: {info}")

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

    # Opção de retomar backup
    with st.expander("📂 Retomar auditoria salva (.json)"):
        st.caption("Se você tem um arquivo de backup, carregue aqui para continuar de onde parou.")
        uploaded = st.file_uploader("Selecione o arquivo .json", type=["json"], key="upload_backup_etapa1")
        if uploaded is not None:
            ok, info = carregar_backup_json(uploaded)
            if ok:
                st.success(f"✅ Auditoria restaurada (backup de {info[:19] if len(info) > 19 else info})")
                st.info("Redirecionando para o ponto onde parou...")
                st.rerun()
            else:
                st.error(f"Erro ao carregar: {info}")

    col1, col2 = st.columns(2)
    with col1:
        data_aud = st.date_input("Data da auditoria", value=date.today(), format="DD/MM/YYYY")
        auditor_lider = st.text_input("Auditor(a) líder *", value=st.session_state.dados_auditoria.get("auditor_lider", ""), placeholder="Nome completo")
        auditor_aux = st.text_input("Auditor(a) auxiliar", value=st.session_state.dados_auditoria.get("auditor_auxiliar", ""), placeholder="Nome completo (opcional)")
    with col2:
        modo_setor = st.radio("Setor auditado", ["Selecionar da lista", "Digitar novo"], horizontal=True)

        setor = st.session_state.dados_auditoria.get("aba_setor", "")
        if modo_setor == "Selecionar da lista":
            agrupador = st.selectbox(
                "1. Tipo / Agrupador *",
                [""] + agrupadores_disponiveis,
                format_func=lambda x: x if x else "— escolha uma categoria —",
            )
            if agrupador:
                opcoes_setor = setores_por_agrupador.get(agrupador, [])
                opcoes_setor = sorted(opcoes_setor, key=lambda s: (s["tipo"] != "Centro de Receita", s["nome"]))
                rotulos = [f'{s["nome"]} ({s["tipo"]})' for s in opcoes_setor]
                idx_sel = st.selectbox(
                    f"2. Setor específico * ({len(opcoes_setor)} disponíveis)",
                    range(len(rotulos)),
                    format_func=lambda i: rotulos[i] if i is not None else "—",
                    index=None,
                    placeholder="— escolha o setor —",
                )
                if idx_sel is not None:
                    setor = opcoes_setor[idx_sel]["nome"]
        else:
            setor = st.text_input("Digite o nome do setor *", value=setor, placeholder="Ex: UTI da MI, UI Cardiologia")

        numero_rel = st.text_input("Nº do relatório", value=st.session_state.dados_auditoria.get("numero_relatorio", ""), placeholder="Opcional")
        participantes = st.text_area("Participantes da auditoria", value=st.session_state.dados_auditoria.get("participantes", ""), placeholder="Liste os profissionais entrevistados/presentes", height=80)

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
            marcar_alteracao()
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
                req_sub = requisitos[requisitos["subsecao"] == s]
                n_total = len(req_sub)
                n_core = (req_sub["nivel"] == 1).sum()
                with cols[i % 2]:
                    if st.checkbox(f"{rotulo_subsecao(s)} ({n_total} req. · {n_core} Core)",
                                   key=f"sub_{s}",
                                   value=s in st.session_state.subsecoes_selecionadas):
                        selecionadas.append(s)

    st.session_state.subsecoes_selecionadas = selecionadas
    marcar_alteracao()

    if selecionadas:
        req_sel = requisitos[requisitos["subsecao"].isin(selecionadas)]
        total = len(req_sel)
        total_core = (req_sel["nivel"] == 1).sum()
        st.markdown(f"""
        <div class="progress-info">
        ✅ <b>{len(selecionadas)} subseção(ões) selecionada(s)</b> — total de <b>{total} requisitos</b>
        (sendo <b>{total_core} Core / Nível 1</b>).
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
# ETAPA 3 — AVALIAÇÃO
# ============================================================
elif st.session_state.etapa == 3:
    req_atuais = requisitos[requisitos["subsecao"].isin(st.session_state.subsecoes_selecionadas)].reset_index(drop=True)
    # Ordenar por subseção e item, e dentro disso por nível (Core primeiro)
    req_atuais = req_atuais.sort_values(["subsecao", "nivel", "item"]).reset_index(drop=True)
    total_req = len(req_atuais)

    if total_req == 0:
        st.warning("Nenhum requisito encontrado.")
        st.stop()

    idx = st.session_state.indice_atual
    idx = max(0, min(idx, total_req - 1))
    req = req_atuais.iloc[idx]
    chave = f"{req['subsecao']}__{req['item']}"
    is_core = req["nivel"] == 1

    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        st.subheader(f"📋 {rotulo_subsecao(req['subsecao'])}")
    with col_b:
        st.metric("Requisito", f"{idx+1} de {total_req}")
    with col_c:
        avaliados = sum(1 for v in st.session_state.avaliacoes.values() if v.get("avaliacao"))
        st.metric("Avaliados", f"{avaliados} de {total_req}")

    st.progress((idx+1) / total_req)

    # Filtro rápido por nível
    with st.expander("🔍 Navegação / Filtros"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_nivel = st.multiselect(
                "Mostrar apenas níveis:",
                [1, 2, 3],
                default=[1, 2, 3],
                format_func=lambda n: {1: "🔴 Core (N1)", 2: "🔵 N2", 3: "🟣 N3"}[n],
            )
            req_filtrados_idx = [i for i, r in req_atuais.iterrows() if r["nivel"] in filtro_nivel]
        with col_f2:
            st.markdown("**Status de cada requisito:**")
            stat_emoji = {"C": "✅", "PC": "🟡", "NC": "❌", "S": "⭐", "NA": "➖"}
            opcoes_nav = []
            for i, r in req_atuais.iterrows():
                if i not in req_filtrados_idx:
                    continue
                cv = st.session_state.avaliacoes.get(f"{r['subsecao']}__{r['item']}", {}).get("avaliacao", "")
                marker = stat_emoji.get(cv, "⚪")
                nivel_str = {1: "🔴", 2: "🔵", 3: "🟣"}.get(r["nivel"], "")
                opcoes_nav.append((i, f"{marker} {nivel_str} [{r['subsecao']}] item {r['item']} — {str(r['requisito'])[:60]}..."))

        if opcoes_nav:
            indices_disponiveis = [o[0] for o in opcoes_nav]
            labels = [o[1] for o in opcoes_nav]
            try:
                indice_pos = indices_disponiveis.index(idx)
            except ValueError:
                indice_pos = 0
            sel_label = st.selectbox("Ir para:", labels, index=indice_pos, key="nav_select")
            novo_idx = indices_disponiveis[labels.index(sel_label)]
            if novo_idx != idx:
                st.session_state.indice_atual = novo_idx
                st.rerun()

    st.divider()

    # Card do requisito (estilo diferente para Core)
    card_class = "req-card-core" if is_core else "req-card"
    badge = rotulo_nivel(req["nivel"])

    st.markdown(f"""
    <div class="{card_class}">
        <p style="margin:0;font-size:0.85rem;color:#666;">{badge}<b>Item {req['item']}</b></p>
        <p style="margin:0.5rem 0 0 0;font-size:1.05rem;"><b>{req['requisito']}</b></p>
    </div>
    """, unsafe_allow_html=True)

    if is_core:
        st.info("🔴 **Requisito CORE (Nível 1)** — fundamental para acreditação. Avalie com atenção especial.")

    if pd.notna(req.get("orientacoes")) and str(req["orientacoes"]).strip():
        with st.expander("📖 Orientações"):
            st.write(req["orientacoes"])

    if pd.notna(req.get("sugestao_evidencia")) and str(req["sugestao_evidencia"]).strip():
        with st.expander("📎 Sugestão de evidência"):
            st.write(req["sugestao_evidencia"])

    st.markdown("### Avaliação")

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

    if nova_aval:
        st.session_state.avaliacoes[chave] = {
            "subsecao": req["subsecao"],
            "item": req["item"],
            "nivel": int(req["nivel"]),
            "requisito": req["requisito"],
            "orientacoes": req.get("orientacoes", ""),
            "sugestao_evidencia": req.get("sugestao_evidencia", ""),
            "avaliacao": nova_aval,
            "observacao": observacao,
            "plano_acao": plano_acao,
        }
        marcar_alteracao()

    st.divider()

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
    total_core = (req_atuais["nivel"] == 1).sum()
    avaliados = sum(1 for v in st.session_state.avaliacoes.values() if v.get("avaliacao"))
    avaliados_core = sum(1 for v in st.session_state.avaliacoes.values()
                         if v.get("avaliacao") and v.get("nivel") == 1)
    nao_avaliados = total_req - avaliados

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total de requisitos", total_req)
    with col2: st.metric("Avaliados", avaliados)
    with col3: st.metric("Pendentes", nao_avaliados)
    with col4:
        if avaliados > 0:
            pct = avaliados / total_req * 100
            st.metric("Conclusão", f"{pct:.1f}%")

    # Status dos Core
    if total_core > 0:
        st.markdown(f"""
        <div class="progress-info">
        🔴 <b>Requisitos Core (Nível 1):</b> {avaliados_core} de {total_core} avaliados
        ({avaliados_core/total_core*100:.1f}%)
        </div>
        """, unsafe_allow_html=True)

    if nao_avaliados > 0:
        st.warning(f"⚠️ {nao_avaliados} requisito(s) ainda não foram avaliados. Você pode baixar mesmo assim — eles ficarão em branco.")

    # Contagem por status
    contagem = {"C": 0, "PC": 0, "NC": 0, "S": 0, "NA": 0}
    contagem_core = {"C": 0, "PC": 0, "NC": 0, "S": 0, "NA": 0}
    for v in st.session_state.avaliacoes.values():
        a = v.get("avaliacao")
        if a in contagem:
            contagem[a] += 1
            if v.get("nivel") == 1:
                contagem_core[a] += 1

    st.markdown("### Distribuição")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric("✅ Conforme", contagem["C"])
    with c2: st.metric("🟡 Parc. Conf.", contagem["PC"])
    with c3: st.metric("❌ Não Conf.", contagem["NC"])
    with c4: st.metric("⭐ Supera", contagem["S"])
    with c5: st.metric("➖ N/A", contagem["NA"])

    # Taxas: Conformidade, PC, NC sobre os avaliados (excluindo NA)
    avaliados_validos = contagem["C"] + contagem["PC"] + contagem["NC"] + contagem["S"]
    if avaliados_validos > 0:
        conf_pct = (contagem["C"] + contagem["S"]) / avaliados_validos * 100
        pc_pct = contagem["PC"] / avaliados_validos * 100
        nc_pct = contagem["NC"] / avaliados_validos * 100

        st.markdown(f"""
        <div class="progress-info">
        📊 <b>Taxa de conformidade (C + S):</b> {conf_pct:.1f}%<br>
        🟡 <b>Taxa de parcialmente conforme (PC):</b> {pc_pct:.1f}%<br>
        ❌ <b>Taxa de não conforme (NC):</b> {nc_pct:.1f}%<br>
        <small><i>Percentuais calculados sobre {avaliados_validos} avaliados (exclui Não Se Aplica).</i></small>
        </div>
        """, unsafe_allow_html=True)

    # Tabela específica para Core
    if total_core > 0 and avaliados_core > 0:
        with st.expander(f"🔴 Detalhamento dos requisitos Core (Nível 1)"):
            avaliados_core_validos = contagem_core["C"] + contagem_core["PC"] + contagem_core["NC"] + contagem_core["S"]
            if avaliados_core_validos > 0:
                conf_core = (contagem_core["C"] + contagem_core["S"]) / avaliados_core_validos * 100
                pc_core = contagem_core["PC"] / avaliados_core_validos * 100
                nc_core = contagem_core["NC"] / avaliados_core_validos * 100
                st.markdown(f"""
                **Taxa de conformidade Core:** {conf_core:.1f}%
                **Taxa PC Core:** {pc_core:.1f}%
                **Taxa NC Core:** {nc_core:.1f}%

                _Sobre {avaliados_core_validos} requisitos Core avaliados_
                """)
            cc1, cc2, cc3, cc4, cc5 = st.columns(5)
            with cc1: st.metric("✅ C", contagem_core["C"])
            with cc2: st.metric("🟡 PC", contagem_core["PC"])
            with cc3: st.metric("❌ NC", contagem_core["NC"])
            with cc4: st.metric("⭐ S", contagem_core["S"])
            with cc5: st.metric("➖ NA", contagem_core["NA"])

    st.divider()

    def gerar_excel():
        dados = st.session_state.dados_auditoria
        req_atuais_sort = req_atuais.sort_values(["subsecao", "nivel", "item"]).reset_index(drop=True)

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
                "nivel": int(req["nivel"]),
                "nivel_descricao": {1: "Nível 1 - Core/Segurança",
                                    2: "Nível 2 - Organização Integrada",
                                    3: "Nível 3 - Excelência"}.get(int(req["nivel"]), ""),
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

        cabecalho = pd.DataFrame({
            "Campo": ["Instituição", "Setor / Área", "Data", "Auditor líder",
                     "Auditor auxiliar", "Nº relatório", "Participantes",
                     "Ciclo", "Subseções avaliadas", "Total de requisitos",
                     "Requisitos Core (N1)", "Requisitos avaliados"],
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
                     total_core,
                     avaliados],
        })

        # Resumo por subseção (com colunas de % conforme, PC, NC)
        resumo_sub = df_resultado.groupby("subsecao").agg(
            total=("avaliacao", "count"),
            conforme=("avaliacao", lambda x: (x == "C").sum()),
            parcial=("avaliacao", lambda x: (x == "PC").sum()),
            nao_conforme=("avaliacao", lambda x: (x == "NC").sum()),
            supera=("avaliacao", lambda x: (x == "S").sum()),
            na=("avaliacao", lambda x: (x == "NA").sum()),
            nao_avaliado=("avaliacao", lambda x: (x == "").sum()),
        ).reset_index()
        validos = (resumo_sub["total"] - resumo_sub["na"] - resumo_sub["nao_avaliado"]).replace(0, 1)
        resumo_sub["pct_conformidade"] = ((resumo_sub["conforme"] + resumo_sub["supera"]) / validos * 100).round(1)
        resumo_sub["pct_parcial"] = (resumo_sub["parcial"] / validos * 100).round(1)
        resumo_sub["pct_nao_conforme"] = (resumo_sub["nao_conforme"] / validos * 100).round(1)

        # Resumo por nível
        resumo_nivel = df_resultado.groupby("nivel").agg(
            total=("avaliacao", "count"),
            conforme=("avaliacao", lambda x: (x == "C").sum()),
            parcial=("avaliacao", lambda x: (x == "PC").sum()),
            nao_conforme=("avaliacao", lambda x: (x == "NC").sum()),
            supera=("avaliacao", lambda x: (x == "S").sum()),
            na=("avaliacao", lambda x: (x == "NA").sum()),
        ).reset_index()
        validos_n = (resumo_nivel["total"] - resumo_nivel["na"]).replace(0, 1)
        resumo_nivel["pct_conformidade"] = ((resumo_nivel["conforme"] + resumo_nivel["supera"]) / validos_n * 100).round(1)
        resumo_nivel["pct_parcial"] = (resumo_nivel["parcial"] / validos_n * 100).round(1)
        resumo_nivel["pct_nao_conforme"] = (resumo_nivel["nao_conforme"] / validos_n * 100).round(1)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            cabecalho.to_excel(writer, sheet_name="Identificação", index=False)
            df_resultado.to_excel(writer, sheet_name="Avaliação", index=False)
            resumo_sub.to_excel(writer, sheet_name="Resumo_por_subsecao", index=False)
            resumo_nivel.to_excel(writer, sheet_name="Resumo_por_nivel", index=False)
        buffer.seek(0)
        return buffer

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

    st.divider()
    if contagem["NC"] > 0 or contagem["PC"] > 0:
        with st.expander(f"📋 Ver não-conformidades e plano de ação ({contagem['NC'] + contagem['PC']} itens)"):
            problemas = []
            for chave, v in st.session_state.avaliacoes.items():
                if v.get("avaliacao") in ("NC", "PC"):
                    problemas.append({
                        "Subseção": v["subsecao"],
                        "Item": v["item"],
                        "Nível": v.get("nivel", "-"),
                        "Status": v["avaliacao"],
                        "Requisito": v["requisito"][:80] + "...",
                        "Observação": v.get("observacao", "")[:80],
                        "Plano de ação": v.get("plano_acao", "")[:80],
                    })
            st.dataframe(pd.DataFrame(problemas), use_container_width=True, hide_index=True)
