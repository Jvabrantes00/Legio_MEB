import random
# ALERTA: Troque 'NOME_DO_SEU_APP' pelo nome real do seu app no Django!
from core.models import Alpinista 

nomes = ["Ana", "Bruno", "Carlos", "Daniela", "Eduardo", "Fernanda", "Gabriel", "Helena", "Igor", "Julia", "Lucas", "Mariana", "Nicolas", "Olivia", "Pedro", "Quintino", "Rafaela", "Samuel", "Tatiana", "Vinicius"]
sobrenomes = ["Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves", "Pereira", "Lima", "Gomes", "Costa", "Ribeiro", "Martins", "Carvalho", "Almeida"]
status_opcoes = ["ativo", "ativo", "inativo", "pendente"] # Mais ativos para ficar realista
neuro_opcoes = ["TDAH", "Autismo Nível 1", "Dislexia", "TDAH e Autismo"]

print("Plantando sementes no banco de dados...")

for i in range(1, 31):
    nome_completo = f"{random.choice(nomes)} {random.choice(sobrenomes)} {random.choice(sobrenomes)}"
    # Gera um CPF falso mas no formato correto e garantindo ser único
    cpf_falso = f"{random.randint(100, 999)}.{random.randint(100, 999)}.{random.randint(100, 999)}-{random.randint(10, 99)}"
    
    is_neuro = random.choice([True, False, False, False, False]) # ~20% de chance
    tipo_neuro = random.choice(neuro_opcoes) if is_neuro else ""

    Alpinista.objects.create(
        nome=nome_completo,
        cpf=cpf_falso,
        email=f"teste{i}@escalada.com",
        telefone=f"619{random.randint(10000000, 99999999)}",
        status=random.choice(status_opcoes),
        is_neurodivergente=is_neuro,
        tipo_neurodivergente=tipo_neuro,
        grupo=f"Grupo {random.choice(['Amarelo', 'Azul', 'Vermelho', 'Verde', 'Laranja'])}"
    )

print("30 Alpinistas criados com sucesso! Pode fechar o shell.")