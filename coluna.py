import psycopg2
import streamlit as st

produtos_reais = [
    ("Vinho", 0, 0, 70), ("Toalhas", 20, 0, 7), ("Snickers", 13, 0, 8),
    ("Skol", 24, 0, 6), ("Shampoo", 5, 0, 20), ("Schweppes Citrus", 12, 0, 8),
    ("Sabonete", 25, 0, 7), ("Nissin Lámen", 6, 0, 8), ("Maisena", 5, 0, 8),
    ("Kit Kat", 7, 0, 8), ("Heineken", 16, 0, 10), ("Halls", 23, 0, 3),
    ("Guarda Chuva", 3, 0, 0), ("Guaraná", 14, 0, 6), ("Fanta Uva", 12, 0, 6),
    ("Fanta Laranja", 12, 0, 6), ("Escova de Dente", 9, 0, 10),
    ("Energético Red Bull", 13, 0, 16), ("Duplo Malte", 21, 0, 9),
    ("Cup Noodles", 5, 0, 13), ("Creme Dental", 14, 0, 10),
    ("Cookies Nestle", 1, 0, 8), ("Coca Cola", 16, 0, 6),
    ("Club Social", 16, 0, 3), ("Cápsula de café", 11, 0, 8),
    ("Bis", 10, 0, 7), ("Bauducco", 9, 0, 6), ("Amendoim", 3, 0, 8),
    ("Água sem gás", 45, 0, 5), ("Água com gás", 11, 0, 6)
]

historico_real = [
    ("2026-05-29 08:21:20", "Ezekiel", "Maisena", 1, 8.00),
    ("2026-05-28 20:01:20", "Ezekiel", "Heineken", 1, 10.00),
    ("2026-05-28 19:32:04", "Daniel", "Heineken", 2, 10.00),
    ("2026-05-28 19:09:10", "Daniel", "Nissin Lámen", 2, 8.00),
    ("2026-05-28 19:08:51", "Daniel", "Heineken", 2, 10.00),
    ("2026-05-28 17:55:26", "Daniel", "Coca Cola", 1, 6.00),
    ("2026-05-29 15:15:16",	"Thaís", "Cápsula de café", 1, 8.00)
]

def popular_banco():
    # Conecta no Supabase usando a url configurada no .streamlit/secrets.toml
    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
    cursor = conn.cursor()

    # 1. Limpar as tabelas e resetar os IDs no PostgreSQL
    cursor.execute("TRUNCATE TABLE historico_gastos, produtos RESTART IDENTITY CASCADE;")

    # 2. Inserir Produtos
    for nome, atual, minimo, preco in produtos_reais:
        cursor.execute('''
            INSERT INTO produtos (nome, estoque_atual, estoque_geral, estoque_minimo, preco_venda) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (nome, atual, atual, minimo, preco))

    # 3. Pegar os IDs gerados para cruzar com o histórico
    cursor.execute("SELECT id, nome FROM produtos")
    mapa_ids = {linha[1]: linha[0] for linha in cursor.fetchall()}

    # 4. Inserir Histórico
    for data, func, nome_prod, qtd, preco_unit in historico_real:
        prod_id = mapa_ids.get(nome_prod)
        if prod_id:
            cursor.execute('''
                INSERT INTO historico_gastos (produto_id, data, quantidade, tipo_dia, preco_vendido, funcionario)
                VALUES (%s, %s, %s, 'util', %s, %s)
            ''', (prod_id, data, qtd, preco_unit, func))

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Banco Supabase populado com os dados reais perfeitamente!")

if __name__ == "__main__":
    popular_banco()