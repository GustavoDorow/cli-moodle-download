# moodle-section-dl

CLI para baixar os arquivos de uma seção específica de um curso no Moodle da
UFSC. Ele autentica pelo CAS, localiza a seção pelo título e baixa recursos,
pastas e anexos servidos pelo Moodle. Atividades interativas sem arquivo, como
questionários e tarefas, são informadas e ignoradas.

## Passo a passo

### 1. Instale o projeto

Requer Python 3.11 ou mais recente, Git e
[`uv`](https://docs.astral.sh/uv/). Clone o repositório e instale as
dependências:

```bash
git clone git@github.com:GustavoDorow/cli-moodle-download.git
cd cli-moodle-download
uv sync
```

### 2. Copie o link da disciplina

Entre no [Moodle Presencial da UFSC](https://presencial.moodle.ufsc.br/), abra
a disciplina desejada em **Meus cursos** e copie a URL da barra de endereço.

O CLI espera o link da página principal da disciplina, que normalmente tem
este formato:

```text
https://presencial.moodle.ufsc.br/course/view.php?id=52983
```

O número após `id=` identifica o curso e será diferente para cada disciplina e
semestre. Um fragmento de seção no final, como `#section-4`, não causa problema.

Não use o link de um PDF, questionário ou outra atividade individual. Links com
formatos como os seguintes não representam a disciplina inteira:

```text
https://presencial.moodle.ufsc.br/mod/resource/view.php?id=...
https://presencial.moodle.ufsc.br/mod/quiz/view.php?id=...
```

Se estiver dentro de uma atividade, clique no nome da disciplina na navegação
do Moodle antes de copiar a URL.

### 3. Configure as credenciais (opcional)

O CLI pode solicitar o idUFSC e a senha a cada execução. Para carregá-los
automaticamente, crie um `.env` a partir do exemplo:

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
credencial estiver ausente ou se o `.env` não existir, o CLI pergunta somente o
valor que estiver faltando. A senha digitada não aparece no terminal.

### 4. Execute com o link da disciplina

Execute somente o comando com a URL do curso:

```bash
uv run moodle-section-dl \
  'https://presencial.moodle.ufsc.br/course/view.php?id=52983'
```

O CLI mostra todas as seções em um seletor interativo. Use `↑/↓` para navegar,
`Espaço` para marcar uma ou várias seções e `Enter` para confirmar o download.

Exemplo do seletor:

```text
? Selecione as seções para baixar:
  ○ Geral
  ○ Unidade 1 - Introdução
» ◉ Unidade 3 - Gerência de Memória
  ○ Bibliografia Indicada
```

### 5. Encontre os arquivos baixados

Por padrão, cada seção recebe uma pasta dentro de `downloads/`:

```text
downloads/
└── Unidade 3 - Gerência de Memória/
    ├── ine5412-memoria-fisica-espacos-enderecamento.pdf
    ├── ine5412-memoria-virtual-paginacao.pdf
    └── ...
```

Atividades interativas sem arquivo, como questionários, aparecem no relatório
como ignoradas. Sem `--overwrite`, arquivos com nomes repetidos recebem sufixos
como `arquivo (2).pdf`.

## Outros modos de uso

Para baixar uma seção diretamente, sem abrir o seletor:

```bash
uv run moodle-section-dl \
  'https://presencial.moodle.ufsc.br/course/view.php?id=52983' \
  --section 'Unidade 3 - Gerência de Memória' \
  --output ./downloads
```

Para apenas conferir os títulos disponíveis:

```bash
uv run moodle-section-dl \
  'https://presencial.moodle.ufsc.br/course/view.php?id=52983' \
  --list-sections
```

Variáveis já exportadas no ambiente têm precedência sobre o conteúdo do `.env`:

```bash
UFSC_USERNAME=seu_id UFSC_PASSWORD='...' uv run moodle-section-dl \
  'https://presencial.moodle.ufsc.br/course/view.php?id=52983' \
  -s 'Gerência de Memória'
```

Evite colocar a senha diretamente em scripts compartilhados ou no histórico do
shell.

## Opções

```text
-s, --section TEXT  Nome completo ou trecho único da seção
--list-sections      Lista as seções disponíveis sem baixar arquivos
-o, --output PATH   Diretório de destino (padrão: ./downloads)
-u, --username ID   idUFSC; também aceita UFSC_USERNAME
--overwrite         Sobrescreve arquivos com o mesmo nome
--timeout SEGUNDOS  Timeout de cada requisição HTTP (padrão: 30)
```

## Problemas comuns

- **Login recusado:** confira o idUFSC e a senha. Se estiver usando `.env`,
  verifique se não deixou os valores de exemplo no arquivo.
- **Curso inacessível:** abra o mesmo link no navegador e confirme que a sua
  conta está matriculada na disciplina.
- **Nenhuma seção encontrada:** confira se a URL contém `/course/view.php?id=`;
  links `/mod/resource/`, `/mod/quiz/` ou `/mod/assign/` são de atividades.
- **Seção não encontrada com `--section`:** execute `--list-sections` ou use o
  seletor para ver o título exatamente como aparece no Moodle.

## Desenvolvimento

```bash
uv sync --dev
uv run pytest
```

O login reutiliza a mesma estratégia do projeto `assistente-ufsc`: mantém uma
sessão HTTP, copia os campos ocultos do formulário CAS e segue o retorno ao
serviço da UFSC. Não há dependência de Selenium nem necessidade de instalar um
navegador.
