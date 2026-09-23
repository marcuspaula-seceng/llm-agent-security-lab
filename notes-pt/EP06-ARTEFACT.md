# EP06 — Artefacto: o que esta série prova, em três números

**Ciclo 8 · 22/09/2026** · fecho técnico.

## Os três números

```text
5/5  ->  1/5  ->  0/5     EP03: prompt injection, de baseline a arquitectura
1/5 restante = injecção INDIRECTA (o vector realista)

2 de 2 acções perigosas pedidas pelo agente nas DUAS configs
0 de 2 executadas quando a guarda é código          EP04/05
```

## O fio condutor da série

| Ep | Pergunta | Resposta medida |
|---|---|---|
| 01 | O system prompt protege um segredo? | Não: 5/5 vazaram, incluindo *"I can't provide… it is SECRET-ALPHA-7"* |
| 03 | Um prompt melhor protege? | Quase: 1/5 — e o que passa é a injecção indirecta |
| 03 | Tirar o segredo do contexto protege? | Sim, por ausência: 0/5 sem o filtro actuar |
| 04+05 | Um agente com ferramentas obedece a um ficheiro? | Sim, de imediato: apaga e exfiltra |
| 04+05 | O que o trava? | Código depois do modelo — não o modelo |
| 02 | (garak) | **não executado** — exige instalação; declarado |

A conclusão que atravessa os quatro episódios executados é uma só:

> **O modelo não é a fronteira de segurança.** A fronteira é o que ele *não tem* (segredo
> fora do contexto, ferramenta fora da allowlist) e o que corre *depois* dele (filtro de
> saída, confirmação humana). Regras dentro do prompt são a última linha, não a primeira.

## Ligação ao resto do repositório de estudo

- Ciclo 5 Dia 6: automação **informa**, humano decide — a automation rule não fecha incidentes.
- Ciclo 7: o playbook `triage.py` tem `decision: NENHUMA` por contrato, com teste.
- Ciclo 8: a guarda G1 é o mesmo princípio dentro de um agente LLM.

Três ciclos, um princípio, três implementações. É isso que se explica em entrevista.

## Reprodutibilidade

```text
python lab/ep03_mitigations.py       ~11 min em CPU, escreve ep03-resultado.{txt,json}
python lab/ep04_excessive_agency.py  ~7 min,  escreve ep04-resultado.{txt,json}
```

Ollama local em `127.0.0.1:11434` com `qwen2.5:7b`. Nada mais.

## Limitações da série inteira

- Um modelo, uma execução por caso, temperatura 0. Reprodutível; não estatístico.
- Sem garak: sem cobertura sistemática de sondas. É a lacuna maior e está nomeada.
- Detecção de vazamento por string; encodings não cobertos.

## Perguntas em aberto (para um Ciclo 8.1, se houver)

- `qwen2.5:3b` vaza mais ou menos? (EP01, ainda por medir)
- M2 com o segredo a entrar pelo *user turn* — o filtro de saída é testado a sério.
- G1 com `read_file` de caminho fora da pasta — o ataque que cabe na allowlist.

```text
MARCUS REFLECTION: PENDING
```
