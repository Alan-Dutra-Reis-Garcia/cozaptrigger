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
            print(f"⚠️ [Firebase] ID de mensagem {wpp_id} nao encontrado.")
    except Exception as e:
        print(f"❌ Erro ao atualizar status: {e}")

def registrar_resposta_firebase(wpp_id: str, texto_resposta: str, horario_resposta: str, telefone_cliente: str = None):
    try:
        leads_ref = db.collection("historico_disparos")
        doc_alvo_id = None
        
        # 1. Busca por ID da mensagem (Se o cliente clicou em Responder diretamente a ela)
        if wpp_id:
            query = leads_ref.where("wpp_message_id", "==", wpp_id).limit(1).stream()
            for doc in query:
                doc_alvo_id = doc.id
                break
                
        # 2. Fallback Inteligente por Telefone (Gera todas as combinações de 8/9 dígitos e máscaras)
        if not doc_alvo_id and telefone_cliente:
            tel_limpo = "".join([c for c in telefone_cliente if c.isdigit()])
            
            # Lista que vai guardar todas as formas possíveis que o número pode estar no seu banco
            telefones_possiveis = [tel_limpo]
            
            if tel_limpo.startswith("55"):
                sem_55 = tel_limpo[2:]
                telefones_possiveis.append(sem_55)
            else:
                sem_55 = tel_limpo
                telefones_possiveis.append(f"55{tel_limpo}")
            
            # 🕵️‍♂️ Quebra o calcanhar de aquiles do 9º dígito do padrão brasileiro
            if len(sem_55) == 10:  # Se a Evolution mandou sem o 9 (Ex: 4498773682)
                ddd = sem_55[:2]
                num = sem_55[2:]
                com_9 = f"{ddd}9{num}"
                telefones_possiveis.extend([com_9, f"55{com_9}"])
                # Adiciona formatos com máscaras comuns de CRM por garantia
                telefones_possiveis.extend([f"({ddd}) {num[:4]}-{num[4:]}", f"({ddd}) 9{num[:4]}-{num[4:]}"])
                
            elif len(sem_55) == 11 and sem_55[2] == "9":  # Se a Evolution mandou com o 9 (Ex: 44998773682)
                ddd = sem_55[:2]
                num = sem_55[3:]
                sem_9 = f"{ddd}{num}"
                telefones_possiveis.extend([sem_9, f"55{sem_9}"])
                telefones_possiveis.extend([f"({ddd}) 9{num[:4]}-{num[4:]}", f"({ddd}) {num[:4]}-{num[4:]}"])

            # Procura no Firebase se o campo 'telefone' bate com QUALQUER uma das opções da lista
            query_tel = leads_ref.where("telefone", "in", telefones_possiveis).limit(1).stream()
            for doc in query_tel:
                doc_alvo_id = doc.id
                break

        if doc_alvo_id:
            leads_ref.document(doc_alvo_id).update({
                "respondido": True,
                "data_resposta": horario_resposta,
                "conteudo_resposta": texto_resposta
            })
            print(f"💬 [Firebase] Resposta gravada com sucesso para o lead: {doc_alvo_id}")
        else:
            print(f"⚠️ [Firebase] Nenhum lead encontrado para as variantes: {telefones_possiveis}")
            
    except Exception as e:
        print(f"❌ Erro ao registrar resposta no Firebase: {e}")
@app.post("/webhook")
async def receber_evento_evolution(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        evento_original = payload.get("event", "")
        data = payload.get("data", {})
        
        # Se a Evolution enviar os dados envelopados em uma lista, extrai o primeiro item
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
            
        evento = evento_original.lower().replace("_", ".")
        print(f"📥 [Webhook] Processando evento: '{evento}'")
        
        # 1. MUDANÇAS DE STATUS (ENTREGUE / LIDO)
        if evento == "messages.update":
            wpp_id = data.get("key", {}).get("id")
            # ✨ CAPTURA INTELIGENTE: Pega o status independente de onde a API colocou
            status = data.get("status") or data.get("update", {}).get("status")
            
            if wpp_id and status:
                if status == "READ":
                    horario_atual = time.strftime("%Y-%m-%d %H:%M:%S")
                    background_tasks.add_task(atualizar_status_firebase, wpp_id, "LIDO", horario_atual)
                elif status in ["DELIVRD", "RECEIVED"]:
                    background_tasks.add_task(atualizar_status_firebase, wpp_id, "ENTREGUE")

        # 2. CAPTURA DE RESPOSTAS
        elif evento == "messages.upsert":
            from_me = data.get("key", {}).get("fromMe", False)
            
            if not from_me:
                remote_jid = data.get("key", {}).get("remoteJid", "")
                telefone_cliente = remote_jid.split("@")[0] if "@" in remote_jid else ""
                
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