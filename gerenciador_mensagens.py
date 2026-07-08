import random

class GerenciadorMensagens:
    def __init__(self):
        # Armazenamos os blocos de Spintax separados por Fonte
        self.blocos_fontes = {
            "Quitados": {
                "saudacoes": ["Oie", "Olá", "Oii", "Oi", "Ei", "Oii"],
                "introducoes": [
                    "Você já faz parte dos nossos clientes e, por isso, pode ter uma nova oportunidade de crédito disponível.",
                    "Como você já contratou conosco anteriormente, pode haver uma nova oferta de crédito para o seu perfil.",
                    "Passando para avisar que pode existir uma nova condição de crédito disponível para você.",
                    "Você já conhece nossos serviços e pode ter uma nova oportunidade disponível.",
                    "Identificamos que você pode estar apto(a) a uma nova análise de crédito."
                ],
                "ofertas": [
                    "Se estiver precisando de um reforço financeiro, podemos verificar as condições disponíveis.",
                    "Caso esteja precisando de crédito, podemos consultar uma nova proposta para você.",
                    "Se este for um bom momento para você, podemos conferir as opções disponíveis.",
                    "Podemos fazer uma nova consulta e verificar as melhores condições para o seu perfil.",
                    "Vale a pena consultar se há uma nova oportunidade disponível para você."
                ],
                "ctas": [
                    "É só responder esta mensagem.",
                    "Basta responder esta mensagem.",
                    "É só nos enviar uma mensagem.",
                    "Responda por aqui e fazemos a consulta.",
                    "Fale conosco por esta conversa para verificar as condições."
                ],
                "conclusoes": [
                    "Esperamos seu contato! CREFAZ", "Conte com a gente! CREFAZ", "Estamos à disposição! CREFAZ", 
                    "Até mais! CREFAZ", "Tenha um ótimo dia! CREFAZ", "Ficamos no aguardo! CREFAZ", "Será um prazer atender você! CREFAZ"
                ]
            },
            "Pré Aprovados": {
                "saudacoes": ["Oie", "Olá", "Oii", "Oi", "Ei", "Oii"],
                "introducoes": [
                    "Verifiquei no sistema que você solicitou uma simulação recentemente e não contratou.",
                    "Ótima notícia! Identificamos que consta uma simulação pré-aprovada exclusiva no seu CPF.",
                    "Passando para avisar que o seu cadastro foi selecionado e pode possuir uma oferta de crédito disponível.",
                    "A sua ficha de análise atualizou e pode haver uma oportunidade pré-aprovada para você hoje.",
                    "Verifiquei que liberamos uma nova linha de crédito para o seu perfil."
                ],
                "ofertas": [
                    "Esse valor pode estar disponível e podemos verificar as melhores condições para o parcelmento.",
                    "Se você tiver interesse em um fôlego financeiro, podemos simular as condições agora.",
                    "Caso queira aproveitar essa liberação, conseguimos excelentes vantagens para o seu caso.",
                    "Podemos fazer uma simulação rápida para você ver como ficam as parcelas.",
                    "Vale a pena dar uma olhada nas condições especiais."
                ],
                "ctas": [
                    "É só me responder por aqui.",
                    "Basta responder esta mensagem para iniciarmos.",
                    "Responda essa mensagem para conferir.",
                    "Fale comigo por aqui para conferimos essa oportunidade.",
                    "É só dar um sinal por esta conversa e eu te passo os valores."
                ],
                "conclusoes": [
                    "Aguardamos seu retorno! CREFAZ", "Conte com a gente! CREFAZ", "Tenha um excelente dia! CREFAZ",
                    "Estamos à disposição para ajudar! CREFAZ", "Até logo! CREFAZ", "Fico no aguardo! CREFAZ", "Será um prazer te atender! CREFAZ"
                ]
            }
        }

    def gerar_mensagem_randomica(self, nome_cliente, fonte_cliente):
        """
        Monta a mensagem combinando 1 bloco aleatório de cada etapa do esqueleto 
        de acordo com a fonte do lead e mapeia as escolhas para o relatório.
        """
        if fonte_cliente not in self.blocos_fontes:
            fonte_cliente = "Pré Aprovados"
            
        blocos = self.blocos_fontes[fonte_cliente]
        
        # Sorteia um elemento de cada lista
        saudacao = random.choice(blocos["saudacoes"])
        introducao = random.choice(blocos["introducoes"])
        oferta = random.choice(blocos["ofertas"])
        cta = random.choice(blocos["ctas"])
        conclusao = random.choice(blocos["conclusoes"])
        
        # Trata o primeiro nome do cliente
        primeiro_nome = nome_cliente.split()[0].strip().capitalize()
        
        # Monta a estrutura final
        mensagem_final = f"{saudacao} {primeiro_nome}! 😊\n{introducao}\n{oferta}\n{cta}\n{conclusao}"
        
        # Dicionário de detalhes para enviarmos para o Firebase acompanhar a performance de cada bloco
        detalhes_blocos = {
            "saudacao_texto": saudacao,
            "introducao_texto": introducao,
            "oferta_texto": oferta,
            "cta_texto": cta,
            "conclusao_texto": conclusao
        }
        
        return mensagem_final, detalhes_blocos