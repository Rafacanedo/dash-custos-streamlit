# Dashboard de Custos Analítico

**(PT-BR)** Um dashboard interativo em Streamlit para análise e visualização de custos de obras. Ele processa planilhas de Relatório Gerencial (RG) para gerar KPIs de orçamento, projeção de custos, custos realizados e variação no término, oferecendo gráficos detalhados e tabelas dinâmicas para acompanhamento financeiro de projetos.

**(EN)** An interactive Streamlit dashboard for analyzing and visualizing construction cost data. It processes Managerial Report (RG) spreadsheets to track budget KPIs, cost projections, realized costs, and variance at completion, providing detailed charts and dynamic pivot tables for financial project monitoring.

---

This application is designed to ingest standard Managerial Report (Relatório Gerencial - RG) Excel spreadsheets and instantly generate a robust financial dashboard for construction and engineering projects. 

## Key Features

- **Automated Data Processing**: Upload formatted Excel files (`AAAA MM RG OBRA.xlsx`) and the app automatically parses the WBS (Work Breakdown Structure) data, extracting project name, reference month, and financial metrics.
- **Top-Level KPIs**: Instantly view the critical numbers: Budgeted Cost (Linha de Base do Custo), Projected Cost at Completion (Projeção do Custo - ENT), Realized Cost (Custo Realizado), and Variance at Completion (Variação no Término).
- **Interactive Visualizations**: 
  - Grouped bar charts showing budget progress normalized as percentage of completion.
  - Drill-down capabilities to view specific cost categories: Direct Costs, Indirect Costs, Additives, and Unforeseen Costs.
  - Pie charts breaking down the real cost projection status.
  - Horizontal bar charts highlighting financial variations with a red-to-green conditionally formatted percentage scale.
- **Dynamic Pivot Tables**: A multi-level pivot table allowing users to filter by Work Breakdown Structure (WBS) levels, equipped with conditional formatting to quickly spot negative or positive variations in specific service items.

## Tech Stack

- **Frontend / Framework:** Streamlit
- **Data Manipulation:** Pandas, NumPy
- **Data Visualization:** Plotly (Express & Graph Objects)

## Project Structure

```text
dash-custos-streamlit/
├── app.py                  # Main Streamlit application
├── process_rg.py           # Core logic for processing the RG spreadsheets
├── data/                   # Directory for storing data files (ignored in git)
├── requirements.txt        # Project dependencies
├── README.md               # Project documentation
└── TECHNICAL_DETAILS.md    # Additional technical documentation
```

## How to Run

1. Clone the repository:
   ```bash
   git clone https://github.com/Rafacanedo/dash-custos-streamlit.git
   ```
2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   streamlit run app.py
   ```
