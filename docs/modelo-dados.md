# Modelo de dados — Nossa Próxima Casa

Cada imóvel deve preservar informação bruta e informação derivada. Campos desconhecidos ficam `null`; ausência de informação nunca deve ser interpretada automaticamente como `false`.

## Identidade
- `id`: identificador estável interno
- `fingerprint`: chave de deduplicação
- `fonte`, `codigoFonte`, `url`
- `primeiroVistoEm`, `ultimoVistoEm`, `publicadoEm`
- `disponivel`

## Imóvel
- `titulo`, `tipo`, `cidade`, `bairro`, `endereco`
- `latitude`, `longitude`
- `zona`: `urbana`, `rural` ou `a_confirmar`
- `aluguel`, `condominio`, `iptu`, `custoMensalEstimado`
- `areaM2`, `quartos`, `banheiros`, `vagas`
- `quintal`, `armarios`, `churrasqueira`, `piscina`, `hidromassagem`: `true`, `false` ou `null`
- `fotos[]`

## Localização
- `hospital.distanciaKm`, `hospital.tempoCarroMin`
- `comercio.supermercado`, `farmacia`, `padaria`, `academia`, `restaurantes`, `posto`
- `comercio.nota` e `comercio.resumo`

## Avaliação visual
- `nota` (0–10)
- `estilo`
- `conservacaoAparente`
- `acabamentos`
- `cozinhaBanheiros`
- `armariosAparentes`
- `areaExterna`
- `confianca`: baixa/média/alta
- `observacoes[]`

A avaliação visual nunca deve afirmar qualidade estrutural, elétrica, hidráulica ou ausência de infiltração apenas por fotografias.

## Match
- `casa` (0–100)
- `localizacao` (0–100)
- `custoBeneficio` (0–100)
- `visual` (0–100)
- `final` (0–100)
- `motivosPositivos[]`, `pontosAtencao[]`

Pesos iniciais: casa 40%, localização 25%, custo-benefício 20%, visual 15%.

## Histórico
Mudanças relevantes devem ser preservadas em `historico[]`, especialmente preço, disponibilidade e fonte.

## Regras críticas
1. Mínimo desejado: 90 m² e 3 quartos.
2. Faixa ideal de aluguel: R$ 2.000–3.000.
3. R$ 3.001–3.500 permanece elegível como oportunidade.
4. Quintal e armários são desejáveis, mas `null` não elimina imóvel.
5. `primeiroVistoEm` define o que é novo no nosso sistema.
6. Imóveis repetidos entre fontes devem ser consolidados, mantendo todas as URLs/origens conhecidas.
