import sqlite3
import random
from datetime import datetime, timedelta
import os
from database import init_db, get_connection

def popular_dados():
    init_db()
    
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM historico_gastos")
    cursor.execute("DELETE FROM produtos")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='produtos'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='historico_gastos'")
    
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

    cursor.execute("SELECT id, preco_venda FROM produtos")
    produtos_ids = cursor.fetchall()

    funcionarios = ["João", "Maria", "Carlos", "Ana"]
    tipos_dia = ["util", "util", "util", "pico", "pico"] 

    historico_dados = []
    
    for i in range(150): 
        prod = random.choice(produtos_ids)
        prod_id = prod[0]
        preco_na_epoca = prod[1] 
        
        if random.random() < 0.2:
            preco_na_epoca = round(preco_na_epoca * 0.8, 2)
            
        qtd = random.randint(1, 5)
        func = random.choice(funcionarios)
        tipo = random.choice(tipos_dia)
        
        dias_atras = random.randint(0, 30)
        horas_atras = random.randint(0, 23)
        minutos_atras = random.randint(0, 59)
        data_venda = (datetime.now() - timedelta(days=dias_atras, hours=horas_atras, minutes=minutos_atras)).strftime("%Y-%m-%d %H:%M:%S")
        
        comprovante = None
        if random.random() < 0.3:
            comprovante = f"temp/comp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}.jpg"

        historico_dados.append((prod_id, data_venda, qtd, tipo, preco_na_epoca, func, comprovante))

    cursor.executemany('''
        INSERT INTO historico_gastos (produto_id, data, quantidade, tipo_dia, preco_vendido, funcionario, comprovante)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', historico_dados)

    conn.commit()
    conn.close()
    print("✅ Banco de dados repovoado com sucesso!")

if __name__ == "__main__":
    popular_dados()