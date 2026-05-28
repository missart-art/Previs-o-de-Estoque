import sqlite3
import os

DB_PATH = "interno/hostel_estoque.db"

def get_connection():
    """Cria a pasta interna se não existir e conecta ao SQLite[cite: 8]."""
    if not os.path.exists("interno"):
        os.makedirs("interno")
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    """Inicializa as tabelas do banco de dados."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de Produtos: Substitui o dicionário 'produtos' do JSON
    cursor.execute('''  
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            estoque_atual REAL DEFAULT 0,
            estoque_minimo REAL DEFAULT 0,
            preco_venda REAL DEFAULT 0.0
        )
    ''')
    
    # Tabela de Gastos: Substitui a lista 'logs' do JSON[cite: 6, 7]
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER,
            data TEXT NOT NULL,
            quantidade REAL NOT NULL,
            tipo_dia TEXT NOT NULL, -- 'util' ou 'pico',
            preco_vendido REAL DEFAULT 0.0,
            funcionario TEXT NOT NULL,
            comprovante TEXT,
            FOREIGN KEY (produto_id) REFERENCES produtos (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def upsert_produto(nome, estoque_min, preco_venda=0.0):
    """Adiciona ou atualiza as configurações e o preço de um produto."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO produtos (nome, estoque_minimo, preco_venda) 
        VALUES (?, ?, ?)
        ON CONFLICT(nome) DO UPDATE SET 
            estoque_minimo = excluded.estoque_minimo,
            preco_venda = excluded.preco_venda
    ''', (nome, estoque_min, preco_venda))
    conn.commit()
    conn.close()

def adicionar_estoque(nome, qtd):
    """Soma a quantidade ao estoque atual (Aba Reposição)[cite: 8]."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE produtos SET estoque_atual = estoque_atual + ? WHERE nome = ?', (qtd, nome))
    conn.commit()
    conn.close()

def registrar_consumo(nome, qtd, tipo_dia, funcionario, data=None, comprovante=None ):
    """Registra o gasto diário e subtrai do estoque (Aba Gasto Diário)[cite: 7, 8]."""
    if data is None:
        from datetime import datetime
        data = datetime.now().strftime("%Y-%m-%d")
        
    conn = get_connection()
    cursor = conn.cursor()
    # 1. Subtrai do estoque
    cursor.execute('UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE nome = ?', (qtd, nome))
    # 2. Salva no histórico para o cálculo das médias futuras[cite: 7]  
    cursor.execute('''
        INSERT INTO historico_gastos (produto_id, data, quantidade, tipo_dia, preco_vendido, funcionario, comprovante)
        SELECT id, ?, ?, ?, preco_venda, ?, ? FROM produtos WHERE nome = ?
    ''', (data, qtd, tipo_dia, funcionario, comprovante, nome))
    
    conn.commit()
    conn.close()

def get_dados_inventario():
    """Retorna todos os produtos para a tabela de inventário[cite: 8]."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome, estoque_atual, estoque_minimo, preco_venda FROM produtos')
    dados = cursor.fetchall()
    conn.close()
    return dados

def get_historico_gastos(termo=""):
    """Retorna o histórico somando quantidades da mesma data e produto[cite: 6, 7]."""
    conn = get_connection()
    # CAST e SUM garantem números inteiros e consolidação por dia[cite: 6]
    query = '''
        SELECT 
               h.data AS Data, 
               h.funcionario AS Vendedor,
               p.nome AS Produto, 
               CAST(SUM(h.quantidade) AS INTEGER) AS Qtd, 
               printf('R$ %.2f', SUM(h.quantidade * h.preco_vendido)) AS [Valor Total (R$)],
               h.comprovante AS Comprovante

        FROM historico_gastos h
        JOIN produtos p ON h.produto_id = p.id
    '''
    params = []
    if termo:
        query += " WHERE p.nome LIKE ? OR h.data LIKE ?"
        params.extend([f'%{termo}%', f'%{termo}%'])
        
    query += " GROUP BY h.data, p.nome, h.preco_vendido, h.funcionario, h.comprovante ORDER BY h.data DESC"    
    
    import pandas as pd
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_faturamento(data_inicio):
    """Retorna o faturamento agrupado por produto a partir de uma data."""
    conn = get_connection()
    query = '''
        SELECT p.nome AS Produto, 
               CAST(SUM(h.quantidade) AS INTEGER) AS Qtd_Vendida, 
               SUM(h.quantidade * h.preco_vendido) AS Total_R$
        FROM historico_gastos h
        JOIN produtos p ON h.produto_id = p.id
        WHERE h.data >= ?
        GROUP BY p.nome
        ORDER BY Total_R$ DESC
    '''
    import pandas as pd
    df = pd.read_sql_query(query, conn, params=[data_inicio])
    conn.close()
    return df
    
def atualizar_produto_pela_tabela(id_produto, nome, estoque, minimo, preco):
    """Atualiza todos os dados de um produto específico através do ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE produtos 
        SET nome = ?, estoque_atual = ?, estoque_minimo = ?, preco_venda = ?
        WHERE id = ?
    ''', (nome, estoque, minimo, preco, id_produto))
    conn.commit()
    conn.close()