from fastapi import FastAPI, Request, BackgroundTasks
from google.cloud import firestore
from google.oauth2 import service_account
import os
import time
import datetime
import json

app = FastAPI(title="CoZapTrigger - Webhook Listener")

# 🔑 Inicialização inteligente do Firebase
if "FIREBASE_KEY_JSON" in os.environ:
    cred_dados = json.loads(os.environ.get("FIREBASE_KEY_JSON"))
    credenciais = service_account.Credentials.from_service_account_info(cred_dados)
    db = firestore.Client(credentials=credenciais, project=credenciais.project_id)
    print("🟢 [Firebase] Conectado via Variável de Ambiente!")
else:
    NOME_ARQUIVO_CHAVE = "firebase_key.json"
    if os.path.exists(NOME_ARQUIVO_CHAVE):
        credenciais = service_account.Credentials.from_service_account_file(NOME_ARQUIVO_CHAVE)
        db = firestore.Client(credentials=credenciais, project=credenciais.project_id)
        print("🟢 [Firebase] Conectado via arquivo local!")
    else:
        db = firestore.Client()

def gerar_variantes_telefone(telefone_cliente: str):
    """Gera todas as combinações possíveis de 8/9 dígitos e máscaras para busca segura"""
    if not telefone_cliente:
        return []
    tel_limpo = "".join([c for c in telefone_cliente if c.isdigit()])
    telefones_possiveis = [tel_limpo]
    
    if tel_limpo.startswith("55"):
        sem_55 = tel_limpo[2:]
        telefones_possiveis.append(sem_55)
    else:
        sem_55 = tel_limpo
        telefones_possiveis.append(f"55{tel_limpo}")
    
    if len(sem_55) == 10:  # 8 dígitos
        ddd = sem_55[:2]
        num = sem_55[2:]
        com_9 = f"{ddd}9{num}"
        telefones_possiveis.extend([com_9, f"55{com_9}"])
        telefones_possiveis.extend([f"({ddd}) {num[:4]}-{num[4:]}", f"({ddd}) 9{num[:4]}-{num[4:]}"])
    elif len(sem_55) == 11 and sem_55[2] == "9":  # 9 dígitos
        ddd = sem_55[:2]
        num = sem_55[3:]
        sem_9 = f"{ddd}{num}"
        telefones_possiveis.extend([sem_9, f"55{sem_9}"])
        telefones_possiveis.extend([f"({ddd}) 9{num[:4]}-{num[4:]}", f"({ddd}) {num[:4]}-{num[4:]}"])
        
    return list(set(telefones_possiveis))

def atualizar_status_firebase(wpp_id: str, novo_status: str, telefone_cliente: str = None, data_leitura: str = None):
    try:
        leads_ref = db.collection("historico_disparos")
        doc_alvo_id = None
        
        # 1. Tenta pelo ID da mensagem
        if wpp_id:
            query = leads_ref.where("wpp_message_id", "==", wpp_id).limit(1).stream()
            for doc in query:
                doc_alvo_id = doc.id
                break
        
        # 2. Fallback por telefone se o ID falhar
        if not doc_alvo_id and telefone_cliente:
            variantes = gerar_variantes_telefone(telefone_cliente)
            query_tel = leads_ref.where("telefone", "in", variantes).limit(1).stream()
            for doc in query_tel:
                doc_alvo_id = doc.id
                break
                
        if doc_alvo_id:
            dados_atualizacao = {"status_envio": novo_status}
            if data_leitura:
                dados_atualizacao["data_leitura"] = data_leitura
                
            leads_ref.document(doc_alvo_id).update(dados_atualizacao)
            print(f"🔥 [Firebase] Status do lead {doc_alvo_id} atualizado para: {novo_status}")
    except Exception as e:
        print(f"❌ Erro ao atualizar status no Firebase: {e}")

def registrar_resposta_firebase(wpp_id: str, texto_resposta: str, horario_resposta: str, telefone_cliente: str = None):
    try:
        leads_ref = db.collection("historico_disparos")
        doc_alvo = None
        
        # 1. Tenta encontrar pelo ID da mensagem de contexto
        if wpp_id:
            query = leads_ref.where("wpp_message_id", "==", wpp_id).limit(1).stream()
            for doc in query:
                doc_alvo = doc
                break
                
        # 2. Fallback por Telefone usando o motor de variantes
        if not doc_alvo and telefone_cliente:
            variantes = gerar_variantes_telefone(telefone_cliente)
            query_tel = leads_ref.where("telefone", "in", variantes).limit(1).stream()
            for doc in query_tel:
                doc_alvo = doc
                break

        if doc_alvo:
            dados_existentes = doc_alvo.to_dict()
            
            # 🔒 TRAVA DE RETORNO ÚNICO
            # Se o campo 'houve_retorno' já for True, ignora as próximas mensagens
            if dados_existentes.get("houve_retorno") is True:
                print(f"🔒 [Firebase] Lead {doc_alvo.id} ja respondeu anteriormente. Ignorando mensagens adicionais.")
                return

            data_envio_dt = dados_existentes.get("data_envio")
            
            tempo_segundos = None
            if data_envio_dt:
                agora_utc = datetime.datetime.now(datetime.timezone.utc)
                if data_envio_dt.tzinfo is None:
                    data_envio_dt = data_envio_dt.replace(tzinfo=datetime.timezone.utc)
                
                diff = agora_utc - data_envio_dt
                tempo_segundos = int(diff.total_seconds())

            # Prepara o payload definitivo da PRIMEIRA resposta
            dados_atualizacao = {
                "houve_retorno": True,
                "status_envio": "LIDO",
                "data_resposta": horario_resposta,
                "conteudo_resposta": texto_resposta
            }
            
            if tempo_segundos is not None:
                dados_atualizacao["tempo_ate_resposta_segundos"] = tempo_segundos

            leads_ref.document(doc_alvo.id).update(dados_atualizacao)
            print(f"💬 [Firebase] Primeira resposta registrada com sucesso para o CPF: {doc_alvo.id}")
            
    except Exception as e:
        print(f"❌ Erro ao registrar resposta no Firebase: {e}")

@app.post("/webhook")
@app.post("/webhook/{event_name}")
async def receber_evento_evolution(request: Request, background_tasks: BackgroundTasks, event_name: str = None):
    try:
        payload = await request.json()
        evento_original = payload.get("event", "")
        data = payload.get("data", {})
        
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
            
        evento = evento_original.lower().replace("_", ".")
        
        # -----------------------------------------------------------------
        # 1. MUDANÇAS DE STATUS (ENTREGUE / LIDO)
        # -----------------------------------------------------------------
        if evento == "messages.update":
            # 🔥 CAPTURA HÍBRIDA: Lê o 'keyId' direto do JSON plano que você enviou
            wpp_id = data.get("keyId") or data.get("key", {}).get("id")
            remote_jid = data.get("remoteJid") or data.get("key", {}).get("remoteJid", "")
            status = data.get("status") or data.get("update", {}).get("status")
            
            # Extrai e limpa o telefone (removendo marcações de privacidade como :32@lid)
            telefone_cliente = remote_jid.split("@")[0] if "@" in remote_jid else ""
            if ":" in telefone_cliente:
                telefone_cliente = telefone_cliente.split(":")[0]
            
            if wpp_id and status:
                # Se o status mapeado for de leitura
                if status in ["READ", "4"]:
                    horario_atual = time.strftime("%Y-%m-%d %H:%M:%S")
                    background_tasks.add_task(atualizar_status_firebase, wpp_id, "LIDO", telefone_cliente, horario_atual)
                # Se o status mapeado for de entrega
                elif status in ["DELIVERY_ACK", "DELIVRD", "RECEIVED", "3"]:
                    background_tasks.add_task(atualizar_status_firebase, wpp_id, "ENTREGUE", telefone_cliente)

        # -----------------------------------------------------------------
        # 2. CAPTURA DE RESPOSTAS
        # -----------------------------------------------------------------
        elif evento == "messages.upsert":
            remote_jid = data.get("key", {}).get("remoteJid", "")
            telefone_cliente = remote_jid.split("@")[0] if "@" in remote_jid else ""
            if ":" in telefone_cliente:
                telefone_cliente = telefone_cliente.split(":")[0]
                
            from_me = data.get("key", {}).get("fromMe", False)
            
            if not from_me:
                wpp_id_contexto = data.get("message", {}).get("extendedTextMessage", {}).get("contextInfo", {}).get("stanzaId")
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
        print(f"💥 Erro no processamento do webhook: {e}")
        return {"status": "error", "message": str(e)}