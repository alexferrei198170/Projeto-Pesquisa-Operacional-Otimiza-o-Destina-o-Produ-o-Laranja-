from gurobipy import *
import pandas as pd
import matplotlib.pyplot as plt

# FUNÇÃO DE OTIMIZAÇÃO
def executar_modelo(
    nome_cenario,
    preco_mercado,
    preco_industria,
    perc_mercado=0.20,
    perc_industria=0.40
):
    modelo = Model(nome_cenario)
    modelo.setParam("OutputFlag", 0)
    meses = [
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro"
    ]
    producao = {
        "Julho": 25000,
        "Agosto": 20000,
        "Setembro": 18000,
        "Outubro": 15000,
        "Novembro": 12000,
        "Dezembro": 10000
    }

    # VARIÁVEIS DE DECISÃO
    M = modelo.addVars(meses, lb=0, name="Mercado")
    I = modelo.addVars(meses, lb=0, name="Industria")
    TM = modelo.addVars(
        meses[:-1],
        lb=0,
        name="TransferenciaMercado"
    )
    TI = modelo.addVars(
        meses[:-1],
        lb=0,
        name="TransferenciaIndustria"
    )

    # FUNÇÃO OBJETIVO
    modelo.setObjective(
        quicksum(
            preco_mercado[m] * M[m]
            for m in meses
        )
        +
        quicksum(
            preco_industria[m] * I[m]
            for m in meses
        ),
        GRB.MAXIMIZE
    )

    # BALANÇO DE PRODUÇÃO
    # Julho
    modelo.addConstr(
        M["Julho"]
        +
        I["Julho"]
        +
        TM["Julho"]
        +
        TI["Julho"]
        ==
        producao["Julho"]
    )
    # Agosto até Novembro
    for i in range(1, 5):
        atual = meses[i]
        anterior = meses[i - 1]
        modelo.addConstr(
            M[atual]
            +
            I[atual]
            +
            TM[atual]
            +
            TI[atual]
            ==
            producao[atual]
            +
            TM[anterior]
            +
            TI[anterior]
        )
    # Dezembro
    modelo.addConstr(
        M["Dezembro"]
        +
        I["Dezembro"]
        ==
        producao["Dezembro"]
        +
        TM["Novembro"]
        +
        TI["Novembro"]
    )

    # POSTERGAÇÃO DA COLHEITA
    for mes in meses[:-1]:
        modelo.addConstr(
            TM[mes]
            <=
            perc_mercado * producao[mes]
        )
        modelo.addConstr(
            TI[mes]
            <=
            perc_industria * producao[mes]
        )

    # CAPACIDADE DO MERCADO INTERNO
    for mes in meses:
        modelo.addConstr(
            M[mes]
            <=
            12000
        )

    # CONTRATO MÍNIMO COM A INDÚSTRIA
    modelo.addConstr(
        quicksum(
            I[m]
            for m in meses
        )
        >=
        40000
    )

    # RESOLUÇÃO
    modelo.optimize()
    if modelo.Status != GRB.OPTIMAL:
        raise Exception(
            f"Não foi encontrada solução ótima para {nome_cenario}"
        )
    receita = modelo.ObjVal
    mercado_total = sum(
        M[m].X
        for m in meses
    )
    industria_total = sum(
        I[m].X
        for m in meses
    )
    return {
        "receita": receita,
        "mercado": mercado_total,
        "industria": industria_total
    }

# RECEITA TRADICIONAL (SEM POSTERGAÇÃO)
receita_tradicional = (
    (12000 * 1700 + 13000 * 1450)
    +
    (12000 * 1850 + 8000 * 1550)
    +
    (12000 * 2000 + 6000 * 1700)
    +
    (12000 * 2150 + 3000 * 1800)
    +
    (12000 * 2250)
    +
    (10000 * 2300)
)

# PREÇOS 
mercado_base = {
    "Julho": 1700,
    "Agosto": 1850,
    "Setembro": 2000,
    "Outubro": 2150,
    "Novembro": 2250,
    "Dezembro": 2300
}
industria_base = {
    "Julho": 1450,
    "Agosto": 1550,
    "Setembro": 1700,
    "Outubro": 1800,
    "Novembro": 1850,
    "Dezembro": 1900
}

# CENÁRIO 1 # BASE
cenario1 = executar_modelo(
    "Base",
    mercado_base,
    industria_base
)

# CENÁRIO 2 # MERCADO -15%
mercado_c2 = {
    k: v * 0.85
    for k, v in mercado_base.items()
}
cenario2 = executar_modelo(
    "Mercado -15%",
    mercado_c2,
    industria_base
)

# CENÁRIO 3 # INDÚSTRIA +20%
industria_c3 = {
    k: v * 1.20
    for k, v in industria_base.items()
}
cenario3 = executar_modelo(
    "Indústria +20%",
    mercado_base,
    industria_c3
)

# CENÁRIO 4 # REDUÇÃO DAS JANELAS
cenario4 = executar_modelo(
    "Janela Reduzida",
    mercado_base,
    industria_base,
    perc_mercado=0.10,
    perc_industria=0.20
)

# COMPARATIVO
comparativo = pd.DataFrame({
    "Cenário": [
        "Base",
        "Mercado -15%",
        "Indústria +20%",
        "Janela Reduzida"
    ],
    "Receita": [
        cenario1["receita"],
        cenario2["receita"],
        cenario3["receita"],
        cenario4["receita"]
    ],
    "Mercado Interno (t)": [
        cenario1["mercado"],
        cenario2["mercado"],
        cenario3["mercado"],
        cenario4["mercado"]
    ],
    "Indústria (t)": [
        cenario1["industria"],
        cenario2["industria"],
        cenario3["industria"],
        cenario4["industria"]
    ]
})
comparativo["Variação (%)"] = (
    (
        comparativo["Receita"]
        -
        cenario1["receita"]
    )
    /
    cenario1["receita"]
) * 100
print("\n")
print("=" * 100)
print("COMPARATIVO DOS CENÁRIOS")
print("=" * 100)
print(comparativo)

# GRÁFICO
plt.figure(figsize=(10,6))

# Cores específicas para cada cenário
cores = ["orange","gold","green","blue"]

# Barras
plt.bar(comparativo["Cenário"], comparativo["Receita"]/1e6, color=cores)

# Título e eixos
plt.title("Receita Máxima por Cenário")
plt.ylabel("Receita (Milhões de R$)")
plt.grid(axis="y", alpha=0.3)

# Valores acima das barras
for i, valor in enumerate(comparativo["Receita"]):
    plt.text(i, valor/1e6 + 0.5, f"{valor/1e6:.2f}", ha="center")



plt.tight_layout()
plt.show()

# CONCLUSÕES AUTOMÁTICAS
melhor = comparativo.loc[
    comparativo["Receita"].idxmax()
]
print("\n")
print("=" * 100)
print("CONCLUSÕES")
print("=" * 100)
print(
    f"Melhor Cenário: "
    f"{melhor['Cenário']}"
)
print(
    f"Receita Máxima: "
    f"R$ {melhor['Receita']:,.2f}"
)
print("\nINTERPRETAÇÃO")
print(
    "- O modelo identifica a alocação ótima entre mercado interno e indústria."
)
print(
    "- A postergação limitada da colheita possui valor econômico."
)
print(
    "- A indústria torna-se mais atrativa quando seus preços aumentam."
)
print(
    "- A redução das janelas operacionais diminui a flexibilidade do sistema."
)
print(
    "- A Programação Linear mostrou-se eficaz como ferramenta de apoio à decisão."
)
