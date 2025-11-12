import os
import sys
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, errors
from bson import ObjectId

# Tenta carregar variáveis de ambiente de um arquivo .env (para desenvolvimento local)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Arquivo .env carregado (se existente).")
except ImportError:
    print("python-dotenv não instalado, carregando variáveis do ambiente.")

# --- Configuração ---
app = Flask(__name__)
# Habilita CORS para permitir que o frontend (rodando em outra origem) acesse a API
CORS(app) 

# --- Leitura Segura da String de Conexão ---
# O Render definirá esta variável de ambiente. Para testes locais, use um arquivo .env
MONGO_CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING", None)
DB_NAME = "mestrado_anotacao" # O nome do seu banco de dados

# --- Verificação Crítica da Conexão ---
if MONGO_CONNECTION_STRING is None or "<usuario>" in MONGO_CONNECTION_STRING:
    print("\nERRO FATAL: A string de conexão do MongoDB (MONGO_CONNECTION_STRING) não foi configurada.")
    print("Configure a variável de ambiente ou um arquivo .env.")
    sys.exit(1) # Impede a aplicação de iniciar sem a conexão

# --- Conexão com o MongoDB ---
try:
    print("Iniciando conexão com MongoDB Atlas...")
    client = MongoClient(MONGO_CONNECTION_STRING, serverSelectionTimeoutMS=10000) # Timeout de 10s
    # Testa a conexão ao iniciar
    client.admin.command('ping') 
    db = client[DB_NAME] # Acessa o banco de dados
    col_mapeamento = db["especialistas_mapeados"] # Coleção para mapear nome -> ID
    print("Conexão com MongoDB estabelecida com sucesso!")
except errors.ConnectionFailure as e:
    print(f"\nERRO FATAL: Falha ao conectar ao MongoDB: {e}")
    print("Verifique a string de conexão, regras de IP no Atlas e conectividade de rede.")
    sys.exit(1)
except Exception as e:
     print(f"\nERRO FATAL inesperado na conexão com MongoDB: {e}")
     sys.exit(1)


# --- Constantes ---
# Nomes das coleções conforme a estrutura do seu banco
VALID_COLLECTIONS = [
    "bc_para_anotar",
    "camara_para_anotar",
    "cgu_para_anotar",
    "ibge_para_anotar",
    "senado_para_anotar",
    "tse_para_anotar"
]
# IDs fixos que TENTAREMOS usar primeiro (conforme dados carregados)
PREDEFINED_SPECIALIST_IDS = ["especialista01", "especialista02", "especialista03"]

# --- Função Auxiliar ---
def normalize_name(name):
    """Gera um ID sugerido a partir do nome (lowercase, sem acentos, sem espaços)."""
    if not name: return None
    name = name.lower()
    # Tenta remover acentos de forma simples (pode precisar de 'unidecode' para cobertura total)
    name = re.sub(r'[áàâã]', 'a', name)
    name = re.sub(r'[éèê]', 'e', name)
    name = re.sub(r'[íìî]', 'i', name)
    name = re.sub(r'[óòôõ]', 'o', name)
    name = re.sub(r'[úùû]', 'u', name)
    name = re.sub(r'[ç]', 'c', name)
    # Substitui espaços e múltiplos caracteres não-alfanuméricos por _
    name = re.sub(r'[\s\W]+', '_', name) 
    return name.strip('_') # Remove underscores no início/fim

# --- Endpoints da API ---

@app.route("/listar_especialistas", methods=["GET"])
def listar_especialistas():
    """Retorna a lista de nomes já registrados."""
    try:
        nomes = [doc["nome_digitado"] for doc in col_mapeamento.find({}, {"nome_digitado": 1, "_id": 0})]
        # Retorna uma lista de nomes únicos, ordenada
        return jsonify(sorted(list(set(nomes)))), 200
    except Exception as e:
        print(f"Erro ao listar especialistas: {e}")
        return jsonify({"message": "Erro ao buscar lista de especialistas."}), 500

@app.route("/obter_id_fixo", methods=["POST"])
def obter_id_fixo():
    """
    Obtém ou registra um especialista e retorna seu ID fixo.
    Primeiro, tenta usar um dos IDs pré-definidos (01, 02, 03).
    Se estiverem ocupados, gera um ID dinâmico a partir do nome.
    """
    data = request.json
    nome_digitado = data.get("nome_digitado")

    if not nome_digitado:
        return jsonify({"message": "Nome do especialista não fornecido"}), 400

    try:
        # 1. Verifica se o nome já existe
        mapeamento_existente = col_mapeamento.find_one({"nome_digitado": nome_digitado})
        if mapeamento_existente:
            print(f"Especialista '{nome_digitado}' já registrado com ID '{mapeamento_existente['id_fixo']}'.")
            return jsonify({"id_fixo": mapeamento_existente["id_fixo"]}), 200
        else:
            # 2. Nome não existe. Tenta encontrar um ID pré-definido livre
            ids_usados = {doc["id_fixo"] for doc in col_mapeamento.find({}, {"id_fixo": 1, "_id": 0})}
            id_final = None
            for pid in PREDEFINED_SPECIALIST_IDS:
                if pid not in ids_usados:
                    id_final = pid
                    break

            if not id_final:
                # 3. Todos os IDs pré-definidos estão ocupados. Gera um ID dinâmico (normalizado)
                id_normalizado = normalize_name(nome_digitado)
                if not id_normalizado:
                     return jsonify({"message": "Nome inválido para gerar ID"}), 400
                 
                id_final = id_normalizado
                # Lógica de desambiguação: se o ID normalizado já existir (colisão), adiciona sufixo
                count = 1
                while id_final in ids_usados:
                     id_final = f"{id_normalizado}_{count}"
                     count += 1
                
                if id_final != id_normalizado:
                    print(f"Colisão detectada para ID '{id_normalizado}', usando '{id_final}'")

            # 4. Registra o novo especialista com o ID encontrado (fixo ou dinâmico)
            novo_mapeamento = {"nome_digitado": nome_digitado, "id_fixo": id_final}
            col_mapeamento.insert_one(novo_mapeamento)
            print(f"Novo especialista '{nome_digitado}' registrado com ID '{id_final}'.")
            return jsonify({"id_fixo": id_final}), 201 # 201 Created

    except Exception as e:
        print(f"Erro ao obter/registrar ID para '{nome_digitado}': {e}")
        return jsonify({"message": "Erro interno ao processar identificação do especialista."}), 500


@app.route("/next_item", methods=["GET"])
def get_next_item():
    """
    Busca o próximo item pendente para um especialista (ID fixo ou dinâmico).
    Primeiro, procura por itens onde o especialista já existe no array mas não anotou (slots pré-definidos).
    Segundo, procura por itens onde o especialista ainda não existe no array (novos especialistas ou itens não pré-preenchidos).
    """
    collection_name = request.args.get("collection_name")
    specialist_id = request.args.get("specialist_id") # Recebe o ID (ex: "especialista01" ou "joao_silva")

    if not collection_name or collection_name not in VALID_COLLECTIONS:
        return jsonify({"message": "Nome da coleção inválido ou não fornecido"}), 400
    if not specialist_id:
        return jsonify({"message": "ID do especialista inválido ou não fornecido"}), 400

    try:
        collection = db[collection_name]

        # Estratégia de busca 1: Procura item onde o slot do especialista existe mas está nulo
        item = collection.find_one({
            "anotacoes_especialistas": {
                "$elemMatch": {
                    "id_especialista": specialist_id,
                    "escolha_final": None
                }
            }
        })

        if not item:
            # Estratégia de busca 2: Se não achou (pode ser um especialista dinâmico),
            # procura item onde o ID do especialista NÃO EXISTE no array
            item = collection.find_one({
                "anotacoes_especialistas.id_especialista": { "$ne": specialist_id }
            })

        # Processa o resultado da busca
        if item:
            item['_id'] = str(item['_id'])
            item['collection_name'] = collection_name
            return jsonify(item), 200
        else:
            # Se ambas as buscas falharam, ele realmente terminou ou não está nos dados
             total_items = collection.count_documents({})
             items_where_specialist_exists = collection.count_documents({"anotacoes_especialistas.id_especialista": specialist_id})

             if items_where_specialist_exists > 0 or total_items == 0:
                 print(f"Nenhum item pendente encontrado para {specialist_id} em {collection_name}. Total: {total_items}, Existente em: {items_where_specialist_exists}")
                 return jsonify({"message": f"Nenhum item pendente para '{specialist_id}' na coleção '{collection_name}'. Parabéns!"}), 404
             else:
                  # Isso não deveria acontecer se a carga inicial foi feita com os 3 slots
                  print(f"AVISO: ID '{specialist_id}' não encontrado em NENHUM documento da coleção '{collection_name}'. Isso é inesperado para os IDs pré-definidos.")
                  # Para um especialista dinâmico, isso pode significar que ele terminou (pois $ne não achou nada)
                  return jsonify({"message": f"Nenhum item pendente para '{specialist_id}' na coleção '{collection_name}'. Parabéns!"}), 404

    except Exception as e:
        print(f"Erro ao buscar próximo item para {specialist_id} na coleção {collection_name}: {e}")
        return jsonify({"message": "Erro interno ao buscar próximo item."}), 500


@app.route("/annotate", methods=["POST"])
def annotate_item():
    """
    Salva a anotação. Tenta ATUALIZAR um slot existente primeiro.
    Se falhar, ADICIONA (PUSH) um novo objeto para o especialista.
    """
    data = request.json
    collection_name = data.get("collection_name")
    item_id = data.get("item_id")
    specialist_id = data.get("specialist_id") # Recebe o ID (ex: "especialista01" ou "joao_silva")
    escolha = data.get("escolha")

    if not all([collection_name, item_id, specialist_id, escolha]):
         return jsonify({"success": False, "message": "Dados incompletos para anotação"}), 400
    if collection_name not in VALID_COLLECTIONS:
         return jsonify({"success": False, "message": "Nome da coleção inválido"}), 400
    if not specialist_id:
         return jsonify({"success": False, "message": "ID de especialista inválido"}), 400

    try:
        collection = db[collection_name]

        # 1. Tenta ATUALIZAR (cobre os slots pré-definidos e correções)
        result_update = collection.update_one(
            # Filtro: encontra o documento pelo _id E o objeto do especialista dentro do array
            { "_id": item_id, "anotacoes_especialistas.id_especialista": specialist_id },
            # Atualização: define o valor de escolha_final para aquele objeto encontrado
            { "$set": { "anotacoes_especialistas.$.escolha_final": escolha } }
        )

        if result_update.matched_count > 0:
            if result_update.modified_count > 0:
                 print(f"Anotação ATUALIZADA: Coleção '{collection_name}', Item ID {item_id}, Especialista '{specialist_id}', Escolha: {escolha}")
                 return jsonify({"success": True, "message": "Anotação atualizada com sucesso"}), 200
            else:
                 print(f"Anotação REPETIDA (sem alteração): Coleção '{collection_name}', Item ID {item_id}, Especialista '{specialist_id}', Escolha: {escolha}")
                 return jsonify({"success": True, "message": "Anotação já estava salva com este valor"}), 200
        else:
            # 2. Não encontrou para atualizar. Tenta ADICIONAR (cobre especialistas > 3 ou slots não criados)
            result_push = collection.update_one(
                { "_id": item_id }, # Apenas garante que o item existe
                # Adiciona o objeto do especialista ao array 'anotacoes_especialistas'
                # $push só adiciona se o $elemMatch falhou, prevenindo duplicatas (embora a lógica de $ne no next_item devesse cuidar disso)
                { "$push": { "anotacoes_especialistas": { "id_especialista": specialist_id, "escolha_final": escolha } } }
            )

            if result_push.modified_count > 0:
                 print(f"Anotação ADICIONADA: Coleção '{collection_name}', Item ID {item_id}, Especialista '{specialist_id}', Escolha: {escolha}")
                 return jsonify({"success": True, "message": "Anotação salva com sucesso"}), 200
            else:
                 # Se nem o push funcionou, o item_id provavelmente não existe
                 print(f"ERRO: Item com ID '{item_id}' não encontrado na coleção '{collection_name}' para adicionar anotação.")
                 return jsonify({"success": False, "message": f"Item com ID '{item_id}' não encontrado na coleção '{collection_name}'."}), 404

    except Exception as e:
        print(f"Erro ao salvar anotação para item {item_id} por {specialist_id} na coleção {collection_name}: {e}")
        return jsonify({"success": False, "message": "Erro interno ao salvar anotação."}), 500

# --- Ponto de Entrada ---
if __name__ == "__main__":
    # O Render definirá a variável PORT. Para local, usa 5000.
    port = int(os.environ.get("PORT", 5000)) 
    # debug=True é ótimo para desenvolvimento, mas para produção no Render
    # o Gunicorn (do Procfile) assumirá.
    app.run(host='0.0.0.0', port=port, debug=True)