# Auditoria inicial de fontes

Atualização: 2026-09-08.

## Fontes verificadas como relevantes

### Casa Nova
- Site próprio ativo para aluguel em Divinópolis.
- Páginas públicas de detalhe exibem código do imóvel, aluguel, bairro, quartos, banheiros, vagas, área, descrição e imagens.
- Há casas residenciais e comerciais; o coletor não deve confiar apenas no título “Casa” e precisa preservar a descrição para classificação posterior.
- Primeira URL residencial verificada para coleta: imóvel 122433 (São Roque).
- Estratégia atual: coleta conservadora de páginas de detalhe previamente verificadas; expansão da descoberta automática ainda será auditada.

### Nova Somar
- Site próprio ativo em Divinópolis com páginas públicas de aluguel.
- Páginas de detalhe exibem preço, área, quartos, banheiros, vagas, descrição e características.
- O estoque mistura casas residenciais e comerciais; é obrigatório classificar o uso a partir do texto e não assumir residencial pelo tipo “casa”.
- Primeira URL residencial verificada para coleta: imóvel 10484 (Centro), embora acima do teto de oportunidade; é útil para validar coleta e regras de elegibilidade/custo.
- Estratégia atual: coleta conservadora de páginas de detalhe verificadas; expansão da descoberta automática ainda será auditada.

### Francisco Imóveis
- Site próprio ativo e explicitamente voltado a venda e locação em Divinópolis.
- A locação residencial é confirmada no site institucional.
- Próxima etapa: identificar rota pública estável de busca/detalhe antes de integrar ao coletor.

## Portais e demais imobiliárias
ZAP Imóveis, Viva Real, OLX e as demais imobiliárias cadastradas permanecem em auditoria. Não serão raspados automaticamente até existir uma rota pública estável e uma forma de coleta compatível com as regras de acesso de cada serviço.

## Princípios adotados
1. Não inventar atributos ausentes.
2. `null` significa “não informado”, nunca “não existe”.
3. Preservar URL e código de origem.
4. Separar dado observado da página de dado derivado pelo sistema.
5. Marcar anúncio que desaparece como indisponível, preservando histórico.
6. Deduplicar primeiro por fonte+código; deduplicação cruzada entre fontes será uma camada posterior com sinais de endereço, área, quartos, preço e imagens.
7. Não usar uma página comercial como opção residencial só porque o site a classifica genericamente como “Casa”.
