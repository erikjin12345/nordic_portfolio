# Privat Avanza MCP

En lokal, skrivskyddad MCP-integration för att analysera ett privat
Avanza-konto tillsammans med en separat marknadsdata-integration.

Integrationen använder det inofficiella Python-biblioteket
[`avanza-api`](https://github.com/Qluxzz/avanza). Avanzas interna API kan ändras
utan förvarning. Användningen sker på egen risk.

## Säkerhetsmodell

- MCP-servern exponerar endast läsning av portfölj och transaktioner.
- Inga metoder för orderläggning, fondhandel, överföringar eller månadssparande
  registreras som MCP-verktyg.
- Konto-ID, interna URL-ID och transaktions-ID returneras inte till modellen.
- Användarnamn, lösenord och TOTP-hemlighet lagras i operativsystemets
  nyckelring. De ska aldrig skrivas i chatten, en `.env`-fil eller Git.
- Återbalansering skapar endast ett beräknat förslag. Den utför aldrig handel.

TOTP-hemligheten är en långlivad andra faktor. Behandla den som ett lösenord.

## Installation

Projektet använder Python 3.11+ och `uv`:

```sh
uv sync
```

Lagra därefter uppgifterna lokalt i nyckelringen:

```sh
uv run nordic-avanza-configure
```

Kommandot frågar interaktivt efter uppgifterna och skriver inte ut
lösenordet eller TOTP-hemligheten.

Testa endast att inloggningen fungerar:

```sh
uv run nordic-avanza-check
```

## Anslut till Codex

Registrera stdio-servern lokalt:

```sh
codex mcp add nordic-avanza-private -- \
  uv run --project /Users/erikjin/Desktop/nordic_portfolio \
  nordic-avanza-mcp
```

Starta därefter om Codex och kontrollera att verktygen syns:

```sh
codex mcp get nordic-avanza-private
```

Servern exponerar:

- `avanza_private_connection_status`
- `get_private_portfolio`
- `get_private_transactions`
- `calculate_portfolio_rebalance`

## Arbetsflöde för återbalansering

1. Hämta privata innehav med `get_private_portfolio`.
2. Använd innehavens `instrument_id` med den separata Avanza-MCP:n för färska
   kurser och marknadsdata.
3. Skicka målvikter och färska kurser till `calculate_portfolio_rebalance`.
4. Granska förslaget manuellt och lägg eventuella order själv i Avanza.

Målvikter anges som decimaltal och måste summera till `1.0`:

```json
[
  {"instrument_id": "5479", "target_weight": 0.40},
  {"isin": "SE0000115446", "target_weight": 0.35},
  {"instrument_id": "878733", "target_weight": 0.25}
]
```

Färska marknadsnoteringar kan skickas från den andra integrationen:

```json
[
  {
    "instrument_id": "5479",
    "price": 312.40,
    "fx_rate_to_base": 1.0,
    "as_of": "2026-07-23T15:00:00+02:00"
  }
]
```

`fx_rate_to_base` omvandlar instrumentets noteringsvaluta till portföljens
basvaluta. För svenska instrument noterade i SEK är värdet normalt `1.0`.
Om en färsk notering saknas används Avanzas aktuella portföljvärde och
förslaget markeras med den datakällan.

## Test

Testerna använder endast syntetiska data och kontaktar inte Avanza:

```sh
uv run pytest
```

## Begränsningar

- Detta är inte ett officiellt Avanza-API.
- Kontot har fortfarande full handelsbehörighet hos Avanza även om denna
  MCP-wrapper är skrivskyddad.
- Kurser och valutaomräkning måste vara aktuella för att ett förslag ska vara
  användbart.
- Förslaget tar inte automatiskt hänsyn till skatt, courtage, spread,
  likviditet, minsta orderstorlek eller fonders handelsdagar.
- Resultatet är ett analysunderlag, inte finansiell rådgivning.
