"""
anki_gerador.py
================
Fluxo interativo para gerar decks Anki com áudio (via edge-tts).

Estrutura de arquivos:
  decks.csv              → lista de decks disponíveis (configuração)
  cards_<algo>.csv        → um arquivo por deck, apenas com frente/verso

Instalação (dentro do seu venv):
    pip install edge-tts genanki

Uso:
    python anki_gerador.py

O script:
  1. Lê decks.csv e mostra a lista de decks disponíveis
  2. Pergunta qual deck você quer gerar
  3. Pergunta se você quer gerar áudio para os cards
  4. Gera os áudios (se solicitado) e empacota tudo em um .apkg
"""

import asyncio
import csv
import re
import random
import sys
import genanki
import edge_tts
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIGURAÇÕES — edite aqui
# ─────────────────────────────────────────────

ARQUIVO_DECKS  = "decks.csv"        # lista de decks disponíveis
PASTA_AUDIO    = Path("audios_tmp") # pasta temporária para os MP3s
PASTA_SAIDA    = Path("decks")          # onde os .apkg gerados serão salvos
MAX_TENTATIVAS = 10                  # tentativas de gerar áudio por frase

# Modelo do card é compartilhado por todos os decks — ID fixo, nunca mude
MODEL_ID_COM_AUDIO = 9274651820
MODEL_ID_SEM_AUDIO = 9274651821

# Vozes em inglês disponíveis para sorteio aleatório.
# Cada frase em inglês usará uma voz diferente, sorteada na hora.
VOZES_EN = [
    "en-US-JennyNeural",       # feminino — americano, caloroso
    "en-US-GuyNeural",         # masculino — americano, claro
    "en-US-AriaNeural",        # feminino — americano, expressivo
    "en-US-DavisNeural",       # masculino — americano, casual
    "en-US-JaneNeural",        # feminino — americano, suave
    "en-US-JasonNeural",       # masculino — americano, direto
    "en-GB-SoniaNeural",       # feminino — britânico
    "en-GB-RyanNeural",        # masculino — britânico
    "en-AU-NatashaNeural",     # feminino — australiano
    "en-AU-WilliamNeural",     # masculino — australiano
]

# Vozes fixas para os demais idiomas
VOZES = {
    "es":    "es-ES-ElviraNeural",     # espanhol peninsular
    "es-mx": "es-MX-DaliaNeural",      # espanhol mexicano
    "zh":    "zh-CN-XiaoxiaoNeural",   # chinês mandarim
    "pt":    "pt-BR-FranciscaNeural",  # português brasileiro
}


def obter_voz(idioma: str) -> str | None:
    """Retorna a voz para o idioma. Para 'en', sorteia aleatoriamente."""
    idioma = idioma.lower()
    if idioma == "en":
        return random.choice(VOZES_EN)
    return VOZES.get(idioma)


# ─────────────────────────────────────────────
# MODELOS DO CARD
# ─────────────────────────────────────────────

MODELO_COM_AUDIO = genanki.Model(
    MODEL_ID_COM_AUDIO,
    "Idiomas com Áudio",
    fields=[
        {"name": "Frente"},
        {"name": "Verso"},
        {"name": "Audio"},   # tag [sound:arquivo.mp3]
    ],
    templates=[
        {
            "name": "Card 1",
            "qfmt": """
                <div class="frase">{{Frente}}</div>
                {{Audio}}
            """,
            "afmt": """
                {{FrontSide}}
                <hr>
                <div class="traducao">{{Verso}}</div>
            """,
        }
    ],
    css="""
        .card { font-family: Arial, sans-serif; text-align: center; padding: 20px; }
        .frase { font-size: 28px; font-weight: bold; margin: 16px 0; }
        .traducao { font-size: 22px; color: #2a5; margin-top: 12px; }
    """,
)

MODELO_SEM_AUDIO = genanki.Model(
    MODEL_ID_SEM_AUDIO,
    "Idiomas sem Áudio",
    fields=[
        {"name": "Frente"},
        {"name": "Verso"},
    ],
    templates=[
        {
            "name": "Card 1",
            "qfmt": '<div class="frase">{{Frente}}</div>',
            "afmt": """
                {{FrontSide}}
                <hr>
                <div class="traducao">{{Verso}}</div>
            """,
        }
    ],
    css="""
        .card { font-family: Arial, sans-serif; text-align: center; padding: 20px; }
        .frase { font-size: 28px; font-weight: bold; margin: 16px 0; }
        .traducao { font-size: 22px; color: #2a5; margin-top: 12px; }
    """,
)


# ─────────────────────────────────────────────
# LEITURA DE DECKS DISPONÍVEIS
# ─────────────────────────────────────────────

def carregar_decks() -> list[dict]:
    """Lê o decks.csv e retorna a lista de decks configurados."""
    try:
        with open(ARQUIVO_DECKS, encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"[!] Arquivo '{ARQUIVO_DECKS}' não encontrado.")
        sys.exit(1)


def escolher_deck(decks: list[dict]) -> dict:
    """Mostra a lista de decks e pede para o usuário escolher um."""
    print("\nDecks disponíveis:\n")
    for i, deck in enumerate(decks, 1):
        idioma = deck["idioma"].strip() or "—"
        print(f"  [{i}] {deck['nome']}  (idioma: {idioma})")

    while True:
        escolha = input(f"\nEscolha um deck [1-{len(decks)}]: ").strip()
        if escolha.isdigit() and 1 <= int(escolha) <= len(decks):
            return decks[int(escolha) - 1]
        print("Opção inválida, tente novamente.")


# ─────────────────────────────────────────────
# GERAÇÃO DE ÁUDIO
# ─────────────────────────────────────────────

def nome_arquivo_audio(texto: str, idioma: str, voz: str) -> str:
    """Gera um nome de arquivo seguro a partir do texto, idioma e voz usada."""
    slug = re.sub(r"[^\w]", "_", texto.lower())[:40]
    voz_curta = voz.split("-")[-1].replace("Neural", "").lower()
    return f"{idioma}_{voz_curta}_{slug}.mp3"


async def gerar_audio(texto: str, voz: str, caminho: Path, idioma: str) -> bool:
    """Gera um arquivo MP3 com edge-tts.
    Tenta até MAX_TENTATIVAS vezes, sorteando uma nova voz a cada falha
    (para inglês). Retorna True apenas se o arquivo foi gerado com sucesso.
    """
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            communicate = edge_tts.Communicate(texto, voz)
            await communicate.save(str(caminho))
            return True
        except Exception as e:
            print(f"    [!] Tentativa {tentativa}/{MAX_TENTATIVAS} falhou: {e}")
            if tentativa < MAX_TENTATIVAS:
                voz = obter_voz(idioma)
                print(f"    🔄 Tentando com voz alternativa: {voz}")

    print(f"    ✗ Áudio não gerado após {MAX_TENTATIVAS} tentativas: '{texto}'")
    return False


# ─────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────

async def main():
    decks = carregar_decks()
    if not decks:
        print(f"[!] Nenhum deck encontrado em '{ARQUIVO_DECKS}'.")
        sys.exit(1)

    deck_escolhido = escolher_deck(decks)

    deck_id       = int(deck_escolhido["deck_id"])
    nome_deck     = deck_escolhido["nome"]
    idioma        = deck_escolhido["idioma"].strip().lower()
    arquivo_cards = deck_escolhido["arquivo_cards"]

    if idioma:
        gerar_audios = True
    else:
        print("\n[i] Este deck não tem idioma configurado — gerando sem áudio.")
        gerar_audios = False

    try:
        with open("contents/" + arquivo_cards, encoding="utf-8") as f:
            linhas = list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"[!] Arquivo de cards '{arquivo_cards}' não encontrado.")
        sys.exit(1)

    print(f"\n[+] Deck: {nome_deck}")
    print(f"[+] {len(linhas)} cards encontrados em '{arquivo_cards}'")
    print(f"[+] Áudio: {'sim' if gerar_audios else 'não'}\n")

    deck = genanki.Deck(deck_id, nome_deck)
    arquivos_midia = []

    if gerar_audios:
        PASTA_AUDIO.mkdir(exist_ok=True)
        voz_fixa = None if idioma == "en" else obter_voz(idioma)
        if voz_fixa is None and idioma != "en":
            print(f"[!] Idioma '{idioma}' sem voz configurada em VOZES — gerando sem áudio.")
            gerar_audios = False

    for i, linha in enumerate(linhas, 1):
        frente = linha["frente"].strip()
        verso  = linha["verso"].strip()

        print(f"[{i}/{len(linhas)}] {frente}")

        audio_ok = False
        nome_audio = None

        if gerar_audios:
            voz = obter_voz(idioma)
            print(f"  🎙  voz: {voz}")
            nome_audio = nome_arquivo_audio(frente, idioma, voz)
            caminho_audio = PASTA_AUDIO / nome_audio
            audio_ok = await gerar_audio(frente, voz, caminho_audio, idioma)

            if audio_ok:
                caminho_absoluto = str(caminho_audio.resolve())
                arquivos_midia.append(caminho_absoluto)
                print(f"  ✓ áudio: {nome_audio}")

        # Escolhe o modelo do card conforme houve áudio ou não
        if audio_ok:
            campo_audio = f"[sound:{nome_audio}]"
            nota = genanki.Note(
                model=MODELO_COM_AUDIO,
                fields=[frente, verso, campo_audio],
            )
        else:
            nota = genanki.Note(
                model=MODELO_SEM_AUDIO,
                fields=[frente, verso],
            )

        deck.add_note(nota)

    # Empacota deck + mídias em um único .apkg
    nome_arquivo_saida = re.sub(r"[^\w]", "_", nome_deck.lower()) + ".apkg"
    caminho_saida = PASTA_SAIDA / nome_arquivo_saida

    pacote = genanki.Package(deck)
    pacote.media_files = arquivos_midia
    pacote.write_to_file(str(caminho_saida))

    total_sem_audio = len(linhas) - len(arquivos_midia)
    print(f"\n[✓] Deck gerado: {caminho_saida}")
    print(f"    {len(linhas)} cards | {len(arquivos_midia)} com áudio | {total_sem_audio} sem áudio")
    print(f"\nImporte no Anki: Arquivo → Importar → selecione {caminho_saida}")


if __name__ == "__main__":
    asyncio.run(main())