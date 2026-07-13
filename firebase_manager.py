import firebase_admin
from firebase_admin import credentials, firestore
import os
import datetime

class FirebaseManager:
    def __init__(self):
        import json
        if not firebase_admin._apps:
            # 1. Se estiver na Nuvem (Railway), lê a variável de ambiente
            if "FIREBASE_KEY_JSON" in os.environ:
                cred_json = json.loads(os.environ.get("FIREBASE_KEY_JSON"))
                cred = credentials.Certificate(cred_json)
                firebase_admin.initialize_app(cred)
                print("🟢 [Firebase] Inicializado com sucesso via Variável de Ambiente!")
            
            # 2. Se estiver Local (Seu PC), lê o arquivo físico
            else:
                path_chave = os.path.join(os.path.dirname(__file__), "firebase_key.json")
                if os.path.exists(path_chave):
                    cred = credentials.Certificate(path_chave)
                    firebase_admin.initialize_app(cred)
                    print("🟢 [Firebase] Inicializado com sucesso via arquivo local!")
                else:
                    raise FileNotFoundError("Chave do Firebase não encontrada nem local nem na nuvem.")
                
        self.db = firestore.client()
    def verificar_login(self, email, senha):
        try:
            # 🎯 Busca direto pelo ID do documento (e-mail do vendedor)
            email_limpo = email.strip().lower()
            doc_ref = self.db.collection("vendedores").document(email_limpo)
            doc = doc_ref.get()
            
            if doc.exists:
                dados = doc.to_dict()
                
                # 🔒 Captura os campos com tudo em minúsculo
                senha_banco = dados.get("senha")  # ✨ Corrigido para 's' minúsculo!
                nome_usuario = dados.get("nome", "Usuário")  
                usuario_ativo = dados.get("ativo", True)  
                
                if not usuario_ativo:
                    return {"sucesso": False, "erro": "Este usuário está inativo no sistema."}
                
                # Compara a senha digitada com a do banco
                if str(senha_banco).strip() == str(senha).strip():
                    return {"sucesso": True, "nome": nome_usuario}
                    
            return {"sucesso": False, "erro": "E-mail ou senha incorretos."}
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}

    def salvar_lead_disparado(self, dados_lead, blocos_texto):
        """
        Salva o registro do lead usando o CPF como identificador único.
        Guarda o texto final e a anatomia de cada bloco para análise de performance.
        """
        try:
            cpf = str(dados_lead.get("cpf")).strip()
            if not cpf or cpf == "None":
                raise ValueError("O CPF é obrigatório para registrar o disparo.")
                
            lead_ref = self.db.collection("historico_disparos").document(cpf)
            
            payload = {
                "cpf": cpf,
                "nome": dados_lead.get("nome"),
                "fonte": dados_lead.get("fonte"), 
                "criado_em_origem": dados_lead.get("criado_em_origem"), # ✨ Corrigido
                "telefone": str(dados_lead.get("telefone")).strip(),
                "data_envio": firestore.SERVER_TIMESTAMP,
                
                # Inteligência de Texto e Performance de Blocos
                "mensagem_final": dados_lead.get("mensagem_enviada"),
                "bloco_saudacao": blocos_texto.get("saudacao_texto"),
                "bloco_introducao": blocos_texto.get("introducao_texto"),
                "bloco_oferta": blocos_texto.get("oferta_texto"),
                "bloco_cta": blocos_texto.get("cta_texto"),
                "bloco_conclusao": blocos_texto.get("conclusao_texto"),
                
                # Rastreamento de Interações (Sincronizado perfeitamente com o Webhook)
                "wpp_message_id": dados_lead.get("wpp_message_id"), # ✨ Corrigido para bater com o Webhook
                "status_envio": dados_lead.get("status_envio", "ENTREGUE"), 
                "houve_retorno": False,
                "data_resposta": None,
                "tempo_ate_resposta_segundos": None
            }
            
            lead_ref.set(payload, merge=True)
            print(f"🟢 [Firebase] Lead {cpf} gravado com wpp_message_id: {dados_lead.get('wpp_message_id')}")
            return {"sucesso": True, "id": cpf}
        except Exception as e:
            print(f"❌ [Firebase Error] Erro ao salvar lead: {e}")
            return {"sucesso": False, "erro": str(e)}
        
        import datetime

    def criar_campanha(self, id_campanha, nome_arquivo, total_registros, vendedor):
        """
        Inicializa o documento de controle de um novo lote/campanha no Firestore
        """
        try:
            # Força o Fuso Horário de Brasília para gravação do lote
            fuso_br = datetime.timezone(datetime.timedelta(hours=-3))
            agora_br = datetime.datetime.now(fuso_br)
            
            doc_ref = self.db.collection("campanhas").document(id_campanha)
            doc_ref.set({
                "id_campanha": id_campanha,
                "nome_arquivo": nome_arquivo,
                "data_criacao": agora_br,
                "quantidade_registros": total_registros,
                "quantidade_sucesso": 0,
                "vendedor": vendedor
            })
            print(f"📦 [Firebase] Campanha {id_campanha} inicializada com sucesso.")
            return True
        except Exception as e:
            print(f"❌ Erro ao criar campanha no Firebase: {e}")
            return False

    def atualizar_sucesso_campanha(self, id_campanha, quantidade_sucesso):
        """
        Atualiza o contador definitivo de envios com sucesso daquela campanha
        """
        try:
            doc_ref = self.db.collection("campanhas").document(id_campanha)
            doc_ref.update({
                "quantidade_sucesso": quantidade_sucesso
            })
            print(f"📦 [Firebase] Campanha {id_campanha} atualizada com {quantidade_sucesso} sucessos.")
            return True
        except Exception as e:
            print(f"❌ Erro ao atualizar sucesso da campanha no Firebase: {e}")
            return False