# Hermes Agent — setup local (Mac)

Stack: container Docker do `nousresearch/hermes-agent` rodando em modo `gateway`, com dashboard web em `:9119` e API OpenAI-compatible em `:8642` (bindadas em `127.0.0.1` — só acessíveis deste Mac).

Dados persistentes ficam em `~/.hermes/` (volume montado). A imagem é stateless: dá pra atualizar com `docker compose pull` sem perder nada.

---

## Pré-requisitos

1. Docker Desktop iniciado (ícone da baleia na barra de menu).
2. Token de bot do Telegram pronto (opcional) — pegue com `@BotFather`.
3. Pelo menos uma API key do provedor de modelo (Anthropic, OpenAI ou OpenRouter).

---

## Passo 1 — Wizard interativo (primeira vez, ~5 min)

```bash
mkdir -p ~/.hermes
docker run -it --rm \
  -v ~/.hermes:/opt/data \
  nousresearch/hermes-agent setup
```

O wizard vai pedir:
- Provedor de modelo + API key (Anthropic / OpenAI / OpenRouter / etc.)
- Cliente de chat → escolher **Terminal** e **Telegram** (cola o bot token)
- Identidade/SOUL.md (pode aceitar default e editar depois)

Tudo é gravado em `~/.hermes/.env` e `~/.hermes/config.yaml`.

---

## Passo 2 — Subir o gateway

```bash
cd ~/hermes-agent
docker compose up -d
docker compose logs -f hermes
```

Quando ver `gateway listening on :8642` e `dashboard on :9119`, está pronto.

---

## Passo 3 — Usar

- **Dashboard web**: http://localhost:9119
- **API OpenAI-compatible**: `http://localhost:8642/v1` — Authorization Bearer com a `API_SERVER_KEY` do `.env`
- **CLI dentro do container**:
  ```bash
  docker exec -it hermes /opt/hermes/.venv/bin/hermes
  ```
- **Telegram**: manda mensagem pro seu bot (se configurou no wizard)

Teste rápido da API:
```bash
curl http://localhost:8642/v1/models \
  -H "Authorization: Bearer 3b2ca75323b4ee8fda61f4be3ebd8a296d4d5fb9d3521641"
```

---

## Operação

| Ação | Comando |
|---|---|
| Ver logs | `docker compose logs -f hermes` |
| Reiniciar | `docker compose restart hermes` |
| Parar | `docker compose down` |
| Atualizar versão | `docker compose pull && docker compose up -d` |
| Backup dos dados | `tar -czf hermes-backup-$(date +%F).tgz -C ~ .hermes` |
| Reset total | `docker compose down && rm -rf ~/.hermes` |

---

## Segurança

- As portas estão bindadas em `127.0.0.1` no `docker-compose.yml` — externamente o Mac não expõe nada. Para abrir, troque para `0.0.0.0` e ponha um reverse proxy com TLS na frente.
- Se for versionar este diretório, o `.gitignore` já exclui o `.env`. Use o `.env.example` como template.
- A `API_SERVER_KEY` em `.env` foi gerada com `openssl rand -hex 24`. Não compartilhe.
