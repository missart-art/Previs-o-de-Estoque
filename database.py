import psycopg2
import streamlit as st
import pandas as pd

@st.cache_resource
def get_connection():
    """Conecta ao Supabase usando a URL dos Secrets."""
    return psycopg2.connect(st.secrets["DATABASE_URL"])

def init_db():
    """Inicializa as tabelas no PostgreSQL."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''  
        CREATE TABLE IF NOT EXISTS produtos (
            id SERIAL PRIMARY KEY,
            nome TEXT UNIQUE NOT NULL,
            estoque_atual REAL DEFAULT 0,
            estoque_geral REAL DEFAULT 0,
            estoque_minimo REAL DEFAULT 0,
            preco_venda REAL DEFAULT 0.0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_gastos (
            id SERIAL PRIMARY KEY,
            produto_id INTEGER REFERENCES produtos(id),
            data TEXT NOT NULL,
            quantidade REAL NOT NULL,
            tipo_dia TEXT NOT NULL,
            preco_vendido REAL DEFAULT 0.0,
            funcionario TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    
    

def upsert_produto(nome, estoque_min, preco_venda=0.0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO produtos (nome, estoque_minimo, preco_venda) 
        VALUES (%s, %s, %s)
        ON CONFLICT (nome) DO UPDATE SET 
            estoque_minimo = EXCLUDED.estoque_minimo,
            preco_venda = EXCLUDED.preco_venda
    ''', (nome, estoque_min, preco_venda))
    conn.commit()
    
    

def adicionar_estoque(nome, qtd):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE produtos 
        SET estoque_atual = estoque_atual + %s, 
            estoque_geral = estoque_geral + %s 
        WHERE nome = %s
    ''', (qtd, qtd, nome))
    conn.commit()
    
    

def registrar_consumo(nome, qtd, tipo_dia, funcionario, data=None):
    if data is None:
        from datetime import datetime
        data = datetime.now().strftime("%Y-%m-%d")
        
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE produtos 
        SET estoque_atual = estoque_atual - %s, 
            estoque_geral = estoque_geral - %s 
        WHERE nome = %s
    ''', (qtd, qtd, nome))
    
    cursor.execute('''
        INSERT INTO historico_gastos (produto_id, data, quantidade, tipo_dia, preco_vendido, funcionario)
        SELECT id, %s, %s, %s, preco_venda, %s FROM produtos WHERE nome = %s
    ''', (data, qtd, tipo_dia, funcionario, nome))
    
    conn.commit()
    
    

def get_dados_inventario():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome, estoque_atual, estoque_minimo, preco_venda, estoque_geral FROM produtos')
    dados = cursor.fetchall()
    
    
    return dados

def get_historico_gastos(termo=""):
    conn = get_connection()
    # Retiramos o agrupamento matemático para espelhar a verdade do banco
    query = '''
        SELECT 
               h.id AS "ID_Transacao",
               p.id AS "ID_Produto",
               h.data AS "Data", 
               h.funcionario AS "Vendedor",
               p.nome AS "Produto", 
               h.quantidade AS "Qtd", 
               h.preco_vendido AS "Preço (R$)"
        FROM historico_gastos h
        JOIN produtos p ON h.produto_id = p.id
    '''
    params = []
    if termo:
        query += " WHERE p.nome ILIKE %s OR h.data ILIKE %s"
        params.extend([f'%{termo}%', f'%{termo}%'])
        
    query += " ORDER BY h.data DESC"
    
    df = pd.read_sql_query(query, conn, params=params)

    return df

def atualizar_historico_com_delta(id_transacao, id_produto, nova_qtd, qtd_antiga, novo_preco, novo_vendedor):
    """Motor de equilíbrio: Atualiza o registro e compensa o inventário automaticamente."""
    delta = nova_qtd - qtd_antiga
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Reescreve o passado
    cursor.execute('''
        UPDATE historico_gastos 
        SET quantidade = %s, preco_vendido = %s, funcionario = %s
        WHERE id = %s
    ''', (nova_qtd, novo_preco, novo_vendedor, id_transacao))
    
    # 2. Reajusta a física do estoque
    # Se delta for positivo (vendeu mais), subtrai mais do estoque.
    # Se delta for negativo (vendeu menos/estorno), a subtração de um negativo soma ao estoque.
    cursor.execute('''
        UPDATE produtos 
        SET estoque_atual = estoque_atual - %s, 
            estoque_geral = estoque_geral - %s 
        WHERE id = %s
    ''', (delta, delta, id_produto))
    
    conn.commit()

def get_faturamento(data_inicio):
    conn = get_connection()
    query = '''
        SELECT p.nome AS "Produto", 
               CAST(SUM(h.quantidade) AS INTEGER) AS "Qtd_Vendida", 
               SUM(h.quantidade * h.preco_vendido) AS "Total_R$"
        FROM historico_gastos h
        JOIN produtos p ON h.produto_id = p.id
        WHERE h.data >= %s
        GROUP BY p.nome
        ORDER BY "Total_R$" DESC
    '''
    df = pd.read_sql_query(query, conn, params=[data_inicio])
    
    return df

def atualizar_produto_pela_tabela(id_produto, nome, estoque_atual, minimo, preco, estoque_geral):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE produtos 
        SET nome = %s, estoque_atual = %s, estoque_minimo = %s, preco_venda = %s, estoque_geral = %s
        WHERE id = %s
    ''', (nome, estoque_atual, minimo, preco, estoque_geral, id_produto))
    conn.commit()
    
    