import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io
import re
from process_rg import AnalisadorRG
from streamlit_pivottable import streamlit_pivottable
import pygwalker as pyg

# Configuração da Página
st.set_page_config(page_title="Dashboard de Custos Analítico", layout="wide", page_icon="📊")

# Custom CSS for larger metrics and layout
st.markdown("""
<style>
/* Make metrics title larger */
[data-testid="stMetricLabel"] {
    font-size: 1.1rem !important;
    font-weight: bold !important;
}
/* Make metrics value bold and prominent */
[data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: bold !important;
}
</style>
""", unsafe_allow_html=True)

def extrair_dados_arquivo(nome_arquivo):
    """Extrai obra, ano e mês do nome do arquivo (ex: 2024 10 RG Catarina.xlsx)"""
    match = re.search(r"(\d{4})\s+(\d{1,2})\s+RG\s+(.*?)(?:\.xlsx|\.xls)", nome_arquivo)
    if match:
        ano = match.group(1)
        mes = match.group(2)
        obra = match.group(3).strip()
        data_base = f"{ano}-{int(mes):02}-01"
        return obra, pd.to_datetime(data_base)
    return "Obra Desconhecida", pd.Timestamp.now()

def init_session_state():
    if 'stage' not in st.session_state:
        st.session_state.stage = 'upload'
    if 'rel_ava' not in st.session_state:
        st.session_state.rel_ava = None
    if 'custo_orcado' not in st.session_state:
        st.session_state.custo_orcado = None
    if 'saldo' not in st.session_state:
        st.session_state.saldo = None
    if 'nome_obra' not in st.session_state:
        st.session_state.nome_obra = None
    if 'data_base' not in st.session_state:
        st.session_state.data_base = None

def restart_app():
    for key in ['rel_ava', 'custo_orcado', 'saldo', 'nome_obra', 'data_base']:
        st.session_state[key] = None
    st.session_state.stage = 'upload'
    st.rerun()

init_session_state()

# ----------------- STAGE: UPLOAD -----------------
if st.session_state.stage == 'upload':
    st.title("📊 Upload de Relatório Gerencial")
    st.markdown("Faça o upload da planilha com o formato `AAAA MM RG OBRA.xlsx` para gerar o dashboard.")
    
    arquivo_up = st.file_uploader("Selecione o arquivo Excel", type=['xlsx', 'xls'])
    
    if arquivo_up:
        obra, data_base = extrair_dados_arquivo(arquivo_up.name)
        
        if st.button("Processar Dashboard", type="primary"):
            st.session_state.stage = 'loading'
            st.session_state.nome_obra = obra
            st.session_state.data_base = data_base
            st.session_state.arquivo_nome = arquivo_up.name
            st.session_state.arquivo_bytes = arquivo_up.getvalue()
            st.rerun()

# ----------------- STAGE: LOADING -----------------
elif st.session_state.stage == 'loading':
    with st.spinner('Processando dados...'):
        try:
            bytes_io = io.BytesIO(st.session_state.arquivo_bytes)
            analisador = AnalisadorRG(
                arquivo_bytes=bytes_io, 
                nome_obra=st.session_state.nome_obra, 
                data_base=st.session_state.data_base
            )
            
            rel_ava, custo_orcado, saldo = analisador.processar()
            
            st.session_state.rel_ava = rel_ava
            st.session_state.custo_orcado = custo_orcado
            st.session_state.saldo = saldo
            st.session_state.stage = 'dashboard'
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")
            if st.button("Voltar"):
                st.session_state.stage = 'upload'
                st.rerun()

# ----------------- STAGE: DASHBOARD -----------------
elif st.session_state.stage == 'dashboard':
    rel_ava = st.session_state.rel_ava
    custo_orcado = st.session_state.custo_orcado
    saldo = st.session_state.saldo
    obra = st.session_state.nome_obra
    data_base = st.session_state.data_base
    
    # Header
    col_t, col_b = st.columns([0.8, 0.2])
    with col_t:
        st.title(f"📊 Dashboard de Custos | {obra}")
        # Mês de Referência com fonte maior (Markdown H3)
        st.markdown(f"### **Mês de Referência:** {data_base.strftime('%m/%Y')}")
    with col_b:
        st.button("🔄 Novo Upload (Restart)", on_click=restart_app, use_container_width=True)
        
    st.markdown("---")

    # Helpers
    def get_first_level(df):
        return df[df['Level'] == 1].copy()
        
    def extrair_grupo(item_str):
        try:
            return int(str(item_str).split('.')[0])
        except:
            return 999

    def format_currency_mi(val):
        """Formatação para a área de Resumo (milhões)"""
        val_mi = val / 1_000_000
        if pd.isna(val_mi) or np.isinf(val_mi): val_mi = 0
        return f"R$ {val_mi:,.2f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
        
    def format_currency_br(val):
        """Formata moedas no padrão BR: 1.000,00"""
        if pd.isna(val): return ""
        v = f"{val:,.2f}"
        return v.replace(",", "X").replace(".", ",").replace("X", ".")

    # Filtros e Métricas Nível 1
    rel_ava_l1 = get_first_level(rel_ava)
    custo_orcado_l1 = get_first_level(custo_orcado)
    
    # 1. Top Level KPIs (Cards)
    linha_de_base = custo_orcado_l1['Custo Orçado'].sum()
    projecao_ent = rel_ava_l1['Estimativa no Termino ENT'].sum()
    custo_realizado = rel_ava_l1['Custo Realizado'].sum()
    variacao_termino = rel_ava_l1['Variacao Termino Final'].sum()
    
    st.markdown("## Resumo do Projeto", unsafe_allow_html=True)
    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    c_m1.metric("🏗️ Linha de Base do Custo", format_currency_mi(linha_de_base))
    
    projecao_str = format_currency_mi(projecao_ent)
    if projecao_ent > linha_de_base:
        projecao_str = "❗ " + projecao_str
    c_m2.metric("📈 Projeção do Custo (ENT)", projecao_str)
    
    c_m3.metric("💰 Custo Realizado", format_currency_mi(custo_realizado))
    
    delta_str = f"{'-' if variacao_termino < 0 else ''}R$ {abs(variacao_termino):,.2f}" if variacao_termino != 0 else None
    c_m4.metric("⚖️ Variação no Término", format_currency_mi(variacao_termino), delta=delta_str, delta_color="normal")

    
    st.markdown("---")
    
    # 2. Acompanhamento (Gráficos de Barras Agrupadas Normalizadas)
    st.markdown("## Acompanhamento", unsafe_allow_html=True)
    
    rel_ava_l1['Grp_Int'] = rel_ava_l1['Item'].apply(extrair_grupo)
    
    def criar_grouped_bar_chart(df_f, titulo):
        cr = df_f['Custo Realizado'].sum()
        ent = df_f['Estimativa no Termino ENT'].sum()
        orc = df_f['Custo Orçado'].sum()
        
        # Normalizando (Orçado = 100%)
        orc_norm = 100.0 if orc > 0 else 0.0
        ent_norm = (ent / orc * 100) if orc > 0 else 0.0
        cr_norm = (cr / orc * 100) if orc > 0 else 0.0
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=['Custo Orçado', 'Projeção do Custo', 'Custo Realizado'],
            y=[orc_norm, ent_norm, cr_norm],
            marker_color=['lightgray', 'black', 'blue'],
            text=[f'R$ {orc/1e6:.2f}M', f'R$ {ent/1e6:.2f}M', f'R$ {cr/1e6:.2f}M'],
            textposition='auto',
            name=titulo,
            hovertemplate="<b>%{x}:</b> %{text} (%{y:.0f}%)<extra></extra>"
        ))
        
        fig.update_layout(
            barmode='group',
            showlegend=False,
            height=300,
            margin=dict(l=40, r=40, t=40, b=30),
            yaxis=dict(title='% do Orçamento', showticklabels=True),
            title={'text': titulo, 'font': {'size': 16}, 'x': 0.5, 'xanchor': 'center'}
        )
        return fig

    # Gráfico Principal
    fig_global = criar_grouped_bar_chart(rel_ava_l1, "Progresso do Orçamento")
    st.plotly_chart(fig_global, use_container_width=True)
    
    with st.expander("🔍 Drill Down por Categoria"):
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(criar_grouped_bar_chart(rel_ava_l1[rel_ava_l1['Grp_Int'] < 16], "Custo Direto"), use_container_width=True)
            st.plotly_chart(criar_grouped_bar_chart(rel_ava_l1[(rel_ava_l1['Grp_Int'] >= 16) & (rel_ava_l1['Grp_Int'] <= 29)], "Custo Indireto"), use_container_width=True)
        with c2:
            st.plotly_chart(criar_grouped_bar_chart(rel_ava_l1[(rel_ava_l1['Grp_Int'] >= 30) & (rel_ava_l1['Grp_Int'] <= 39)], "Aditivos"), use_container_width=True)
            st.plotly_chart(criar_grouped_bar_chart(rel_ava_l1[rel_ava_l1['Grp_Int'] >= 40], "Não Previsto"), use_container_width=True)
    
    st.markdown("---")



    # 4. Pie Chart
    st.markdown("## Status da Projeção do Custo Real")
    itens_l1 = rel_ava_l1['Item'].unique()
    saldo_l1 = saldo[saldo['Item'].isin(itens_l1)].copy()
    
    # filter out 'Estimativa no Termino ENT'
    saldo_l1 = saldo_l1[saldo_l1['Tipo'] != 'Estimativa no Termino ENT']
    
    saldo_summ = saldo_l1.groupby('Tipo')['Valor'].sum().reset_index()
    saldo_summ = saldo_summ[saldo_summ['Valor'] > 0]
    
    if not saldo_summ.empty:
        # Pega valor em milhoes pro tooltip
        saldo_summ['Valor_mi'] = saldo_summ['Valor'] / 1_000_000
        fig_pie = px.pie(
            saldo_summ, 
            values='Valor', 
            names='Tipo',
            hole=0  # Filled pie chart
        )
        fig_pie.update_traces(
            textinfo='percent',  # Only percentage inside
            customdata=saldo_summ['Valor_mi'],
            hovertemplate="<b>%{label}</b><br>Valor: R$ %{customdata:,.2f} mi<br>Porcentagem: %{percent}<extra></extra>"
        )
        pull_array = [0.1 if t == 'Saldo da Projeção do Custo' else 0.0 for t in saldo_summ['Tipo']]
        fig_pie.update_traces(pull=pull_array)
        fig_pie.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=10)) # Keep legend intact by default
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Nenhum dado com valores positivos na tabela Saldo L1.")

    st.markdown("---")
    
    # 5. Variação Projetada Vertical (Piled)
    st.markdown("## Variação no Término")
    
    rel_ava_l1['Rotulo'] = rel_ava_l1['Item'].apply(lambda x: str(x).lstrip('0')) + " - " + rel_ava_l1['Servico']
    
    def plot_var_piled(df, title):
        if df.empty: return None
        
        df_plot = df.copy()
        df_plot['Var_mil'] = df_plot['Variacao Termino Final'] / 1000
        
        # Calculate Percentage (Delta Normalized)
        df_plot['Perc_Delta'] = (df_plot['Variacao Termino Final'] / df_plot['Custo Orçado'].replace(0, np.nan)) * 100
        df_plot['Perc_Delta'] = df_plot['Perc_Delta'].replace([np.inf, -np.inf], 0).fillna(0)
        
        # Sort values so they display neatly in the horizontal chart
        df_plot = df_plot.sort_values(by='Perc_Delta', ascending=True)
        
        fig = px.bar(
            df_plot,
            y='Rotulo', # Agora o Rótulo vai no Y (gráfico horizontal)
            x='Variacao Termino Final', # E o valor financeiro no X
            orientation='h',
            title=title,
            color='Perc_Delta',
            color_continuous_scale=[(0, "red"), (0.5, "gray"), (1, "green")],
            color_continuous_midpoint=0,
            text='Perc_Delta',
            custom_data=['Var_mil', 'Perc_Delta']
        )
        fig.update_traces(
            texttemplate='%{text:,.0f}%',
            textposition='outside', # Mostra a % fora da barra
            hovertemplate="<b>%{y}</b><br>Variação: R$ %{customdata[0]:,.2f} mil<br>Percentual (% Orçamento): %{customdata[1]:,.2f}%<extra></extra>",
            marker_line_width=0,
        )
        fig.update_layout(
            height=500, # Aumentado um pouco para caber os labels Y
            coloraxis_showscale=False,
            margin=dict(l=150, r=40, t=40, b=40), # Margem esquerda maior pros rótulos textuais
            yaxis=dict(title=''), # Esconde "Rotulo"
            xaxis=dict(title='Variação (R$)', zeroline=True, zerolinewidth=1, zerolinecolor='black', tickformat=".2s")
        )
        return fig
    
    df_cd = rel_ava_l1[rel_ava_l1['Grp_Int'] < 16]
    fig_cd = plot_var_piled(df_cd, "Custo Direto")
    
    df_ci = rel_ava_l1[(rel_ava_l1['Grp_Int'] >= 16) & (rel_ava_l1['Grp_Int'] <= 29)]
    fig_ci = plot_var_piled(df_ci, "Custo Indireto")
    
    df_ad = rel_ava_l1[(rel_ava_l1['Grp_Int'] >= 30) & (rel_ava_l1['Grp_Int'] <= 39)]
    fig_ad = plot_var_piled(df_ad, "Aditivos")

    col_var1, col_var2, col_var3 = st.columns(3)
    with col_var1:
        if fig_cd: st.plotly_chart(fig_cd, use_container_width=True)
    with col_var2:
        if fig_ci: st.plotly_chart(fig_ci, use_container_width=True)
    with col_var3:
        if fig_ad: st.plotly_chart(fig_ad, use_container_width=True)

    st.markdown("---")
    
    # 6. Tabela Dinâmica (Pivot Table) com Níveis
    st.markdown("## Rel Ava")
    
    # Selecionar colunas numéricas de rel_ava
    numeric_cols = rel_ava.select_dtypes(include=[np.number]).columns.tolist()
    cols_to_remove = ['Grp_Int', 'Level']
    numeric_cols = [c for c in numeric_cols if c not in cols_to_remove]
    
    # Preparar DataFrame para a tabela baseando-se no level
    df_pivot = rel_ava.copy()
    
    # Adicionar o serviço ao item para melhor identificação
    df_pivot['Item_Completo'] = df_pivot['Item'].astype(str) + " - " + df_pivot['Servico']
    
    # Obter lista de níveis únicos
    niveis_disponiveis = sorted(df_pivot['Level'].unique().tolist())
    niveis_default = [1] if 1 in niveis_disponiveis else niveis_disponiveis
    
    # Filtro multiselect para Nível
    niveis_selecionados = st.multiselect(
        "Filtrar por Nível:",
        options=niveis_disponiveis,
        default=niveis_default
    )
    
    # Filtrar o DataFrame pelos níveis escolhidos
    if niveis_selecionados:
        df_filtered = df_pivot[df_pivot['Level'].isin(niveis_selecionados)]
    else:
        df_filtered = df_pivot.copy() # Mostra tudo se limpar o filtro
        
    # Organizar por nível
    pivot_native = pd.pivot_table(
        df_filtered,
        index=['Level', 'Item_Completo'],
        values=numeric_cols,
        aggfunc='sum'
    ).reset_index()
    
    # Garantir que a ordem das colunas seja igual a da tabela original
    cols_order = ['Level', 'Item_Completo'] + numeric_cols
    
    # Mover 'Custo Orçado' e 'Representatividade' para antes de 'Andamento Fisico'
    for col in ['Custo Orçado', 'Representatividade']:
        if col in cols_order and 'Andamento Fisico' in cols_order:
            cols_order.remove(col)
            idx = cols_order.index('Andamento Fisico')
            cols_order.insert(idx, col)
        
    pivot_native = pivot_native[cols_order]
    
    # Ordenar por Item (já que Nível + Item_Completo segue a ordem natural do WBS)
    pivot_native = pivot_native.sort_values(by=['Item_Completo'])
    
    # Custom formatters para as colunas do Pivot Table
    def style_br(val):
        if pd.isna(val) or isinstance(val, str): return val
        v = f"{val:,.2f}"
        return "R$ " + v.replace(",", "X").replace(".", ",").replace("X", ".")
        
    def style_pct(val):
        if pd.isna(val) or isinstance(val, str): return val
        v = f"{val * 100:,.2f}"
        return v.replace(",", "X").replace(".", ",").replace("X", ".") + "%"
        
    def style_dec(val):
        if pd.isna(val) or isinstance(val, str): return val
        v = f"{val:,.2f}"
        return v.replace(",", "X").replace(".", ",").replace("X", ".")

    formatters = {}
    for col in numeric_cols:
        if col in ['Andamento Fisico', 'Representatividade']:
            formatters[col] = style_pct
        elif col == 'IDC':
            formatters[col] = style_dec
        else:
            formatters[col] = style_br
            
    # Conditional formatting for Variacao Termino Final
    def color_variacao(val):
        if pd.isna(val) or isinstance(val, str): return ''
        color = 'green' if val > 0 else 'red' if val < 0 else ''
        return f'color: {color}'
            
    styled_pivot = (pivot_native.style
                    .format(formatters)
                    .map(color_variacao, subset=['Variacao Termino Final'] if 'Variacao Termino Final' in pivot_native.columns else None)
                   )
    
    # Esconder a coluna "Level" usando column_config (o valor None oculta a coluna)
    st.dataframe(
        styled_pivot, 
        use_container_width=True, 
        hide_index=True,
        column_config={"Level": None}
    )
