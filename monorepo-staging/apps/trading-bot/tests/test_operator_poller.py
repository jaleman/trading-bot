# pyright: reportMissingImports=false

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.services.operator_poller import (  # noqa: E402
    MAX_REPLY_CHARS,
    PollerConfig,
    handle_update,
    is_authorized,
    load_offset,
    looks_like_command,
    save_offset,
)

OPERATOR = "7757313036"
STRANGER = "9999999999"


def config(tmp: Path) -> PollerConfig:
    return PollerConfig(
        bot_token="unused-in-these-tests",
        operator_id=OPERATOR,
        router_script=Path("/bin/echo"),
        state_file=tmp / "state.json",
    )


def update(text: str, sender: str = OPERATOR, chat: str = "123", uid: int = 1) -> dict:
    return {
        "update_id": uid,
        "message": {"text": text, "chat": {"id": chat}, "from": {"id": sender}},
    }


class AuthorizationTests(unittest.TestCase):
    def test_operator_is_authorized(self) -> None:
        self.assertTrue(is_authorized(OPERATOR, OPERATOR))
        self.assertTrue(is_authorized(int(OPERATOR), OPERATOR))  # Telegram sends ints

    def test_everyone_else_is_denied(self) -> None:
        self.assertFalse(is_authorized(STRANGER, OPERATOR))
        self.assertFalse(is_authorized(None, OPERATOR))
        self.assertFalse(is_authorized("", OPERATOR))

    def test_stranger_gets_silence_not_a_rejection_notice(self) -> None:
        """Replying at all would confirm the bot is live to an unknown sender."""
        with tempfile.TemporaryDirectory() as tmp:
            chat, reply = handle_update(config(Path(tmp)), update("/bot balance", sender=STRANGER))
        self.assertIsNone(chat)
        self.assertIsNone(reply)


class CommandRecognitionTests(unittest.TestCase):
    def test_recognises_slash_and_plain_forms(self) -> None:
        for text in ("/bot balance", "/bot", "bot balance", "BOT HOLDINGS", "  /bot status  "):
            self.assertTrue(looks_like_command(text), text)

    def test_recognises_compatibility_aliases(self) -> None:
        for text in ("/balance", "/Holdings", "/info AAPL"):
            self.assertTrue(looks_like_command(text), text)

    def test_ignores_ordinary_chatter(self) -> None:
        for text in ("hello", "what is my balance?", "", "   ", "robot uprising"):
            self.assertFalse(looks_like_command(text), repr(text))


class UpdateHandlingTests(unittest.TestCase):
    def test_command_is_forwarded_to_the_router_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config(Path(tmp))
            with patch("trading_bot.services.operator_poller.run_router",
                       return_value="Balance: cash=$1,848.59") as router:
                chat, reply = handle_update(cfg, update("/bot balance"))

        router.assert_called_once()
        self.assertEqual(router.call_args[0][1], "/bot balance")
        self.assertEqual(chat, "123")
        self.assertIn("1,848.59", reply)

    def test_non_command_from_operator_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            chat, reply = handle_update(config(Path(tmp)), update("good morning"))
        self.assertIsNone(chat)
        self.assertIsNone(reply)

    def test_malformed_update_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config(Path(tmp))
            for bad in ({}, {"message": {}}, {"message": {"text": "/bot balance"}}):
                chat, reply = handle_update(cfg, bad)
                self.assertIsNone(chat)


class RouterOutputTests(unittest.TestCase):
    def test_output_is_truncated_below_the_telegram_limit(self) -> None:
        from trading_bot.services.operator_poller import run_router

        with tempfile.TemporaryDirectory() as tmp:
            cfg = PollerConfig("t", OPERATOR, Path("/bin/echo"), Path(tmp) / "s.json")
            with patch("subprocess.run") as run:
                run.return_value.stdout = "x" * 10_000
                run.return_value.stderr = ""
                run.return_value.returncode = 0
                out = run_router(cfg, "/bot holdings")

        self.assertLessEqual(len(out), MAX_REPLY_CHARS + 20)
        self.assertTrue(out.endswith("truncated."))

    def test_router_timeout_is_reported_not_raised(self) -> None:
        import subprocess

        from trading_bot.services.operator_poller import run_router

        with tempfile.TemporaryDirectory() as tmp:
            cfg = PollerConfig("t", OPERATOR, Path("/bin/echo"), Path(tmp) / "s.json")
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 120)):
                out = run_router(cfg, "/bot balance")

        self.assertIn("timed out", out.lower())


class OffsetTests(unittest.TestCase):
    def test_offset_round_trips_so_restarts_do_not_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            self.assertEqual(load_offset(state), 0)
            save_offset(state, 42)
            self.assertEqual(load_offset(state), 42)

    def test_corrupt_state_falls_back_to_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            state.write_text("{not json", encoding="utf-8")
            self.assertEqual(load_offset(state), 0)


if __name__ == "__main__":
    unittest.main()
