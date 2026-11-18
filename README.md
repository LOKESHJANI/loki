# LOKI 🜲

**A local, voice-driven personal AI agent for macOS.** Ask LOKI out loud to find files, read documents, open apps and websites, or run commands. It decides which tools to use, runs them safely, and answers back in voice.

Everything runs **on your own machine**: the LLM (Ollama), speech-to-text (Whisper) and text-to-speech (macOS `say`). No API keys, no cloud, no data leaves your laptop.

```
you:  "Find my resume in Documents and tell me when I last updated it"
  -> search_files({'folder': '~/Documents', 'pattern': '*resume*'})
  <- /Users/bharath/Documents/Bharath_Resume_2026.pdf
loki: I found Bharath_Resume_2026.pdf in your Documents folder.
```

## Architecture

```
 🎤 mic ──> Whisper (STT) ──┐
                            v
                    ┌──────────────┐   tool schemas   ┌──────────────┐
  you (text) ─────> │    Agent     │ ───────────────> │ Brain (LLM)  │
                    │  ReAct loop  │ <─────────────── │ Ollama       │
                    └──────┬───────┘   tool calls     └──────────────┘
                           │
              ┌────────────┼─────────────┐
              v            v             v
         Safety layer   Tool registry   History
         (sandbox +     files / system
          confirm)      / browser ...
                           │
 🔊 macOS say <────────── answer
```

| Module | Job |
|---|---|
| `loki/brain.py` | Adapter around the LLM; swap Ollama for Claude/OpenAI without touching anything else |
| `loki/agent.py` | The think → act → observe loop, with a step limit and error handling |
| `loki/tools/` | Python functions the LLM may call; JSON schemas are generated from type hints + docstrings |
| `loki/safety.py` | Folder sandbox, plus confirmation before any `dangerous=True` tool |
| `loki/voice/` | Offline speech in (faster-whisper) and out (`say`) |

## Quick start (macOS)

```bash
# 1. Install Ollama and pull a model that supports tool calling
brew install ollama portaudio
ollama serve &              # or open the Ollama app
ollama pull qwen2.5:3b     # 8 GB Mac; use qwen2.5:7b with 16 GB+

# 2. Set up LOKI
git clone https://github.com/<you>/loki.git && cd loki
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Run
python -m loki --text       # typed chat
python -m loki              # voice: press Enter, speak, pause
```

The first voice run downloads the Whisper model (~150 MB), and macOS will ask for microphone permission for your terminal.

Configuration is in environment variables; see `.env.example`.

## Developing in VS Code

1. `File → Open Folder…` → `loki`. Accept the "install recommended extensions" prompt.
2. In the integrated terminal (`` Ctrl+` ``): `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env`
3. `Cmd+Shift+P` → **Python: Select Interpreter** → `.venv`.
4. **Run and Debug** sidebar (`Cmd+Shift+D`) → pick **LOKI: text mode** or **LOKI: voice mode** → ▶ (F5).
5. **Testing** sidebar (beaker icon) runs the pytest suite.

Tip: set a breakpoint in `Agent.ask()` in `loki/agent.py` and step through to watch each think → act → observe cycle.

Voice mode: macOS must allow **Visual Studio Code** under System Settings → Privacy & Security → Microphone.

## Tools

| Tool | Phase | Needs your OK? |
|---|---|---|
| `list_directory`, `read_file`, `search_files` | 1 | No (sandboxed) |
| `write_file` | 1 | **Yes** |
| `get_datetime`, `open_application`, `open_url` | 1 | No |
| `run_shell_command` | 1 | **Yes** |
| `web_search` | 2 | No |
| `read_webpage` | 2 | No (public sites only) |

```
you:  "Who is the current Chief Minister of Tamil Nadu?"
  -> web_search({'query': 'current Chief Minister of Tamil Nadu'})
  <- 1. ... (snippets from the web)
loki: According to ..., the Chief Minister is ...
```

## Tests

```bash
pytest -q
```
The tests use a fake brain, so they run in milliseconds without Ollama or a microphone.

## Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md). Next up: Gmail, long-term memory, wake word and a web dashboard.

## Learn how it works

[`docs/LEARNING.md`](docs/LEARNING.md) walks through every concept behind LOKI, step by step.

## License
MIT
