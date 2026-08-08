from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHINESE_TEXT = re.compile(r"[\u3400-\u9fff]")


class DocumentationLocalizationTest(unittest.TestCase):
    def test_every_english_markdown_has_linked_chinese_translation(self) -> None:
        english_documents = []
        for path in PROJECT_ROOT.rglob("*.md"):
            relative = path.relative_to(PROJECT_ROOT)
            if relative.parts[0] == "doc" or path.name.endswith(".zh-CN.md"):
                continue
            english_documents.append(path)

        self.assertGreaterEqual(len(english_documents), 22)
        for english_path in sorted(english_documents):
            chinese_path = english_path.with_name(
                f"{english_path.stem}.zh-CN{english_path.suffix}"
            )
            relative = english_path.relative_to(PROJECT_ROOT)
            self.assertTrue(chinese_path.is_file(), f"missing translation for {relative}")

            language_switch = (
                f"[English]({english_path.name}) | [简体中文]({chinese_path.name})"
            )
            english_text = english_path.read_text(encoding="utf-8")
            chinese_text = chinese_path.read_text(encoding="utf-8")
            self.assertEqual(
                english_text.splitlines()[0],
                language_switch,
                f"missing Chinese jump in {relative}",
            )
            self.assertEqual(
                chinese_text.splitlines()[0],
                language_switch,
                f"missing English return link in {chinese_path.relative_to(PROJECT_ROOT)}",
            )
            self.assertIsNotNone(
                CHINESE_TEXT.search(chinese_text),
                f"translation contains no Chinese text: {chinese_path}",
            )
            self.assertGreater(
                len(chinese_text),
                80,
                f"translation is unexpectedly short: {chinese_path}",
            )
            self.assertGreater(
                len(chinese_text),
                len(english_text) * 0.45,
                f"translation is incomplete relative to {relative}",
            )
            english_headings = sum(
                line.startswith("#") for line in english_text.splitlines()
            )
            chinese_headings = sum(
                line.startswith("#") for line in chinese_text.splitlines()
            )
            self.assertEqual(
                chinese_headings,
                english_headings,
                f"heading structure drifted for {relative}",
            )
            self.assertEqual(
                chinese_text.count("```"),
                english_text.count("```"),
                f"code-block structure drifted for {relative}",
            )


if __name__ == "__main__":
    unittest.main()
