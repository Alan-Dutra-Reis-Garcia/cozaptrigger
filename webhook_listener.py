from fastapi import FastAPI, Request, BackgroundTasks
from google.cloud import firestore
from google.oauth2 import service_account
import os
import time
import json

app = FastAPI(title="CoZapTrigger - Webhook Listener")

# 🔑 Inicialização inteligente (Variável na nuvem / Arquivo local)
if "FIREBASE_KEY_JSON" in os.environ:
    cred_dados = json.loads(os.environ.get("FIREBASE_KEY_JSON"))
    credenciais = service_account.Credentials.from_service_account_info(cred_dados)
    db = firestore.Client(credentials=credenciais, project=credenciais.project_id)
    print("🟢 [Firebase Webhook] Conectado via Variável de Ambiente!")
else:
    NOME_ARQUIVO_CHAVE = "firebase_key.json"
    if os.path.exists(NOME_ARQUIVO_CHAVE):
        credenciais = service_account.Credentials.from_service_account_file(NOME_ARQUIVO_CHAVE)
        db = firestore.Client(credentials=credenciais, project=credenciais.project_id)
        print("🟢 [Firebase Webhook] Conectado via arquivo local!")
    else:
        db = firestore.Client()

def atualizar_status_firebase(wpp_id: str, novo_status: str, data_leitura: str = None):
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
            print(f"🔥 [Firebase] Lead {doc.id} atualizado para: {novo_status}")
            
        if not encontrou:
            print(f"⚠️ [Firebase] ID {wpp_id} não encontrado no banco.")
    except Exception as e:
        print(f"❌ Erro ao atualizar status: {e}")

def registrar_resposta_firebase(wpp_id: str, texto_resposta: str, horario_resposta: str, telefone_cliente: str = None):
    try:
        leads_ref = db.collection("historico_disparos")
        doc_alvo_id = None
        
        if wpp_id:
            query = leads_ref.where("wpp_message_id", "==", wpp_id).limit(1).stream()
            for doc in query:
                doc_alvo_id = doc.id
                break
                
        if not doc_alvo_id and telefone_cliente:
            query_tel = leads_ref.where("telefone", "==", telefone_cliente).limit(1).stream()
            for doc in query_tel:
                doc_alvo_id = doc.id
                break

        if doc_alvo_id:
            leads_ref.document(doc_alvo_id).update({
                "respondido": True,
                "data_resposta": horario_resposta,
                "conteudo_resposta": texto_resposta
            })
            print(f"💬 [Firebase] Resposta gravada para o lead: {doc_alvo_id}")
        else:
            print(f"⚠️ [Firebase] Nenhum lead achado para ID {wpp_id} ou Tel {telefone_cliente}")
            
    except Exception as e:
        print(f"❌ Erro ao registrar resposta: {e}")

@app.post("/webhook")
async def receber_evento_evolution(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        evento_original = payload.get("event", "")
        data = payload.get("data", {})
        
        # 🔍 LOG MÁGICO: Mostra no Railway exatamente o que está chegando da Evolution
        print(f"📥 [Webhook] Evento Recebido: '{evento_original}'")
        
        # Normaliza o evento para minúsculo e padroniza os pontos (ex: MESSAGES_UPDATE -> messages.update)
        evento = evento_original.lower().replace("_", ".")
        
        # 1. CAPTURA MUDANÇAS DE STATUS (ENTREGUE / LIDO)
        if evento == "messages.update":
            wpp_id = data.get("key", {}).get("id")
            status = data.get("status")
            print(f"   -> Status da mensagem {wpp_id}: {status}")
            
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
                remote_jid = data.get("key", {}).get("remoteJid", "")
                telefone_cliente = remote_jid.split("@")[0] if "@" in remote_jid else ""
                
                wpp_id_contexto = data.get("message", {}).get("extendedTextMessage", {}).get("contextInfo", {}).get("stanzaId")
                
                texto_cliente = data.get("message", {}).get("conversation") or \
                                data.get("message", {}).get("extendedTextMessage", {}).get("text", "")
                
                horario_resposta = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"   -> Cliente {telefone_cliente} digitou: '{texto_cliente}'")
                
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
        print(f"💥 Erro crítico no processamento do webhook: {e}")
        return {"status": "error", "message": str(e)}