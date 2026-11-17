"""Entry point.

    python -m loki          # voice mode (push Enter to talk)
    python -m loki --text   # type instead of talking
"""
from __future__ import annotations

import argparse
import time

from .agent import Agent
from .brain import OllamaBrain
from .config import settings

EXIT_WORDS = {"exit", "quit", "goodbye", "bye loki", "goodbye loki"}

DIM, CYAN, YELLOW, RESET = "\033[2m", "\033[36m", "\033[33m", "\033[0m"


def confirm_in_terminal(name: str, args: dict) -> bool:
    """Human-in-the-loop check. Always typed, even in voice mode, so a
    misheard word can never approve a dangerous action."""
    print(f"\n{YELLOW}LOKI wants to run {name} with {args}{RESET}")
    return input("Allow? [y/N] ").strip().lower() in {"y", "yes"}


def show_event(kind: str, text: str) -> None:
    prefix = "->" if kind == "tool" else "<-"
    print(f"{DIM}  {prefix} {text}{RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LOKI personal AI agent")
    parser.add_argument("--text", action="store_true", help="type instead of using the microphone")
    parser.add_argument("--quiet", action="store_true", help="don't speak replies aloud")
    args = parser.parse_args()

    agent = Agent(
        brain=OllamaBrain(settings.model, settings.ollama_host),
        confirm=confirm_in_terminal,
        max_steps=settings.max_steps,
        on_event=show_event,
    )

    from .voice.speak import Speaker

    speaker = Speaker(settings.voice)
    listener = None
    if not args.text:
        from .voice.listen import Listener

        print(f"{DIM}Loading speech model ({settings.whisper_model})...{RESET}")
        listener = Listener(settings.whisper_model, device=settings.whisper_device)

    print(f"{CYAN}LOKI online.{RESET} Model: {settings.model}. Say or type 'goodbye' to exit.\n")
    if not args.quiet:
        speaker.say("LOKI online.")

    while True:
        try:
            if listener:
                typed = input(f"{DIM}[press Enter and speak, or type a message]{RESET} ")
                if typed.strip():
                    user_text = typed
                else:
                    print(f"{DIM}listening...{RESET}")
                    try:
                        user_text = listener.listen()
                    except Exception as e:  # mic glitches shouldn't kill LOKI
                        print(f"{YELLOW}Microphone error ({e}). Type your message instead.{RESET}")
                        user_text = input("you: ")
                    else:
                        print(f"you: {user_text}")
            else:
                user_text = input("you: ")
        except (EOFError, KeyboardInterrupt):
            break

        if not user_text.strip():
            continue
        if user_text.strip().lower().rstrip(".!") in EXIT_WORDS:
            break

        print(f"{DIM}  thinking...{RESET}", flush=True)
        started = time.perf_counter()
        try:
            answer = agent.ask(user_text)
        except Exception as e:  # e.g. Ollama not running
            answer = f"I couldn't reach my brain ({type(e).__name__}: {e}). Is Ollama running?"
        print(f"{CYAN}loki:{RESET} {answer} {DIM}({time.perf_counter() - started:.1f}s){RESET}\n")
        if not args.quiet:
            speaker.say(answer)

    print("LOKI offline.")
    if not args.quiet:
        speaker.say("Goodbye.")


if __name__ == "__main__":
    main()
