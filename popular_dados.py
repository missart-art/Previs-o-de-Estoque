import sqlite3
import random
from datetime import datetime, timedelta
import os
from database import init_db, get_connection

def popular_dados():
    # 1. Garante que as tabelas existam e tenham as colunas novas
    init_db()
    
    conn = get_connection()
    cursor = conn.cursor()

    print("Limpando banco de dados...")
    cursor.execute("DELETE FROM historico_gastos")
    cursor.execute("DELETE FROM produtos")
    
    # Resetar o auto-incremento (opcional, mas deixa os IDs limpos)
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='produtos'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='historico_gastos'")
    
    # 2. Criar Produtos com Preços Fictícios
    print("Criando produtos...")
    produtos_mock = [
        ("Cerveja Heineken 330ml", 15.00, 120, 20),
        ("Água Mineral 500ml", 5.00, 50, 10),
        ("Refrigerante Cola 350ml", 7.50, 80, 15),
        ("Saladinha Pronta", 22.00, 15, 5),
        ("Chips Batata", 12.00, 30, 10)
    ]
    
    for nome, preco, estoque, minimo in produtos_mock:
        cursor.execute('''
            INSERT INTO produtos (nome, preco_venda, estoque_atual, estoque_minimo) 
            VALUES (?, ?, ?, ?)
        ''', (nome, preco, estoque, minimo))
    
    conn.commit()

    # Puxar os IDs criados para gerar o histórico
    cursor.execute("SELECT id, preco_venda FROM produtos")
    produtos_ids = cursor.fetchall()

    # 3. Gerar Histórico de Vendas (Últimos 30 dias)
    print("Gerando histórico de vendas...")
    funcionarios = ["João", "Maria", "Carlos", "Ana"]
    tipos_dia = ["util", "util", "util", "pico", "pico"] # Mais peso para dia útil na simulação

    historico_dados = []
    
    for _ in range(150): # 150 vendas aleatórias
        prod = random.choice(produtos_ids)
        prod_id = prod[0]
        preco_na_epoca = prod[1] # Pega o preço de venda para carimbar
        
        # Simula uma pequena inflação (20% das vezes o produto foi vendido mais barato no passado)
        if random.random() < 0.2:
            preco_na_epoca = round(preco_na_epoca * 0.8, 2)
            
        qtd = random.randint(1, 5)
        func = random.choice(funcionarios)
        tipo = random.choice(tipos_dia)
        
        # Gera uma data aleatória nos últimos 30 dias
        dias_atras = random.randint(0, 30)
        data_venda = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d")
        
        historico_dados.append((prod_id, data_venda, qtd, tipo, preco_na_epoca, func))

    # Inserção em lote para ser rápido
    cursor.executemany('''
        INSERT INTO historico_gastos (produto_id, data, quantidade, tipo_dia, preco_vendido, funcionario)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', historico_dados)

    conn.commit()
    conn.close()
    print("✅ Banco de dados repovoado com sucesso!")

if __name__ == "__main__":
    popular_dados()