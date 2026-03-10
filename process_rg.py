import pandas as pd
import numpy as np

def formatar_item(item):
    """
    Formata a string 'item' no formato hierárquico xx.xx.xx...
    """
    try:
        parts = str(item).split('.')
        formatted_parts = [f"{int(part):02}" for part in parts]
        return ".".join(formatted_parts)
    except ValueError:
        return str(item)
    except AttributeError:
        return str(item)
    
def calcular_nivel(item):
    """
    Calcula o nível hierárquico com base na coluna 'Item' formatada.
    """
    if not item or pd.isna(item):
        return 0
    return str(item).count(".") + 1

class AnalisadorRG:
    """
    Classe para extração e processamento das tabelas 
    Rel AVA, Saldo e Custo Orçado a partir de um relatório gerencial (RG) carregado.
    """
    def __init__(self, arquivo_bytes, nome_obra, data_base):
        self.arquivo_bytes = arquivo_bytes
        self.nome_obra = nome_obra
        self.data_base = data_base
        
        # Padrões de colunas do Rel AVA (20 primeiras colunas)
        self.colunas_rel_ava = [
            'Item', 'Servico_RelAva', 'Andamento Fisico', 'Orcamento_RelAva',
            'Valor Agregado', 'Desembolso Realizado', 'Comprometido Lancado', 'Executado N Medido',
            'Comprometido', 'Estoque Adiantamento', 'Custo Realizado', 'Variacao de Custo',
            'OCs Aberto', 'Saldo Contrato Aberto', 'Saldo a Ser Contratado', 'IDC',
            'Estimativa no Termino_RelAva', 'Variação no Término pela AVA (R$)', 'Variacao Termino Final', 'Estimativa no Termino ENT'
        ]

    def _extrair_rel_ava(self):
        """Lê a aba Rel AVA e trata a tabela."""
        try:
            df = pd.read_excel(self.arquivo_bytes, sheet_name="Rel AVA", header=11, engine='openpyxl')
            dados = df.iloc[:, :20].copy()
            if len(dados.columns) != len(self.colunas_rel_ava):
                raise ValueError(f"O arquivo não possui as 20 colunas esperadas na aba Rel AVA. Possui {len(dados.columns)}")
                
            dados.columns = self.colunas_rel_ava
            
            remover = {'TOTAL'}
            dados = dados[~(dados['Item'].astype(str).str.upper().isin({i.upper() for i in remover}) | pd.isna(dados['Item']))]
            dados = dados.fillna(0)
            
            # Filtros padrão
            dados = dados[dados['Item'] != 0]
            dados = dados[dados['Servico_RelAva'] != 0]
            dados = dados[dados['Servico_RelAva'] != 2]
            
            # Removendo 'E'
            dados = dados[dados['Item'] != 'E']
            
            # Não precisamos da coluna Servico do RelAva pois vem sem descrição util quase sempre, e usamos a do Custo Orcado
            dados.drop(columns=['Servico_RelAva'], inplace=True)
            
            dados['Item'] = dados['Item'].astype(str).apply(formatar_item)
            
            # Conversões numéricas
            cols_numericas = ['Andamento Fisico', 'Valor Agregado', 'Desembolso Realizado', 
                              'Comprometido', 'Custo Realizado', 'Variacao Termino Final', 
                              'Estimativa no Termino ENT', 'OCs Aberto', 'Saldo Contrato Aberto']
            for col in cols_numericas:
                dados[col] = pd.to_numeric(dados[col], errors='coerce').fillna(0)
                
            return dados
        except Exception as e:
            raise Exception(f"Erro ao extrair Rel AVA: {e}")

    def _extrair_custo_orcado(self):
        """Lê a aba ClasR$ para extrair a baseline."""
        try:
            df = pd.read_excel(self.arquivo_bytes, sheet_name='ClasR$', header=11, engine='openpyxl')
            dados = df.iloc[:, [0, 1, 2]].copy()
            dados.columns = ['Item', 'Servico', 'Custo Orçado']
            
            dados = dados.dropna(subset=['Item'])
            dados['Custo Orçado'] = pd.to_numeric(dados['Custo Orçado'], errors='coerce').fillna(0)
            dados['Servico'] = dados['Servico'].fillna('Sem Descrição')
            
            dados = dados[~dados['Servico'].isin([0, 2, '0', '2'])]
            dados = dados[~dados['Item'].astype(str).str.upper().isin(["TOTAL"])]
            
            dados['Item'] = dados['Item'].astype(str).apply(formatar_item)
            dados['Level'] = dados['Item'].apply(calcular_nivel)
            
            # Regra Padrão (Catarina/Valmet)
            dados.loc[dados['Item'].isin(["A", "B"]), 'Level'] = 0
            
            total_orcado = dados[dados['Level'] == 1]['Custo Orçado'].sum()
            dados['Representatividade'] = dados['Custo Orçado'] / total_orcado if total_orcado != 0 else 0
            dados['Grupo'] = dados['Item'].str.split('.').str[0]
            
            return dados
        except Exception as e:
            raise Exception(f"Erro ao extrair Custo Orçado: {e}")

    def _merge_relava_custo(self, rel_ava, custo_orcado):
        """Junta RelAva e Custo Orçado"""
        merged = pd.merge(
            rel_ava,
            custo_orcado[['Item', 'Servico', 'Custo Orçado', 'Level', 'Representatividade', 'Grupo']],
            on='Item',
            how='left'
        )
        
        # Preencher Level e Grupo para itens não emparelhados pra nao quebrar filtros
        merged['Level'] = merged['Level'].fillna(0)
        merged['Servico'] = merged['Servico'].fillna('Desconhecido')
        merged['Custo Orçado'] = merged['Custo Orçado'].fillna(0)
        
        merged['Obra'] = self.nome_obra
        merged['Data'] = self.data_base
        
        return merged

    def _gerar_saldo(self, df_merged):
        """Gera a tabela Saldo baseada no Merged."""
        colunas_necessarias = ['Obra', 'Item', 'Data', 'Comprometido', 'Desembolso Realizado', 'Estimativa no Termino ENT', 'OCs Aberto', 'Saldo Contrato Aberto']
        colunas_disponiveis = [c for c in colunas_necessarias if c in df_merged.columns]
        
        saldo_base = df_merged[colunas_disponiveis].copy()
        saldo_melted = saldo_base.melt(id_vars=['Obra', 'Item', 'Data'], var_name='Tipo', value_name='Valor')
        saldo_melted = saldo_melted[saldo_melted['Valor'] != 0].reset_index(drop=True)
        
        saldo_agg = saldo_melted.groupby(['Obra', 'Data', 'Item', 'Tipo']).agg({'Valor': 'sum'}).reset_index()
        
        linhas_saldo_proj = []
        for (obra_val, data_val, item_val), rel_group in saldo_agg.groupby(['Obra', 'Data', 'Item']):
            # Pega as somas para o item/data
            d = rel_group.set_index('Tipo')['Valor'].to_dict()
            etn = d.get('Estimativa no Termino ENT', 0)
            contrato = d.get('Saldo Contrato Aberto', 0)
            ocs = d.get('OCs Aberto', 0)
            desembolso = d.get('Desembolso Realizado', 0)
            comprometido = d.get('Comprometido', 0)
            
            # Padrao Valmet/Catarina
            saldo_proj = etn - contrato - ocs - desembolso - comprometido
            
            if saldo_proj != 0:
                linhas_saldo_proj.append({
                    'Obra': obra_val,
                    'Data': data_val,
                    'Item': item_val,
                    'Tipo': 'Saldo da Projeção do Custo',
                    'Valor': saldo_proj
                })
                
        if linhas_saldo_proj:
            saldo_agg = pd.concat([saldo_agg, pd.DataFrame(linhas_saldo_proj)], ignore_index=True)
            
        return saldo_agg

    def processar(self):
        """Orquestra o ETL e retorna as tabelas em memória."""
        custo_orcado = self._extrair_custo_orcado()
        rel_ava = self._extrair_rel_ava()
        
        rel_ava_merged = self._merge_relava_custo(rel_ava, custo_orcado)
        saldo = self._gerar_saldo(rel_ava_merged)
        
        return rel_ava_merged, custo_orcado, saldo
