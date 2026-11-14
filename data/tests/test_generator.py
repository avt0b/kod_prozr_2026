"""Тесты генератора: детерминизм, проверки data-check, разметка демо-кейсов.

python -m unittest discover -s data/tests -t .
"""

import json
import tempfile
import unittest
from pathlib import Path

from data.generator.__main__ import generate, sample, write
from data.generator.check import run
from data.generator.ids import inn_legal, inn_person, is_valid_inn, is_valid_ogrn, ogrn
from data.generator.names import FullName


class GeneratorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows, cls.truth, cls.scenario = generate(42, 600_000)

    def test_deterministic(self) -> None:
        again, truth, _ = generate(42, 600_000)
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(self.rows, sort_keys=True))
        self.assertEqual(truth["schemes"], self.truth["schemes"])

    def test_full_set_and_sample_pass_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            for name, items in self.rows.items():
                write(out / f"{name}.json", items)
            for name in ("schemes", "appeals_labels", "peer_anomalies"):
                write(out / "_truth" / f"{name}.json", self.truth[name])
            self.assertEqual(run(out).errors, [])
            part = out / "sample"
            for name, items in sample(self.rows, self.scenario).items():
                write(part / f"{name}.json", items)
            self.assertEqual(run(part, partial=True).errors, [])

    def test_demo_cases_in_truth(self) -> None:
        by_case = {s["case_id"]: s["rule_codes"] for s in self.truth["schemes"]}
        self.assertEqual(by_case["H1"], ["R01", "R05", "R06", "R07"])
        self.assertEqual(by_case["C2"], ["R02"])
        self.assertEqual(by_case["C6"], ["R08"])
        self.assertTrue(any(not rules for rules in by_case.values()), "нет шумовых кейсов")

    def test_one_appeal_stays_new_for_live_demo(self) -> None:
        keep = [label for label in self.truth["appeals_labels"] if label["keep_new"]]
        self.assertEqual(len(keep), 1)
        self.assertEqual(keep[0]["category"], "conflict_of_interest")

    def test_requisites_checksums(self) -> None:
        import random

        rng = random.Random(1)
        for _ in range(50):
            self.assertTrue(is_valid_inn(inn_legal(rng)))
            self.assertTrue(is_valid_inn(inn_person(rng)))
            self.assertTrue(is_valid_ogrn(ogrn(rng, 2015)))

    def test_declension(self) -> None:
        name = FullName("Соколов", "Андрей", "Викторович", "m")
        self.assertEqual(name.full_in("dat"), "Соколову Андрею Викторовичу")
        self.assertEqual(name.name_patronymic_surname("gen"), "Андрея Викторовича Соколова")
        self.assertEqual(
            FullName("Белова", "Ирина", "Андреевна", "f").full_in("gen"), "Беловой Ирины Андреевны"
        )


if __name__ == "__main__":
    unittest.main()
