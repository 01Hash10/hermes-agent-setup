# Hermes Agent — setup local (Mac)

Stack: container Docker do `nousresearch/hermes-agent` rodando em modo `gateway`, com dashboard web em `:9119` e API OpenAI-compatible em `:8642` (bindadas em `127.0.0.1` — só acessíveis desta máquina).

Dados persistentes do agente (sessions, memories, skills, API keys do wizard) ficam em `./data/` — uma subpasta deste projeto, **ignorada pelo Git**. A imagem do container é stateless: dá pra atualizar com `docker compose pull` sem perder nada do estado.

> Como `./data/` é um path relativo, basta clonar este repo para o disco que você quiser (interno, SSD externo, NAS) e tudo — configs e estado — fica junto.

---

## Pré-requisitos

1. Docker Desktop iniciado (ícone da baleia na barra de menu).
2. Token de bot do Telegram pronto (opcional) — pegue com `@BotFather`.
3. Pelo menos uma API key de provedor de modelo (Anthropic, OpenAI, OpenRouter, etc.).

---

## Passo 0 — Configurar segredos locais

```bash
cp .env.example .env
# substitua o placeholder por uma chave forte
sed -i '' "s/CHANGE_ME_openssl_rand_hex_24/$(openssl rand -hex 24)/" .env
```

---

## Passo 1 — Wizard interativo (primeira vez, ~5 min)

```bash
mkdir -p data
docker run -it --rm \
  -v "$PWD/data:/opt/data" \
  nousresearch/hermes-agent setup
```

O wizard vai pedir:
- Provedor de modelo + API key (Anthropic / OpenAI / OpenRouter / etc.)
- Cliente(s) de chat (Terminal, Telegram, Discord, Slack, WhatsApp, Signal)
- Identidade/SOUL.md (pode aceitar default e editar depois)

Tudo é gravado em `./data/.env` e `./data/config.yaml`.

---

## Passo 2 — Subir o gateway

```bash
docker compose up -d
docker compose logs -f hermes
```

Quando ver `gateway listening on :8642` e `dashboard on :9119`, está pronto.

---

## Passo 3 — Usar

- **Dashboard web**: http://localhost:9119
- **API OpenAI-compatible**: `http://localhost:8642/v1` — header `Authorization: Bearer <API_SERVER_KEY do .env>`
- **CLI dentro do container**:
  ```bash
  docker exec -it hermes /opt/hermes/.venv/bin/hermes
  ```
- **Telegram**: manda mensagem pro seu bot (se configurou no wizard)

Teste rápido da API (lê a key direto do `.env` local, sem expor):
```bash
source .env && curl http://localhost:8642/v1/models \
  -H "Authorization: Bearer $API_SERVER_KEY"
```

---

## Operação

| Ação | Comando |
|---|---|
| Ver logs | `docker compose logs -f hermes` |
| Reiniciar | `docker compose restart hermes` |
| Parar | `docker compose down` |
| Atualizar versão | `docker compose pull && docker compose up -d` |
| Backup do estado | `tar -czf hermes-backup-$(date +%F).tgz data/` |
| Reset total | `docker compose down && rm -rf data/` |

---

## Storage do Docker em disco externo (opcional, macOS)

Se o disco interno do Mac estiver apertado, mova o storage do Docker (imagens, volumes, cache) para um SSD externo APFS:

1. **Docker Desktop → Settings → Resources → Advanced**
2. Em **Disk image location**, aponte para uma pasta no SSD externo (ex.: `/Volumes/<seu-ssd>/Docker`)
3. **Apply & Restart** — o Docker migra o `Docker.raw` existente para o novo path.

Cuidado: o SSD precisa estar montado sempre que o Docker for usado. Se desmontar, os containers param até remontar.

---

## Segurança

- As portas estão bindadas em `127.0.0.1` no `docker-compose.yml` — externamente esta máquina não expõe nada. Para abrir, troque para `0.0.0.0` e ponha um reverse proxy com TLS na frente.
- O `.gitignore` exclui `.env` e `data/`. Use o `.env.example` como template ao versionar.
- A `API_SERVER_KEY` em `.env` foi gerada com `openssl rand -hex 24`. Não compartilhe; rotacione se vazar.
