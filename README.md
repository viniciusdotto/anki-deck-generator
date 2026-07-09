# Anki Generator

Este projeto gera decks Anki em formato `.apkg` a partir de arquivos CSV com frases e traduções.

## O que faz

- lê a configuração de decks em `decks.csv`
- usa arquivos CSV em `contents/` para montar os cards
- pode gerar áudio para os cards com `edge-tts`
- exporta os decks prontos para a pasta `decks/`

## Estrutura

- `app.py` — script principal para gerar os decks
- `decks.csv` — csv que lista informações sobre os decks que você utiliza
- `contents/` — arquivos CSV com os cards de cada deck
- `decks/` — arquivos `.apkg` gerados
- `audios_tmp/` — áudios temporários gerados durante a execução

## Requisitos

Instale as dependências do projeto em um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
pip install genanki edge-tts
```

## Como usar

1. Faça uma cópia do molde de conteúdo em `contents/template_cards.csv` e renomeie para um nome próprio, por exemplo `contents/ingles.csv`.
2. Faça uma cópia do molde de deck em `template_deck.csv` e renomeie para `decks.csv`, nele ficarão as informações sobre os seus decks.
3. Edite o arquivo de deck criado para informar:
   - `deck_id`: será gerado na sequência
   - `nome`: Nome do seu deck
   - `idioma`: idioma que vai estudar
   - `arquivo_cards`: nome do seu csv de conteúdo presente em `contents/`
4. Gere um `deck_id` com o script bash:

```bash
./gerar_deck_id.sh
```

O comando retornará um número que deve ser colocado no campo `deck_id` do arquivo de configuração do deck.

5. Adicione o idioma de seu deck. Atualmente disponíveis:
- `en` para inglês
- `es` para espanhol
- `zh` para chinês
- `pt` para português
- Caso não seja um deck de idiomas deixe em branco

6. Execute:

```bash
python app.py
```

6. O arquivo `.apkg` será criado na pasta `decks/`.

## Modelos fornecidos

- `contents/template_cards.csv` — molde para os cards do deck.
- `template_deck.csv` — molde para a configuração do deck.

> Duplicar e renomear esses arquivos é o caminho recomendado para criar novos decks sem alterar os modelos originais.
> O id do deck é único, não o altere depois que o adicionar no Anki.

## Observações

- Os arquivos reais de conteúdo e configuração de decks são ignorados pelo Git para evitar conflitos com dados locais.
- O arquivo `.gitignore` foi preparado para ignorar artefatos de ambiente e saída gerada.
