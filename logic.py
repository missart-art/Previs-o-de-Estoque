from datetime import datetime, timedelta
from config import FERIADOS
from database import get_connection

def get_tipo_dia(dt):
    """
    Classifica o dia como 'pico' (feriados e finais de semana a partir de sexta) 
    ou 'util'.
    """
    # Verifica se a data está na lista de feriados do config.py
    if dt.strftime("%Y-%m-%d") in FERIADOS or dt.weekday() >= 4:
        return "pico"
    return "util"

def calcular_medias(nome_produto):
    """
    Calcula a média de consumo dos últimos 30 registros de cada tipo 
    diretamente do SQL (PostgreSQL).
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    medias = {"util": 0, "pico": 0}
    
    for tipo in ["util", "pico"]:
        # Trocado '?' por '%s' para PostgreSQL e adicionado 'AS subquery' no final
        cursor.execute('''
            SELECT AVG(quantidade) FROM (
                SELECT quantidade FROM historico_gastos h
                JOIN produtos p ON h.produto_id = p.id
                WHERE p.nome = %s AND h.tipo_dia = %s
                ORDER BY h.data DESC LIMIT 30
            ) AS subquery
        ''', (nome_produto, tipo))
        res = cursor.fetchone()[0]
        # Converte para float caso o resultado seja um Decimal do Postgres
        medias[tipo] = float(res) if res else 0
        
    return medias

def simular_duracao(nome_produto, estoque_atual):
    """
    Simula o gasto diário futuro para prever a data de esgotamento.
    """
    if estoque_atual <= 0: 
        return 0, "Esgotado"
    
    medias = calcular_medias(nome_produto)
    m_util = medias["util"]
    m_pico = medias["pico"]
    
    # Se não houver dados históricos, não há como prever
    if m_util == 0 and m_pico == 0: 
        return "N/A", "Sem dados"

    dias = 0
    dt_simulada = datetime.now()
    estoque = estoque_atual
    
    # Loop de simulação: subtrai o gasto médio dia após dia
    while estoque > 0 and dias < 365:
        tipo = get_tipo_dia(dt_simulada)
        gasto = m_pico if tipo == "pico" else m_util
        estoque -= gasto
        dias += 1
        dt_simulada += timedelta(days=1)

        if estoque <= 0: 
            break
            
    return dias, dt_simulada.strftime("%d/%m/%Y")