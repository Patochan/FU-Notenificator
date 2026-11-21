import configparser, json, os, tempfile, unittest
from unittest import mock

import FU_Notenificator as n


def make_cfg(enabled="1"):
    cfg = configparser.ConfigParser()
    cfg["BOT"] = {"enabled": enabled}
    return cfg


def make_entry(status="bestanden", versuch="1"):
    # Status kommt aus der Webseite mit führendem Leerzeichen
    return n.createKlausurEntry("1234", " Mathe", "WS22", "2,0", " " + status, "6", None, None, versuch, "01.02.2023")


class CreateEntryTests(unittest.TestCase):
    def test_empty_cells_become_empty_text_not_none(self):
        e = n.createKlausurEntry("1234", " Mathe", "WS22", None, " nicht bestanden", "6", None, None, "1", "01.02.2023")
        self.assertEqual(e["Note"], "")
        self.assertEqual(e["Punkte"], "")
        self.assertEqual(e["Modulname"], "Mathe")

    def test_empty_name_and_status_do_not_crash(self):
        e = n.createKlausurEntry("1234", None, "WS22", "2,0", None, "6", "", "", "1", "01.02.2023")
        self.assertEqual(e["Modulname"], "")
        self.assertEqual(e["Status"], "")


class NotifyTests(unittest.TestCase):
    def test_message_is_passed_without_shell(self):
        msg = 'Grundlagen "Java" $(rm -rf x)'
        with mock.patch.object(n.subprocess, "run") as run:
            run.return_value.returncode = 0
            self.assertTrue(n.notify(msg))
        args = run.call_args[0][0]
        self.assertIn(f"--msg={msg}", args)
        self.assertNotIn("shell", run.call_args[1])


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "store.json")
        n.cacheFile = self.path
        n.cfg = make_cfg()

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_result_is_sent_and_saved(self):
        with mock.patch.object(n, "notify", return_value=True) as notify:
            n.compareKlausurData({"klausuren": [make_entry()]}, {"klausuren": []})
        notify.assert_called_once()
        with open(self.path) as f:
            self.assertEqual(len(json.load(f)["klausuren"]), 1)

    def test_known_result_is_not_sent_again(self):
        old = {"klausuren": [make_entry()]}
        with mock.patch.object(n, "notify") as notify:
            n.compareKlausurData(old, old)
        notify.assert_not_called()

    def test_changed_status_is_sent(self):
        stored = {"klausuren": [make_entry("nicht bestanden")]}
        with mock.patch.object(n, "notify", return_value=True) as notify:
            n.compareKlausurData({"klausuren": [make_entry("bestanden")]}, stored)
        notify.assert_called_once()

    def test_failed_notify_does_not_save(self):
        with mock.patch.object(n, "notify", return_value=False):
            with self.assertRaises(SystemExit):
                n.compareKlausurData({"klausuren": [make_entry()]}, {"klausuren": []})
        self.assertFalse(os.path.exists(self.path))

    def test_empty_fetch_does_not_wipe_saved_results(self):
        with mock.patch.object(n, "notify"):
            with self.assertRaises(SystemExit):
                n.compareKlausurData({"klausuren": []}, {"klausuren": [make_entry()]})
        self.assertFalse(os.path.exists(self.path))

    def test_broken_cache_stops_run(self):
        with open(self.path, "w") as f:
            f.write("{kaputt")
        with self.assertRaises(SystemExit):
            n.getKlausurenStored()


if __name__ == "__main__":
    unittest.main()
