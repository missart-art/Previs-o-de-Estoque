import sqlite3
import os

DB_PATH = "interno/hostel_estoque.db"

# Dados brutos do WhatsApp
dados_estoque_raw = """
COCA COLA		18	
GUARANA		14	
FANTA LARANJA		12	
FANTA UVA		12	
SCHWEPPES CITRUS		12	
HEINEKEN		21	
SKOL		24	
DUPLO MALTE		21	
ÁGUA SEM GÁS		35	
ÁGUA COM GÁS		11	
ENERGÉTICO		13	
KIT KAT		7	
BIS		10	
SNICKERS		13	
HALLS		23	
MAISENA		6	
COOKIES NESTLE		1	
CLUB SOCIAL		16	
BAUDUCCO		9	
CÁPSULA DE CAFÉ		11	
NISSIN LAMEN		8	
CUP NOODLES		5	
ÁGUA RECEPÇÃO		10	
VINHO		0	
SHAMPOO		5	
SABONETE		25	
CREME DENTAL		14	
ESCOVA DE DENTE		9	
GUARDA-CHUVA		3	
AMENDOIM		3
"""

dados_preco_raw = """
halls 3$
club social 3$
bauduco 6$
bis 7$
cookie 7$
kit kat 8$
maisena 8$
snickers 8$
amendoim 8$
nissim lamem 8$
m&m's 8$
cup noddles 13$
vinho 70$
agua sem gas 5$
agua com gas 6$
refrigerantes 7$
skol 8$
schewpps 8$
duplo malte 9$
heineken 10$
red bull/energetico 16$
sabonete 7$
toalha 7$
pasta de dente 10$
escova de dente 10$
shampoo 20$
"""

# Mapeamento para cruzar os nomes diferentes (Estoque -> Preço)
# Se o preço for genérico (ex: "refrigerantes"), a gente mapeia manualmente.
de_para_precos = {
    "COCA COLA": "refrigerantes",
    "GUARANA": "refrigerantes",
    "FANTA LARANJA": "refrigerantes",
    "FANTA UVA": "refrigerantes",
    "SCHWEPPES CITRUS": "schewpps",
    "HEINEKEN": "heineken",
    "SKOL": "skol",
    "DUPLO MALTE": "duplo malte",
    "ÁGUA SEM GÁS": "agua sem gas",
    "ÁGUA COM GÁS": "agua com gas",
    "ENERGÉTICO": "red bull/energetico",
    "KIT KAT": "kit kat",
    "BIS": "bis",
    "SNICKERS": "snickers",
    "HALLS": "halls",
    "MAISENA": "maisena",
    "COOKIES NESTLE": "cookie",
    "CLUB SOCIAL": "club social",
    "BAUDUCCO": "bauduco",
    "NISSIN LAMEN": "nissim lamem",
    "CUP NOODLES": "cup noddles",
    "VINHO": "vinho",
    "SHAMPOO": "shampoo",
    "SABONETE": "sabonete",
    "CREME DENTAL": "pasta de dente",
    "ESCOVA DE DENTE": "escova de dente",
    "AMENDOIM": "amendoim",
}

def processar_dados():
    # Extrair precos
    precos = {}
    for linha in dados_preco_raw.strip().split('\n'):
        if not linha.strip(): continue
        # separa pelo $, pega o número e o nome
        partes = linha.split('$')[0].strip().rsplit(' ', 1)
        if len(partes) == 2:
            nome_preco = partes[0].strip().lower()
            valor = float(partes[1])
            precos[nome_preco] = valor

    # Para os itens que só tem preço (como toalha, m&m's)
    precos["m&m's"] = 8.0
    precos["toalha"] = 7.0

    produtos_final = {}
    
    # Extrair estoque e cruzar com os preços
    for linha in dados_estoque_raw.strip().split('\n'):
        if not linha.strip(): continue
        # Separa por tabs/espaços longos
        partes = [p for p in linha.split('\t') if p.strip()]
        if len(partes) >= 2:
            nome_estoque = partes[0].strip()
            qtd = float(partes[1].strip())
            
            # Buscar o preço cruzando pelo dicionário
            chave_busca = de_para_precos.get(nome_estoque, "").lower()
            preco_final = precos.get(chave_busca, 0.0)
            
            produtos_final[nome_estoque] = {"estoque": qtd, "preco": preco_final}

    # Adicionar produtos que estão na lista de preços mas não na de estoque (zerados)
    produtos_final["M&M's"] = {"estoque": 0, "preco": 8.0}
    produtos_final["Toalha"] = {"estoque": 0, "preco": 7.0}

    # Injetar no Banco
    if not os.path.exists("interno"): os.makedirs("interno")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for nome, dados in produtos_final.items():
        cursor.execute('''
            INSERT INTO produtos (nome, estoque_atual, preco_venda, estoque_minimo) 
            VALUES (?, ?, ?, 5)
            ON CONFLICT(nome) DO UPDATE SET 
                estoque_atual = excluded.estoque_atual,
                preco_venda = excluded.preco_venda
        ''', (nome, dados["estoque"], dados["preco"]))

    conn.commit()
    conn.close()
    print(f"✅ {len(produtos_final)} produtos injetados com sucesso no banco de dados!")

if __name__ == "__main__":
    processar_dados()