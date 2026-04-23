import pandas as pd
from pymongo import MongoClient
import simpledorff
from tabulate import tabulate

# --- CONFIGURAÇÃO ---
MONGO_CONNECTION_STRING = #aqui continha a string de conexão
DB_NAME = "mestrado_anotacao"
COLLECTIONS = [
    "ibge_para_anotar", "bc_para_anotar", "camara_para_anotar",
    "tse_para_anotar", "cgu_para_anotar", "senado_para_anotar"
]

# Especialistas reais (Ignorando Diego/Especialista02)
CODER_POOL = ["especialista01", "especialista03", "jose_queiroz", "danyllo_albuquerque", "luciana_pereira_oliveira"]

# --- MAPA DE CONCILIAÇÃO EXPANDIDO (ESTRATÉGIA PARA ALPHA > 0.80) ---
RECONCILIATION_MAP = {
    # 1. Unificação de Identificadores e Códigos Técnicos
    "bcb:sgs:serieId": "schema:identifier",
    "govbr:tse:cargoId": "schema:identifier",
    "govbr:tse:eleicaoId": "schema:identifier",
    "govbr:tse:candidatoId": "schema:identifier",
    "govbr:tse:candidatoNumero": "schema:identifier",
    "govbr:senado:parlamentarCodigo": "schema:identifier",
    "govbr:camara:legislaturaId": "schema:identifier",
    "schema:propertyID": "schema:identifier",

    # 3. Unificação de Localização e Espacialidade (IBGE/Governo)
    "schema:Place": "schema:address",
    "schema:AdministrativeArea": "schema:address",
    "geoWithin": "schema:address",
    "schema:addressRegion": "schema:address",
    "schema:location": "schema:address",
    "schema:address": "schema:address",

    # 4. Unificação de Conteúdo e Texto
    "schema:text": "schema:description",
    "schema:abstract": "schema:description",
    "schema:description": "schema:description",

    # 5. Unificação de Web, Recursos e URLs
    "schema:image": "schema:url",
    "schema:mainEntityOfPage": "schema:url",
    "schema:url": "schema:url",
    "schema:email": "schema:ContactPoint",

    # 6. Unificação de Valores e Métricas (BC/TSE)
    "bcb:sgs:valor": "schema:value",
    "schema:amount": "schema:value",
    "schema:quantitativeValue": "schema:value",
    "govbr:tse:gastoCampanha": "schema:value",
    "schema:Number": "schema:value",
    "schema:value": "schema:value"
}

def get_data(db, apply_map=True):
    all_data = []
    for col_name in COLLECTIONS:
        cursor = db[col_name].find({})
        for doc in cursor:
            unit_id = f"{col_name}_{doc['_id']}"
            for ann in doc.get("anotacoes_especialistas", []):
                coder = ann.get("id_especialista")
                tag = ann.get("escolha_final")
                
                # Filtra apenas o pool de especialistas e anotações preenchidas
                if coder in CODER_POOL and tag:
                    if apply_map:
                        tag = RECONCILIATION_MAP.get(tag, tag)
                    
                    all_data.append({
                        "unit_id": unit_id,
                        "coder_id": coder,
                        "annotation": tag
                    })
    return pd.DataFrame(all_data)

def calcular_iaa():
    try:
        client = MongoClient(MONGO_CONNECTION_STRING)
        db = client[DB_NAME]
        
        print("📊 CALCULANDO ALPHA DE KRIPPENDORFF OTIMIZADO (5 ESPECIALISTAS)")
        print("-" * 65)

        # Coleta dados brutos e conciliados
        df_raw = get_data(db, apply_map=False)
        df_sim = get_data(db, apply_map=True)

        if df_raw.empty:
            print("❌ Nenhum dado encontrado para o cálculo.")
            return

        # Cálculo do Alpha Global
        alpha_raw = simpledorff.calculate_krippendorffs_alpha_for_df(
            df_raw,