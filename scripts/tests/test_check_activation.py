import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("check_activation", ROOT / "eval/activation/check_activation.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def assistant(name, **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


def jsonl(events):
    return "\n".join(json.dumps(e) for e in events) + "\n"


CASES = {"skill": "ezorca", "cases": [
    {"id": "favor-a", "level": "favor"}, {"id": "neutro-a", "level": "neutro"}, {"id": "contra-a", "level": "contra"}]}
LOADED = [{"type": "system"}, assistant("Skill", skill="ezorca")]
PLAIN = [{"type": "system"}, assistant("Read", file_path="C:/repo/scripts/x.py")]


class LoadViaTests(unittest.TestCase):
    def test_skill_tool(self):
        self.assertEqual(mod.load_via(LOADED, "ezorca"), "Skill")

    def test_other_skill_does_not_count(self):
        self.assertIsNone(mod.load_via([assistant("Skill", skill="orchestration")], "ezorca"))

    def test_read_skill_file_with_backslashes(self):
        event = assistant("Read", file_path="C:\\Users\\x\\.agents\\skills\\ezorca\\SKILL.md")
        self.assertEqual(mod.load_via([event], "ezorca"), "Read")

    def test_read_other_file_does_not_count(self):
        self.assertIsNone(mod.load_via([assistant("Read", file_path="/a/ezorca/README.md")], "ezorca"))

    def test_user_events_ignored(self):
        block = {"type": "tool_use", "name": "Skill", "input": {"skill": "ezorca"}}
        event = {"type": "user", "message": {"content": [block]}}
        self.assertIsNone(mod.load_via([event], "ezorca"))

    def test_text_blocks_and_odd_input_tolerated(self):
        content = [{"type": "text", "text": "hola"}, {"type": "tool_use", "name": "Skill", "input": None}]
        event = {"type": "assistant", "message": {"content": content}}
        self.assertIsNone(mod.load_via([event], "ezorca"))


class EvaluateTests(unittest.TestCase):
    def run_dir(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for name, events in files.items():
            text = events if isinstance(events, str) else jsonl(events)
            (Path(tmp.name) / name).write_text(text, encoding="utf-8")
        return Path(tmp.name)

    def test_criteria_met_and_neutral_informative(self):
        d = self.run_dir({"favor-a__haiku.jsonl": LOADED, "neutro-a__haiku.jsonl": LOADED,
                          "contra-a__haiku.jsonl": PLAIN})
        report = mod.evaluate(CASES, d)
        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"]["neutro"], {"runs": 1, "loaded": 1})
        self.assertIsNone([r for r in report["runs"] if r["level"] == "neutro"][0]["ok"])

    def test_favor_not_loaded_fails(self):
        d = self.run_dir({"favor-a__haiku.jsonl": PLAIN, "neutro-a__haiku.jsonl": PLAIN,
                          "contra-a__haiku.jsonl": PLAIN})
        self.assertFalse(mod.evaluate(CASES, d)["ok"])

    def test_contra_loaded_fails(self):
        d = self.run_dir({"favor-a__haiku.jsonl": LOADED, "neutro-a__haiku.jsonl": PLAIN,
                          "contra-a__haiku.jsonl": LOADED})
        self.assertFalse(mod.evaluate(CASES, d)["ok"])

    def test_invalid_inputs(self):
        with self.assertRaises(mod.InvalidInput):
            mod.evaluate(CASES, self.run_dir({"favor-a__haiku.jsonl": LOADED}))
        d = self.run_dir({"favor-a__h.jsonl": "no json\n", "neutro-a__h.jsonl": LOADED,
                          "contra-a__h.jsonl": PLAIN})
        with self.assertRaises(mod.InvalidInput):
            mod.evaluate(CASES, d)
        with self.assertRaises(mod.InvalidInput):
            mod.parse_events("\n\n", "vacío")

    def test_main_exit_codes(self):
        d = self.run_dir({"favor-a__h.jsonl": LOADED, "neutro-a__h.jsonl": PLAIN,
                          "contra-a__h.jsonl": PLAIN})
        cases = d / "cases.json"
        cases.write_text(json.dumps(CASES), encoding="utf-8")
        self.assertEqual(mod.main(["--cases", str(cases), "--results", str(d)]), 0)
        (d / "contra-a__h.jsonl").write_text(jsonl(LOADED), encoding="utf-8")
        self.assertEqual(mod.main(["--cases", str(cases), "--results", str(d)]), 1)
        self.assertEqual(mod.main(["--cases", str(cases), "--results", str(d / "nada")]), 2)


if __name__ == "__main__":
    unittest.main()
