# moodle-section-dl

CLI para baixar os arquivos de uma seção específica de um curso no Moodle da
UFSC. Ele autentica pelo CAS, localiza a seção pelo título e baixa recursos,
pastas e anexos servidos pelo Moodle. Atividades interativas sem arquivo, como
questionários e tarefas, são informadas e ignoradas.

## Instalação

Requer Python 3.11 ou mais recente e [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Uso

Primeiro, liste as seções disponíveis no curso:

```bash
uv run moodle-section-dl \
  'https://presencial.moodle.ufsc.br/course/view.php?id=52983' \
  --list-sections
```

Depois, escolha uma seção pelo título completo ou por um trecho único:

```bash
uv run moodle-section-dl \
  'https://presencial.moodle.ufsc.br/course/view.php?id=52983' \
  --section 'Unidade 3 - Gerência de Memória' \
  --output ./downloads
```

O CLI procura primeiro as credenciais em um arquivo `.env` no diretório atual.
Crie-o a partir do exemplo:

```bash
cp .env.example .env
chmod 600 .env
```

Preencha o arquivo:

```dotenv
UFSC_USERNAME=seu_idufsc
UFSC_PASSWORD=sua_senha
```

O `.env` está ignorado pelo Git. Como ele contém a senha em texto simples,
mantenha as permissões restritas e nunca o envie ou faça commit dele. Se uma
credencial não estiver no arquivo, o CLI a pede de modo interativo. A senha não
aparece no terminal.

O resultado do exemplo fica em:

```text
downloads/Unidade 3 - Gerência de Memória/
```

Variáveis já exportadas no ambiente têm precedência sobre o conteúdo do `.env`:

```bash
UFSC_USERNAME=seu_id UFSC_PASSWORD='...' uv run moodle-section-dl \
  'https://presencial.moodle.ufsc.br/course/view.php?id=52983' \
  -s 'Gerência de Memória'
```

Evite colocar a senha diretamente em scripts compartilhados ou no histórico do
shell. Sem `--overwrite`, colisões recebem sufixos como `arquivo (2).pdf`.

## Opções

```text
-s, --section TEXT  Nome completo ou trecho único da seção
--list-sections      Lista as seções disponíveis sem baixar arquivos
-o, --output PATH   Diretório de destino (padrão: ./downloads)
-u, --username ID   idUFSC; também aceita UFSC_USERNAME
--overwrite         Sobrescreve arquivos com o mesmo nome
--timeout SEGUNDOS  Timeout de cada requisição HTTP (padrão: 30)
```

## Desenvolvimento

```bash
uv sync --dev
uv run pytest
```

O login reutiliza a mesma estratégia do projeto `assistente-ufsc`: mantém uma
sessão HTTP, copia os campos ocultos do formulário CAS e segue o retorno ao
serviço da UFSC. Não há dependência de Selenium nem necessidade de instalar um
navegador.
