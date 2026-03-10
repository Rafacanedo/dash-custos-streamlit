# Documentação Técnica dos Scripts

Este documento detalha o funcionamento interno dos dois pilares principais do projeto: o pipeline de dados (`process_rg.py`) e o dashboard interativo (`app.py`).

---

## 1. Scripts/process_rg.py (Pipeline de Dados)

O script utiliza a classe `AnalisadorRG` para encapsular toda a lógica de ETL (Extração, Transformação e Carga).

### Classe `AnalisadorRG`
**Construtor (`__init__`)**:
- `pasta_origem`: Caminho onde estão os arquivos Excel brutos (`Crawl`).
- `nome_filtro`: String para filtrar os arquivos da obra (ex: "RG Catarina").
- `pasta_destino_powerbi`: Caminho onde as tabelas tratadas serão salvas (`PowerBI`).

### Principais Métodos

#### `consolidar_rel_ava()`
- **Objetivo**: Lê a aba "Rel AVA" de todos os históricos Excel da obra.
- **Lógica**:
  1. Extrai Data e Nome da Obra a partir do nome do arquivo usando regex.
  2. Filtra as 20 colunas padrão da planilha corporativa.
  3. Remove linhas de soma ("TOTAL"), linhas vazias e códigos de serviço irrelevantes (0, 2).
  4. Realiza a limpeza de tipos (conversão para numérico) e formatação hierárquica do campo `Item`.
  5. **Regra de Negócio**: Remove automaticamente o item `E` (padrão Catarina/Valmet).

#### `gerar_custo_orcado()`
- **Objetivo**: Gera o baseline (orçamento inicial) a partir da aba `ClasR$` do arquivo mais recente.
- **Lógica**:
  1. Renomeia a coluna "Previsto" para "Custo Orçado".
  2. Calcula o `Level` (profundidade na árvore de custos) baseando-se na pontuação do item (ex: `01.02` = Nível 2).
  3. **Regra de Negócio**: Força `Level 0` para itens "A" e "B" para facilitar agrupamentos no dashboard.

#### `calcular_rel_ava_historico()`
- **Objetivo**: Realiza cálculos incrementais de tempo cruzando os meses.
- **Lógica**:
  1. Ordena os dados cronologicamente.
  2. Calcula o **Custo Realizado Período**: `Custo_Atual - Custo_Anterior`.
  3. Calcula o **IDC (Índice de Desempenho de Custo)** e a **Estimativa no Término (ETN)**.
  4. Garante que os indicadores reflitam o acumulado correto até a data de status.

#### `gerar_saldo()`
- **Objetivo**: Cria a tabela para análise de projeção de saldo.
- **Lógica**:
  1. Utiliza a função `melt` para transformar colunas (Contratos, OCs, Comprometido) em linhas.
  2. Calcula a nova métrica **Saldo da Projeção do Custo** via fórmula: `ETN - Contrato - OCs - Desembolso - Comprometido`.

---

## 2. app.py (Dashboard Streamlit)

O dashboard é a interface visual consumidora das tabelas geradas pelo pipeline.

### Estrutura de Fluxo

1. **Carregamento de Dados (`load_data`)**:
   - Utiliza `@st.cache_data` para evitar releituras de disco a cada interação do usuário.
   - Lê os arquivos `Rel Ava.xlsx`, `Saldo.xlsx` e `Custo Orçado.xlsx`.

2. **Gerenciamento de Filtros**:
   - **Obra**: Scaneia as subpastas em busca de dados processados.
   - **Mês de Status**: Filtra os DataFrames em tempo real baseando-se na seleção da sidebar.

3. **Renderização de Visuais (Plotly)**:
   - **KPIs**: Utiliza `st.columns` e `st.metric` para exibir os grandes números (IDC, Custo Total, etc).
   - **Gráfico de Evolução (`go.Figure`)**: Combina um gráfico de Barras (Custo) com um de Linhas (Desembolso) em um mesmo eixo temporal.
   - **Gráfico de Saldo (`px.bar`)**: Exibe uma barra horizontal (`orientation='h'`) mostrando as parcelas que compõem o saldo aberto do projeto.

---

## Funções Auxiliares (Utils)

Localizadas no início do `process_rg.py`:
- `formatar_item()`: Normaliza itens como "1" para "01" e "1.2" para "01.02".
- `extrair_data()`: Usa expressões regulares para converter "2024 10 RG..." em atributos de Ano e Mês.
- `cria_ano_mes()`: Garante que as datas sempre apontem para o **último dia do mês**, padronizando a escala temporal do Dashboard.
