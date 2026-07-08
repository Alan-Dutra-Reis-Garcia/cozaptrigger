import firebase_admin
from firebase_admin import credentials, firestore, auth
import os

class FirebaseManager:
    def __init__(self, cred_path="firebase_key.json"):
        """
        Inicializa a conexão segura com o Firebase Firestore.
        """
        if not firebase_admin._apps:
            if not os.path.exists(cred_path):
                raise FileNotFoundError(f"O arquivo {cred_path} não foi encontrado na pasta do projeto.")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()

    def verificar_login(self, email, senha):
        """
        Simula a validação de login e senha. Como estamos rodando o Python como servidor backend,
        podemos gerenciar os usuários permitidos direto em uma coleção de segurança no Firestore.
        """
        try:
            # Busca o vendedor pelo e-mail na coleção de usuários autorizados
            user_ref = self.db.collection("vendedores").document(email.lower()).get()
            if user_ref.exists:
                dados = user_ref.to_dict()
                # Verifica se a senha confere e se o usuário está ativo
                if dados.get("senha") == senha and dados.get("ativo", True):
                    return {"sucesso": True, "nome": dados.get("nome", email)}
                return {"sucesso": False, "erro": "Senha incorreta ou usuário desativado."}
            return {"sucesso": False, "erro": "Usuário não autorizado no sistema."}
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