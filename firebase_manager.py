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
            usuarios_ref = self.db.collection("vendedores")
            query = usuarios_ref.where("email", "==", email).where("senha", "==", senha).limit(1).stream()
            
            for doc in query:
                dados = doc.to_dict()
                return {"sucesso": True, "nome": dados.get("nome", "Usuário")}
                
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
            if not cpf:
                raise ValueError("O CPF é obrigatório para registrar o disparo.")
                
            lead_ref = self.db.collection("historico_disparos").document(cpf)
            
            payload = {
                "cpf": cpf,
                "nome": dados_lead.get("nome"),
                "fonte": dados_lead.get("fonte"), # Pré Aprovados / Quitados
                "criado_em_origem": dados_lead.get("criado"),
                "telefone": str(dados_lead.get("telefone")).strip(),
                "data_envio": firestore.SERVER_TIMESTAMP,
                
                # Inteligência de Texto e Performance de Blocos
                "mensagem_final": dados_lead.get("mensagem_enviada"),
                "bloco_saudacao": blocos_texto.get("saudacao_texto"),
                "bloco_introducao": blocos_texto.get("introducao_texto"),
                "bloco_oferta": blocos_texto.get("oferta_texto"),
                "bloco_cta": blocos_texto.get("cta_texto"),
                "bloco_conclusao": blocos_texto.get("conclusao_texto"),
                
                # Rastreamento de Interações
                "mensagem_id": dados_lead.get("mensagem_id"),
                "status_envio": "Enviado", # Enviado -> Entregue -> Visualizado
                "houve_retorno": False,
                "data_resposta": None,
                "tempo_ate_resposta_segundos": None
            }
            
            lead_ref.set(payload, merge=True)
            return {"sucesso": True, "id": cpf}
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}