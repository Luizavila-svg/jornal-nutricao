# jornal-nutri

Projeto reiniciado do zero para coleta e publicação de notícias da área de nutrição.

## Regras ativas do processamento

- Todo texto recebido é traduzido para português.
- O conteúdo é resumido com foco nos dados mais relevantes, em geral entre 15 e 20 linhas (quando houver conteúdo suficiente).
- Na coleta por RSS, o sistema tenta extrair o texto completo da matéria pelo link para gerar resumos mais ricos.
- Blocos gráficos são preservados no resumo (ex.: markdown de imagem e blocos `mermaid`).
- Classificação automática por tema: `clinica`, `esportiva`, `emagrecimento` ou `geral`.
- Score de relevância calculado em escala de 0 a 100.

## Endpoints

- `GET /health`: verificação de saúde da aplicação.
- `GET /`: dashboard web com botão de coleta e listagem.
- `POST /translate`: traduz um texto para português.
- `POST /news/process`: recebe uma notícia, traduz título e conteúdo para português e retorna resumo priorizando dados relevantes (alvo entre 15 e 20 linhas).
- `POST /collect`: coleta feeds RSS/Google News, traduz, resume e salva no SQLite.
- `GET /api/news`: lista notícias salvas com filtros opcionais por tema e score.
- `GET /api/news/count`: retorna total de notícias considerando os mesmos filtros.
- `GET /api/settings`: retorna configuracoes atuais (timezone, horario e score minimo da newsletter).
- `PUT /api/settings`: atualiza configuracoes e reagenda a newsletter automaticamente.
- `POST /api/settings/reset`: restaura configuracoes padrao e reaplica agendamento.
- `GET /export/csv`: exporta notícias em CSV.
- `GET /export/xlsx`: exporta notícias em Excel.
- `POST /newsletter/run`: gera newsletter diária em markdown.

## Como executar

1. Criar e ativar ambiente virtual
2. Instalar dependências
3. Iniciar aplicação

Exemplo:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

Abra `http://127.0.0.1:8010` para usar o dashboard.

## Newsletter automatica

- O sistema agenda a geracao da newsletter diaria no fuso configurado.
- Os arquivos sao salvos em `data/newsletter/newsletter-AAAA-MM-DD.md`.

Variaveis de ambiente:

- `JORNAL_NUTRI_TIMEZONE`: fuso horario da newsletter (padrao: `America/Sao_Paulo`).
- `JORNAL_NUTRI_NEWSLETTER_HOUR`: hora da execucao diaria (padrao: `7`).
- `JORNAL_NUTRI_NEWSLETTER_MINUTE`: minuto da execucao diaria (padrao: `0`).

Painel de configuracoes no dashboard:

- Ajusta timezone e horario da newsletter sem editar variavel de ambiente.
- Ajusta score minimo da newsletter em tempo real.
- Exibe validacao por campo e permite restaurar padrao com um clique.

Notificacoes opcionais apos gerar newsletter:

- Email SMTP: `JORNAL_NUTRI_SMTP_HOST`, `JORNAL_NUTRI_SMTP_PORT`, `JORNAL_NUTRI_SMTP_USER`, `JORNAL_NUTRI_SMTP_PASSWORD`, `JORNAL_NUTRI_SMTP_FROM`, `JORNAL_NUTRI_SMTP_TO`.
- Telegram: `JORNAL_NUTRI_TELEGRAM_BOT_TOKEN`, `JORNAL_NUTRI_TELEGRAM_CHAT_ID`.

Busca e paginacao:

- `GET /api/news?limit=10&offset=0&q=creatina&theme=esportiva&min_score=40`

Exemplo para processar notícia:

```bash
curl -X POST http://127.0.0.1:8010/news/process \
	-H "Content-Type: application/json" \
	-d '{
		"title": "Nutrition update",
		"content": "Long foreign language text...",
		"source": "rss",
		"language": "auto"
	}'
```

## Deploy no Railway

1. Faça commit e push deste projeto para o GitHub.
2. No Railway, clique em `New Project` e escolha `Deploy from GitHub repo`.
3. Selecione o repositório do projeto.
4. O Railway vai detectar Python e instalar `requirements.txt`.
5. O start command já está configurado em `railway.json`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

6. Após o deploy, abra a URL pública gerada pelo Railway.

Variáveis de ambiente recomendadas no Railway:

- `JORNAL_NUTRI_TIMEZONE`
- `JORNAL_NUTRI_NEWSLETTER_HOUR`
- `JORNAL_NUTRI_NEWSLETTER_MINUTE`
- `JORNAL_NUTRI_NEWSLETTER_MIN_SCORE`

Observação importante sobre dados:

- O projeto usa SQLite local (`data/jornal_nutri.db`). Em cloud, esse armazenamento pode ser efêmero e ser perdido em reinícios/novos deploys.
- Para produção estável, o próximo passo é migrar para PostgreSQL.
