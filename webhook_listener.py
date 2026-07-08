from fastapi import FastAPI, Request, BackgroundTasks
from google.cloud import firestore
from google.oauth2 import service_account
import os
import json

app = FastAPI(title="CoZapTrigger - Webhook Listener")

# 🔑 Inicialização explícita e à prova de falhas para o Railway usando a chave do arquivo
NOME_ARQUIVO_CHAVE = "firebase_key.json"

if os.path.exists(NOME_ARQUIVO_CHAVE):
    credenciais = service_account.Credentials.from_service_account_file(NOME_ARQUIVO_CHAVE)
    db = firestore.Client(credentials=credenciais, project=credenciais.project_id)
    print("🟢 [Firebase] Conectado com sucesso usando o arquivo local!")
else:
    # Caso o arquivo mude de nome, ele tenta puxar da variável de ambiente do Railway
    db = firestore.Client()
    print("⚠️ [Firebase] Arquivo de chave não encontrado, tentando credenciais padrão.")

def atualizar_status_firebase(wpp_id: str, novo_status: str, data_leitura: str = None):
    """Busca o documento pelo ID da mensagem do WhatsApp e atualiza o status"""
    try:
        leads_ref = db.collection("historico_disparos")
        # Busca o lead que possui aquele ID único do WhatsApp
        query = leads_ref.where("wpp_message_id", "==", wpp_id).limit(1).stream()
        
        for doc in query:
            dados_atualizacao = {"status_envio": novo_status}
            if data_leitura:
                dados_atualizacao["data_leitura"] = data_leitura
                
            leads_ref.document(doc.id).update(dados_atualizacao)
            print(f"🔥 [Firebase] Lead {doc.id} atualizado para status: {novo_status}")
            return True
    except Exception as e:
        print(f"❌ Erro ao atualizar status no Firebase: {e}")

def registrar_resposta_firebase(wpp_id: str, texto_resposta: str, horario_resposta: str):
    """Registra que o cliente respondeu e salva o conteúdo da resposta"""
    try:
        leads_ref = db.collection("historico_disparos")
        query = leads_ref.where("wpp_message_id", "==", wpp_id).limit(1).stream()
        
        for doc in query:
            leads_ref.document(doc.id).update({
                "respondido": True,
                "data_resposta": horario_resposta,
                "conteudo_resposta": texto_resposta
            })
            print(f"💬 [Firebase] Resposta registrada para o lead {doc.id}")
            return True
    except Exception as e:
        print(f"❌ Erro ao registrar resposta no Firebase: {e}")

@app.post("/webhook")
async def receber_evento_evolution(request: Request, background_tasks: BackgroundTasks):
    """Ponto de entrada que recebe as notificações do Railway da Evolution API"""
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
                    import time
                    horario_atual = time.strftime("%Y-%m-%d %H:%M:%S")
                    background_tasks.add_task(atualizar_status_firebase, wpp_id, "LIDO", horario_atual)
                elif status == "DELIVRD":
                    background_tasks.add_task(atualizar_status_firebase, wpp_id, "ENTREGUE")

        # 2. CAPTURA SE O CLIENTE RESPONDEU
        elif evento == "messages.upsert":
            # Garante que a mensagem veio do cliente (não enviada por nós)
            from_me = data.get("key", {}).get("fromMe", False)
            
            if not from_me:
                # Captura o ID da última mensagem enviada por nós para vincular a resposta
                # A Evolution API geralmente manda o 'quotedMessageId' quando o cliente responde diretamente, 
                # ou podemos buscar pelo número do telefone do cliente.
                wpp_id_contexto = data.get("message", {}).get("extendedTextMessage", {}).get("contextInfo", {}).get("stanzaId")
                
                # Texto digitado pelo cliente
                texto_cliente = data.get("message", {}).get("conversation") or \
                                data.get("message", {}).get("extendedTextMessage", {}).get("text", "")
                
                import time
                horario_resposta = time.strftime("%Y-%m-%d %H:%M:%S")
                
                if wpp_id_contexto and texto_cliente:
                    background_tasks.add_task(registrar_resposta_firebase, wpp_id_contexto, texto_cliente, horario_resposta)
                    
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.post("/login-check")
async def verificar_login_api(request: Request):
    """Rota para o Streamlit local autenticar usuários via nuvem"""
    try:
        payload = await request.json()
        email = payload.get("email")
        senha = payload.get("senha")
        
        # Faz a mesma busca que o seu firebase_manager fazia localmente
        usuarios_ref = db.collection("vendedores")
        query = usuarios_ref.where("email", "==", email).where("senha", "==", senha).limit(1).stream()
        
        for doc in query:
            dados = doc.to_dict()
            return {"sucesso": True, "nome": dados.get("nome", "Vendedor")}
            
        return {"sucesso": False, "erro": "Usuário ou senha inválidos."}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}