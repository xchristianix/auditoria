# Auditoria ONA 2026 — ICHC/HC-FMUSP

App Streamlit para auditoras lançarem avaliações de auditoria interna ONA (ciclo 2026 / OPSS 2026) in loco e baixarem Excel pronto para envio à SEIG.

## Como funciona

1. **Identificação** — auditora preenche dados básicos (nome, setor, data, participantes)
2. **Seleção de subseções** — escolhe quais subseções da norma serão avaliadas naquele setor
3. **Avaliação** — sistema mostra um requisito por vez, com orientações e sugestão de evidência; auditora marca C / PC / NC / S / NA e escreve observação e plano de ação
4. **Download** — Excel pronto com identificação, avaliação completa e resumo por subseção

## Estrutura de arquivos

```
app_auditoria_ona/
├── app.py                    # Aplicação Streamlit
├── requisitos_2026.csv       # Catálogo de 1.333 requisitos OPSS 2026
├── nomes_subsecoes.json      # Mapeamento código → nome legível das subseções
├── setores.json              # Lista de setores do ICHC (centros de custo já auditados)
├── requirements.txt          # Dependências Python
└── README.md
```

## Deploy no Streamlit Cloud (gratuito)

1. **Criar repositório no GitHub**
   - Crie um repo público (ex: `auditoria-ona-ichc`)
   - Suba todos os arquivos desta pasta (não precisa de `.gitignore` especial)

2. **Conectar ao Streamlit Cloud**
   - Acesse https://share.streamlit.io
   - Faça login com sua conta GitHub
   - Clique em "New app"
   - Selecione o repositório, branch `main` e arquivo `app.py`
   - Clique em "Deploy"

3. **Pronto!**
   - A app fica disponível em uma URL pública (ex: `auditoria-ona-ichc.streamlit.app`)
   - Pode compartilhar com as auditoras direto

## Rodando localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

A app abrirá em http://localhost:8501

## Estrutura do Excel gerado

Cada arquivo baixado tem 3 abas:

- **Identificação** — dados da auditoria (setor, auditor, data, participantes)
- **Avaliação** — uma linha por requisito, com 21 colunas compatíveis com o consolidado SEIG
- **Resumo_por_subsecao** — contagem e % de conformidade por subseção avaliada

Compatível com o pipeline do consolidado ONA existente — pode ser ingerido diretamente.

## Manutenção do catálogo de requisitos

Se a ONA publicar atualização do OPSS 2026, basta regenerar o `requisitos_2026.csv` a partir do arquivo-modelo da norma e fazer commit no GitHub — o Streamlit Cloud atualiza sozinho.
