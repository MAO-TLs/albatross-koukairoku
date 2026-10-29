"""Exercise the actual release ZIP on disposable copies, never the retail install."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from build_release import PACKAGE, RELEASE, VERSION
from build_script_patch import GAME_ROOT, PATCH_ROOT
import install_patch as installer


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='albatross-install-test-')
        self.root = Path(self.temp.name)
        with zipfile.ZipFile(RELEASE / (PACKAGE.name + '.zip')) as archive:
            archive.extractall(self.root / 'download')
        self.package = self.root / 'download' / PACKAGE.name
        self.game = self.root / 'ゲーム installation'
        self.game.mkdir()
        for name in installer.FILES:
            source = PATCH_ROOT / 'work/exe/albatross-original.exe' if name == 'Albatross.exe' else GAME_ROOT / name
            shutil.copy2(source, self.game / name)
        self.save = self.game / 'save0004.dat'
        self.save.write_bytes(b'Untouched player progress')
        self.original = self.snapshot()
        self.manifest = json.loads((self.package / 'patch.json').read_text())

    def tearDown(self): self.temp.cleanup()
    def snapshot(self): return {p.name:installer.file_hash(p) for p in self.game.iterdir() if p.is_file()}
    def run_install(self, uninstall=False): return installer.install(self.package,self.game,uninstall)
    def assert_original(self): self.assertEqual(self.snapshot(), self.original)

    def test_clean_install_reinstall_restore_and_reinstall(self):
        self.run_install()
        expected = {f['name']:f['output_sha256'] for f in self.manifest['files']}
        for name, digest in expected.items():
            self.assertEqual(installer.file_hash(self.game/name),digest)
            self.assertEqual(installer.file_hash(self.game/installer.BACKUP/name),self.original[name])
        self.assertEqual(installer.file_hash(self.game/'Fonts'/installer.FONT),self.manifest['font_sha256'])
        installed = self.snapshot()
        self.run_install()
        self.assertEqual(self.snapshot(),installed)
        self.run_install(uninstall=True)
        self.assert_original()
        self.assertFalse((self.game/'Fonts'/installer.FONT).exists())
        self.assertTrue((self.game/installer.BACKUP/installer.FONT).is_file())
        self.run_install()
        self.assertEqual(self.snapshot(),installed)
        self.assertEqual(self.save.read_bytes(),b'Untouched player progress')

    def test_wrong_edition_rejected_before_mutation(self):
        (self.game/'scr.xfl').chmod(0o644)  # Disc-derived test copies are read-only
        (self.game/'scr.xfl').write_bytes(b'Wrong edition')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError,'supported Japanese'): self.run_install()
        self.assertEqual(before,self.snapshot())
        self.assertFalse((self.game/installer.BACKUP).exists())

    def test_damaged_payload_rejected_before_mutation(self):
        (self.package/'patch.dat.gz').write_bytes(b'Damaged')
        with self.assertRaisesRegex(ValueError,'Damaged patch data'): self.run_install()
        self.assert_original()
        self.assertFalse((self.game/installer.BACKUP).exists())

    def test_bad_delta_output_rejected_before_mutation(self):
        self.manifest['files'][0]['operations'][0][2] = 1
        (self.package/'patch.json').write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError,'Output'): self.run_install()
        self.assert_original()
        self.assertFalse((self.game/installer.BACKUP).exists())

    def test_conflicting_backup_rejected_before_mutation(self):
        saved = self.game/installer.BACKUP
        saved.mkdir()
        (saved/'grps.xfl').write_bytes(b'An unrelated backup')
        with self.assertRaisesRegex(ValueError,'Conflicting original backup'): self.run_install()
        self.assert_original()

    def test_replacement_failure_rolls_back_every_changed_game_file(self):
        real_replace = installer.os.replace
        calls = 0
        def replace(source,target):
            nonlocal calls
            calls += 1
            if calls == 2: raise OSError('Simulated disk failure')
            return real_replace(source,target)
        with patch.object(installer.os,'replace',side_effect=replace):
            with self.assertRaisesRegex(OSError,'Simulated disk failure'): self.run_install()
        self.assert_original()
        self.assertFalse((self.game/'Fonts'/installer.FONT).exists())
        self.run_install()

    def test_font_failure_after_files_rolls_back_files(self):
        (self.game/'Fonts').write_bytes(b'Unrelated file')
        before = self.snapshot()
        with self.assertRaises(FileExistsError): self.run_install()
        self.assertEqual(before,self.snapshot())

    def test_lowercase_retail_executable_keeps_its_name(self):
        (self.game/'Albatross.exe').rename(self.game/'albatross.exe')
        self.run_install()
        self.assertTrue((self.game/'albatross.exe').is_file())
        self.assertNotIn('Albatross.exe', [p.name for p in self.game.iterdir()])
        self.run_install(uninstall=True)
        self.assertEqual(installer.file_hash(self.game/'albatross.exe'),self.original['Albatross.exe'])

    def test_initial_v1_install_upgrades_and_restores(self):
        old_zip = PATCH_ROOT / 'reports/pre-hotfix-v1.0.0/Albatross-Koukairoku-English-v1.0.0.zip'
        self.assertEqual(installer.file_hash(old_zip), '744f7f3bf3e78379310a8ffe081c8a591953d342eea172712ef0fbca2fa63ac2')
        with zipfile.ZipFile(old_zip) as archive:
            archive.extractall(self.root / 'initial-release')
        old_package = self.root / 'initial-release' / 'Albatross-Koukairoku-English-v1.0.0'
        installer.install(old_package, self.game)
        self.assertEqual(installer.file_hash(self.game/'grps.xfl'), installer.PREVIOUS_OUTPUTS['grps.xfl'][0])
        backups = {n:installer.file_hash(self.game/installer.BACKUP/n) for n in installer.FILES}
        self.run_install()
        for row in self.manifest['files']:
            self.assertEqual(installer.file_hash(self.game/row['name']),row['output_sha256'])
            self.assertEqual(installer.file_hash(self.game/installer.BACKUP/row['name']),backups[row['name']])
        self.assertEqual(self.save.read_bytes(), b'Untouched player progress')
        self.run_install()
        self.run_install(uninstall=True)
        self.assert_original()

    def test_previous_ui_without_original_backup_is_rejected(self):
        (self.game/'grps.xfl').chmod(0o644)  # Only this disposable disc-derived test copy.
        shutil.copy2(PATCH_ROOT/'reports/pre-hotfix-v1.0.0/grps.xfl', self.game/'grps.xfl')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Original backup missing'):
            self.run_install()
        self.assertEqual(before, self.snapshot())

    def test_published_stop_voice_hotfix_upgrades_to_crash_fix(self):
        old_zip = PATCH_ROOT / 'reports/published-v1.0.0-hotfix.zip'
        self.assertEqual(installer.file_hash(old_zip),
                         '6920c784ea3373865a068877afe00d718ac9306343b40b2066bd89a5e35b4008')
        with zipfile.ZipFile(old_zip) as archive:
            archive.extractall(self.root / 'stop-voice-hotfix')
        old_package = self.root / 'stop-voice-hotfix' / 'Albatross-Koukairoku-English-v1.0.0'
        old_installer = {}
        exec((old_package / 'install_patch.py').read_text(), old_installer)
        old_installer['install'](old_package, self.game)
        self.assertEqual(installer.file_hash(self.game / 'Albatross.exe'),
                         installer.PREVIOUS_OUTPUTS['Albatross.exe'][0])
        self.run_install()
        expected = {row['name']: row['output_sha256'] for row in self.manifest['files']}
        for name, digest in expected.items():
            self.assertEqual(installer.file_hash(self.game / name), digest)
        self.assertEqual(self.save.read_bytes(), b'Untouched player progress')
        self.run_install(uninstall=True)
        self.assert_original()

    def test_published_crash_hotfix_upgrades_to_text_speed_fix(self):
        old_zip = PATCH_ROOT / 'reports/published-v1.0.0-crash-hotfix.zip'
        self.assertEqual(installer.file_hash(old_zip),
                         '8dbc045d0a50815c7a9054f5b6da167400e15eaf59003672e598c68347f93d5f')
        with zipfile.ZipFile(old_zip) as archive:
            archive.extractall(self.root / 'crash-hotfix')
        old_package = self.root / 'crash-hotfix' / 'Albatross-Koukairoku-English-v1.0.0'
        old_installer = {}
        exec((old_package / 'install_patch.py').read_text(), old_installer)
        old_installer['install'](old_package, self.game)
        self.assertEqual(installer.file_hash(self.game / 'Albatross.exe'),
                         installer.PREVIOUS_OUTPUTS['Albatross.exe'][1])
        self.run_install()
        for row in self.manifest['files']:
            self.assertEqual(installer.file_hash(self.game / row['name']), row['output_sha256'])
            self.assertEqual(installer.file_hash(self.game / installer.BACKUP / row['name']),
                             self.original[row['name']])
        self.assertEqual(self.save.read_bytes(), b'Untouched player progress')
        self.run_install(uninstall=True)
        self.assert_original()

    def test_published_readability_hotfix_upgrades_to_choice_fix(self):
        old_zip = PATCH_ROOT / 'reports/published-v1.0.0-readability-hotfix.zip'
        self.assertEqual(installer.file_hash(old_zip),
                         'ee940d1201fdebc3fef3d29a5875101dba773d3bcf72fc39127f86e6b5130f6a')
        with zipfile.ZipFile(old_zip) as archive:
            archive.extractall(self.root / 'readability-hotfix')
        old_package = self.root / 'readability-hotfix' / 'Albatross-Koukairoku-English-v1.0.0'
        old_installer = {}
        exec((old_package / 'install_patch.py').read_text(), old_installer)
        old_installer['install'](old_package, self.game)
        self.assertEqual(installer.file_hash(self.game / 'scr.xfl'),
                         installer.PREVIOUS_OUTPUTS['scr.xfl'][0])
        self.assertIn(f'v{VERSION} installed', self.run_install())
        for row in self.manifest['files']:
            self.assertEqual(installer.file_hash(self.game / row['name']), row['output_sha256'])
            self.assertEqual(installer.file_hash(self.game / installer.BACKUP / row['name']),
                             self.original[row['name']])
        self.assertEqual(self.save.read_bytes(), b'Untouched player progress')
        self.run_install(uninstall=True)
        self.assert_original()


    def test_published_v101_upgrades_preserving_saves_and_originals(self):
        old_zip = PATCH_ROOT / 'reports/published-v1.0.1.zip'
        with zipfile.ZipFile(old_zip) as archive:
            archive.extractall(self.root / 'v101')
        old_package = self.root / 'v101' / 'Albatross-Koukairoku-English-v1.0.1'
        installer.install(old_package, self.game)
        self.assertEqual(installer.file_hash(self.game / 'Albatross.exe'),
                         '7b53c254ab511a8829b29fd11f03d4b368b044b8c7a15eb1198525702b1e3eac')
        before = self.snapshot()
        self.run_install()
        for row in self.manifest['files']:
            self.assertEqual(installer.file_hash(self.game / row['name']), row['output_sha256'])
            self.assertEqual(installer.file_hash(self.game / installer.BACKUP / row['name']),
                             self.original[row['name']])
        for name in ('scr.xfl', 'grpo.xfl', 'grps.xfl'):
            self.assertEqual(installer.file_hash(self.game / name), before[name])
        self.assertEqual(self.save.read_bytes(), b'Untouched player progress')
        self.run_install(uninstall=True)
        self.assert_original()


if __name__ == '__main__': unittest.main()
