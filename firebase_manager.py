import firebase_admin
from firebase_admin import credentials, firestore
import os

class FirebaseManager:
    def __init__(self):
        # Garante o caminho correto do arquivo json na raiz do projeto no Railway
        path_chave = os.path.join(os.path.dirname(__file__), "firebase_key.json")
        
        if not firebase_admin._apps:
            if os.path.exists(path_chave):
                cred = credentials.Certificate(path_chave)
                firebase_admin.initialize_app(cred)
                print("🟢 [Firebase] Inicializado com sucesso via arquivo de chaves!")
            else:
                # Se não achar o arquivo, tenta ler como variável de ambiente do Railway
                firebase_admin.initialize_app()
                print("⚠️ [Firebase] Arquivo firebase_key.json não encontrado. Usando credenciais padrão.")
                
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