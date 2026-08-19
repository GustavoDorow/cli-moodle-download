# cli-moodle-download

CLI para baixar os arquivos de uma ou mais seções de uma disciplina no Moodle
Presencial da UFSC.

![Seletor interativo de seções do Moodle](image.png)

## Instalação

1. Instale o [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
   (Linux, macOS e Windows).
2. Clone e prepare o projeto:

```bash
git clone https://github.com/GustavoDorow/cli-moodle-download.git
cd cli-moodle-download
uv sync
```

### Instalação com pip

Como alternativa ao `uv`, crie e ative um ambiente virtual e instale o projeto
pelo `requirements.txt`:

```bash
python -m venv .venv
```

No Linux ou macOS:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

No Windows:

```cmd
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Depois da instalação, use `moodle-section-dl` no lugar de
`uv run moodle-section-dl` nos exemplos abaixo.

## Uso

Abra a página principal da disciplina e copie um link neste formato:

```text
https://presencial.moodle.ufsc.br/course/view.php?id=52983
```

Execute o comando inteiro em uma única linha, mantendo somente as aspas duplas
ao redor do link:

```cmd
uv run moodle-section-dl "https://presencial.moodle.ufsc.br/course/view.php?id=52983"
```

Esse mesmo comando funciona no Prompt de Comando do Windows, no PowerShell e
em terminais Linux e macOS. Não adicione uma barra invertida ao final.

No seletor:

- `↑/↓`: navegar;
- `Espaço`: marcar uma ou mais seções;
- `Enter`: confirmar e baixar.

Os arquivos ficam em
`downloads/<nome da disciplina>/<nome da seção>/`. Por exemplo:

```text
downloads/Análise-e-Projeto-de-Sistemas/Unidade 3/
```

Use o link da disciplina (`/course/view.php?id=...`), não o link de um arquivo
ou atividade (`/mod/resource/...`, `/mod/quiz/...`).
