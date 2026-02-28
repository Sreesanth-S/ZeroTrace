import sys
import unittest
from pathlib import Path

# make sure the desktop_app package is on the path for imports
sys.path.append(str(Path(__file__).parent.parent))

from wipe_engine import WipeEngine, DeviceInfo, WipeMethod, DriveType

class HiddenSectorTests(unittest.TestCase):
    def setUp(self):
        self.engine = WipeEngine()

    def test_supported_methods_include_hidden_when_hpa(self):
        di = DeviceInfo("PHYSICALDRIVE99", "TestDrive", 1024)
        di.hpa_enabled = True
        di.hpa_hidden_sectors = 100
        methods = self.engine.get_supported_methods(di)
        self.assertIn(WipeMethod.HIDDEN_SECTORS, methods)

    def test_best_method_reason_mentions_hidden(self):
        di = DeviceInfo("PHYSICALDRIVE99", "TestDrive", 1024)
        di.drive_type = DriveType.HDD
        di.hpa_enabled = True
        di.hpa_hidden_sectors = 42
        best = self.engine.detect_best_wipe_method(di)
        self.assertIn("hidden sectors", best['reason'])

    def test_hidden_sector_wipe_no_hpa(self):
        di = DeviceInfo("PHYSICALDRIVE99", "TestDrive", 1024)
        result = self.engine._perform_hidden_sector_wipe(di, None, {'method':WipeMethod.HIDDEN_SECTORS})
        # since no real device exists this will fail; we just want to make sure it doesn't crash
        self.assertFalse(result.get('success'))
        err = result.get('error', '')
        # expected to either complain about missing drive or no hidden sectors
        self.assertTrue('hidden' in err.lower() or 'drive' in err.lower())

if __name__ == '__main__':
    unittest.main()
