from fastapi import FastAPI, Request, BackgroundTasks
from google.cloud import firestore
from google.oauth2 import service_account
import os
import time

app = FastAPI(title="CoZapTrigger - Webhook Listener")

# 🔑 Inicialização explícita usando o arquivo de chaves atualizado
NOME_ARQUIVO_CHAVE = "firebase_key.json"

if os.path.exists(NOME_ARQUIVO_CHAVE):
    credenciais = service_account.Credentials.from_service_account_file(NOME_ARQUIVO_CHAVE)
    db = firestore.Client(credentials=credenciais, project=credenciais.project_id)
    print("🟢 [Firebase Webhook] Conectado com sucesso usando o arquivo local!")
else:
    db = firestore.Client()
    print("⚠️ [Firebase Webhook] Arquivo de chave não encontrado, tentando credenciais padrão.")

def atualizar_status_firebase(wpp_id: str, novo_status: str, data_leitura: str = None):
    """Busca o documento pelo ID da mensagem do WhatsApp e atualiza o status (ENTREGUE/LIDO)"""
    try:
        leads_ref = db.collection("historico_disparos")
        query = leads_ref.where("wpp_message_id", "==", wpp_id).limit(1).stream()
        
        encontrou = False
        for doc in query:
            encontrou = True
            dados_atualizacao = {"status_envio": novo_status}
            if data_leitura:
                dados_atualizacao["data_leitura"] = data_leitura
                
            leads_ref.document(doc.id).update(dados_atualizacao)
            print(f"🔥 [Webhook -> Firebase] Lead {doc.id} atualizado para status: {novo_status}")
            
        if not encontrou:
            print(f"⚠️ [Webhook] ID de mensagem {wpp_id} não encontrado no banco para atualizar status.")
    except Exception as e:
        print(f"❌ Erro ao atualizar status no Firebase: {e}")

def registrar_resposta_firebase(wpp_id: str, texto_resposta: str, horario_resposta: str, telefone_cliente: str = None):
    """Registra o retorno do cliente buscando por ID de mensagem ou por Telefone (Fallback)"""
    try:
        leads_ref = db.collection("historico_disparos")
        doc_alvo_id = None
        
        # Tentativa 1: Buscar pelo ID da mensagem vinculada (se houver)
        if wpp_id:
            query = leads_ref.where("wpp_message_id", "==", wpp_id).limit(1).stream()
            for doc in query:
                doc_alvo_id = doc.id
                break
                
        # Tentativa 2: Se não achou pelo ID, busca pelo telefone limpo do cliente
        if not doc_alvo_id and telefone_cliente:
            print(f"🔍 ID de mensagem não vinculado. Buscando lead pelo telefone: {telefone_cliente}")
            query_tel = leads_ref.where("telefone", "==", telefone_cliente).limit(1).stream()
            for doc in query_tel:
                doc_alvo_id = doc.id
                break

        # Se encontrou o lead por qualquer um dos caminhos, atualiza os campos de resposta
        if doc_alvo_id:
            leads_ref.document(doc_alvo_id).update({
                "respondido": True,
                "data_resposta": horario_resposta,
                "conteudo_resposta": texto_resposta
            })
            print(f"💬 [Webhook -> Firebase] Resposta gravada com sucesso para o lead CPF: {doc_alvo_id}")
        else:
            print(f"⚠️ [Webhook] Não foi possível encontrar nenhum lead com o ID {wpp_id} ou Telefone {telefone_cliente} para registrar a resposta.")
            
    except Exception as e:
        print(f"❌ Erro ao registrar resposta no Firebase: {e}")

@app.post("/webhook")
async def receber_evento_evolution(request: Request, background_tasks: BackgroundTasks):
    """Ponto de entrada que recebe as notificações em tempo real da Evolution API"""
    try:
        payload = await request.json()
        evento = payload.get("event")
        data = payload.get("data", {})
        
        # 1. CAPTURA MUDANÇAS DE STATUS (ENTREGUE / LIDO)
        if evento == "messages.update":
            wpp_id = data.get("key", {}).get("id")
            status = data.get("status") # DELIVRD ou READ
            
            if wpp_id:
                if status == "READ":
                    horario_atual = time.strftime("%Y-%m-%d %H:%M:%S")
                    background_tasks.add_task(atualizar_status_firebase, wpp_id, "LIDO", horario_atual)
                elif status == "DELIVRD":
                    background_tasks.add_task(atualizar_status_firebase, wpp_id, "ENTREGUE")

        # 2. CAPTURA SE O CLIENTE RESPONDEU
        elif evento == "messages.upsert":
            from_me = data.get("key", {}).get("fromMe", False)
            
            if not from_me:
                # Captura o telefone de quem enviou e limpa o sufixo do WhatsApp
                remote_jid = data.get("key", {}).get("remoteJid", "")
                telefone_cliente = remote_jid.split("@")[0] if "@" in remote_jid else ""
                
                # ID da mensagem que ele respondeu (se houver citação direta)
                wpp_id_contexto = data.get("message", {}).get("extendedTextMessage", {}).get("contextInfo", {}).get("stanzaId")
                
                # Texto digitado pelo cliente
                texto_cliente = data.get("message", {}).get("conversation") or \
                                data.get("message", {}).get("extendedTextMessage", {}).get("text", "")
                
                horario_resposta = time.strftime("%Y-%m-%d %H:%M:%S")
                
                if texto_cliente:
                    background_tasks.add_task(
                        registrar_resposta_firebase, 
                        wpp_id_contexto, 
                        texto_cliente, 
                        horario_resposta, 
                        telefone_cliente
                    )
                    
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}