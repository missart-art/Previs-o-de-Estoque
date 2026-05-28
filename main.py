import streamlit as st
import pandas as pd
from datetime import datetime
from database import init_db, upsert_produto, adicionar_estoque, registrar_consumo, get_dados_inventario
from logic import simular_duracao, get_tipo_dia
import os
import time
import tempfile

# Cria o caminho seguro para a pasta temporária do servidor
# Valores padrão caso o arquivo não exista
modo_previsao = 1
modo_financeiro = 1

if os.path.exists("config.txt"):
    with open("config.txt", "r") as f:
        for linha in f:
            if "modo_previsao" in linha:
                modo_previsao = int(linha.split("=")[1].strip())
            if "modo_financeiro" in linha:
                modo_financeiro = int(linha.split("=")[1].strip())

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="PrevHostel Pro - Gestão", layout="wide", page_icon="🏨")
init_db()

st.title("🏨 PrevHostel Pro - Gestão Integrada")

# Criamos as mesmas abas que você tinha no Tkinter
abas_nomes = ["📦 REPOSIÇÃO", "📋 INVENTÁRIO", "📉 GASTO DIÁRIO"]
if modo_financeiro == 1:
    abas_nomes.append("💰 FINANCEIRO")

abas = st.tabs(abas_nomes)
tab_reposicao, tab_inventario, tab_gasto = abas[0], abas[1], abas[2]

# --- ABA 1: REPOSIÇÃO (Entrada de Mercadoria)[cite: 8] ---
with tab_reposicao:
    st.subheader("Adicionar ou Atualizar Produto")
    with st.form("form_entrada"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome do Produto", placeholder="Ex: Papel Higiênico")
        estoque_min = col2.number_input("Estoque Mínimo (Alerta)", min_value=0, step=1)
        
        # Injeção do Passo 3: Campo de preço dinâmico
        preco_venda = 0.0
        if modo_financeiro == 1:
            preco_venda = st.number_input("Preço de Venda (R$)", min_value=0.0, step=0.50, format="%.2f")
        
        quantidade = st.number_input("Quantidade para Adicionar ao Estoque", min_value=0, step=1)
        
        if st.form_submit_button("Confirmar Entrada"):
            if nome:
                # Passando o preço de venda coletado para a função do banco
                upsert_produto(nome, estoque_min, preco_venda)
                adicionar_estoque(nome, quantidade)
                st.success(f"Estoque de '{nome}' atualizado com sucesso!")
            else:
                st.error("Por favor, insira o nome do produto.")

# --- ABA 2: INVENTÁRIO (Visualização e Previsão)[cite: 7, 8] ---
with tab_inventario:
    if modo_previsao and not modo_financeiro:
        st.subheader("Situação Atual e Previsão de Término:")
    if modo_financeiro and not modo_previsao:
        st.subheader("Estoque Atual:")
        
    dados = get_dados_inventario()
    
    if not dados:
        st.info("Nenhum produto cadastrado no inventário.")
    else:
        lista_final = []
        for p_id, nome, atual, minimo, preco in dados:
            dias, previsao = simular_duracao(nome, atual)
            
            if atual <= 0:
                status = "🚨 ESGOTADO"
            elif atual <= minimo:
                status = "⚠️ REPOR AGORA"
            else:
                status = "✅ EM DIA"
                
            item_tabela = {
                "ID": p_id,
                "Produto": nome,
                "Estoque Atual": atual,
                "Estoque Mínimo": minimo,
                "Preço de Venda (R$)": preco,
                "Status": status
            }
            
            if modo_previsao == 1:
                item_tabela["Duração Est. (Dias)"] = dias
                item_tabela["Data Estimada"] = previsao
                
            lista_final.append(item_tabela)
        
        df_inv = pd.DataFrame(lista_final)
        
        # Exibe a tabela como editor interativo
        df_editado = st.data_editor(
            df_inv, 
            use_container_width=True, 
            hide_index=True, 
            key="editor_estoque",
            column_config={
                "ID": st.column_config.NumberColumn("ID", disabled=True),
                "Status": st.column_config.TextColumn("Status", disabled=True),
                "Duração Est. (Dias)": st.column_config.TextColumn("Duração Est. (Dias)", disabled=True),
                "Data Estimada": st.column_config.TextColumn("Data Estimada", disabled=True),
                
                # Travas para não aceitar valores nulos (células vazias)
                "Produto": st.column_config.TextColumn(required=True),
                "Estoque Atual": st.column_config.NumberColumn(required=True),
                "Preço de Venda (R$)": st.column_config.NumberColumn(required=True),
            }
        )
        
        # Botão para processar e salvar apenas as linhas modificadas
        # Botão para processar e salvar apenas as linhas modificadas
        if st.button("💾 Salvar Alterações da Tabela"):
            from database import atualizar_produto_pela_tabela
            
            alteracoes = st.session_state.editor_estoque.get("edited_rows", {})
            
            if alteracoes:
                for idx_linha, mudancas in alteracoes.items():
                    # Garante que o índice é lido corretamente
                    idx_linha = int(idx_linha)
                    
                    # Pega a linha completa já com as edições feitas pelo usuário
                    linha_nova = df_editado.iloc[idx_linha]
                    
                    p_id = int(linha_nova["ID"])
                    novo_nome = str(linha_nova["Produto"])
                    novo_estoque = float(linha_nova["Estoque Atual"])
                    novo_minimo = float(linha_nova["Estoque Mínimo"])
                    novo_preco = float(linha_nova["Preço de Venda (R$)"])
                    
                    atualizar_produto_pela_tabela(p_id, novo_nome, novo_estoque, novo_minimo, novo_preco)
                
                st.success("Alterações salvas com sucesso!")
                st.rerun()
            else:
                st.info("Nenhuma modificação detectada para salvar.")

# --- ABA 3: GASTO DIÁRIO (Registro de Consumo)[cite: 7, 8] ---
with tab_gasto:
    st.subheader("Registrar Consumo")
    produtos_cadastrados = [p[1] for p in get_dados_inventario()]
    
    if not produtos_cadastrados:
        st.warning("Cadastre produtos na aba de Reposição primeiro.")
    else:
        # --- FORMULÁRIO DE REGISTRO ---
        with st.form("form_consumo"):
            col1, col2, col3 = st.columns(3)
            produto_sel = col1.selectbox("Produto", produtos_cadastrados)
            qtd_consumida = col2.number_input("Quantidade", min_value=1, step=1)
            data_consumo = col3.date_input("Data", datetime.now())
            funcionario = st.text_input("Vendedor/Funcionário", placeholder="Nome")
            
            if st.form_submit_button("🚀 Registrar Gasto"):
                tipo = get_tipo_dia(data_consumo)
                data_completa = datetime.combine(data_consumo, datetime.now().time()).strftime("%Y-%m-%d %H:%M:%S")
                # O último 'None' garante que nada de foto seja enviado
                registrar_consumo(produto_sel, qtd_consumida, tipo, funcionario, data_completa, None)
                
                st.toast(f"Consumo de {produto_sel} registrado!")
                st.rerun()

        st.divider() # Separa o formulário do histórico

        # --- SEÇÃO DE HISTÓRICO E BUSCA ---
        st.subheader("📜 Histórico de Lançamentos")
        
        # Campo de busca em tempo real[cite: 8]
        termo_busca = st.text_input("🔍 Buscar por produto ou data (AAAA-MM-DD)", 
                                    placeholder="Ex: Cerveja ou 2026-04-30")
        
        from database import get_historico_gastos
        df_hist = get_historico_gastos(termo_busca)
        
        if df_hist.empty:
            st.write("Nenhum registro encontrado.")
        else:
            # Mostra a tabela de histórico[cite: 8]
            # Mostra a tabela (o caminho da foto aparece na coluna 'Comprovante')
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            
            # Botão para abrir as fotos
            
# --- ABA 4: FINANCEIRO ---
if modo_financeiro == 1:
    with abas[3]:
        st.subheader("Relatório de Faturamento")
        
        # Filtro de tempo
        filtro_tempo = st.radio("Período", ["Hoje", "Últimos 7 dias", "Últimos 30 dias"], horizontal=True)
        
        from datetime import datetime, timedelta
        if filtro_tempo == "Hoje":
            dias_voltar = 0
        elif filtro_tempo == "Últimos 7 dias":
            dias_voltar = 7
        else:
            dias_voltar = 30
            
        data_filtro = (datetime.now() - timedelta(days=dias_voltar)).strftime("%Y-%m-%d")
        
        # Busca os dados
        from database import get_faturamento
        df_fin = get_faturamento(data_filtro)
        
        if df_fin.empty:
            st.info("Nenhuma venda registrada neste período.")
        else:
            # Mostra o totalzão em destaque
            total_geral = df_fin['Total_R$'].sum()
            st.metric("Faturamento Total do Período", f"R$ {total_geral:.2f}")
            
            # Mostra a tabela detalhada
            st.dataframe(df_fin, use_container_width=True, hide_index=True)