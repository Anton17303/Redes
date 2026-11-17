"""Regional ARM inventory pagination, using synthetic responses only."""
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from azure_snapshot import resource_skus

SIZE = "Standard_B2ats_v2"


class SkuInventoryTests(unittest.TestCase):
    def test_regional_pagination_preserves_restrictions_and_family(self):
        sku = {"name": SIZE, "resourceType": "virtualMachines", "family": "test",
               "restrictions": [{"reasonCode": "NotAvailableForSubscription"}]}
        pages = [{"value": [{"name": "other"}], "nextLink": "https://management.azure.com/page2"}, {"value": [sku]}]
        calls = []
        def reply(*args, **kwargs):
            parameters = json.loads(Path(args[-1][1:]).read_text("utf-8"))
            calls.append((args, parameters))
            return pages[len(calls)-1]
        with patch("azure_snapshot.request", side_effect=reply) as request:
            self.assertEqual(resource_skus("synthetic", SIZE), [sku])
            self.assertEqual(calls[0][1]["$filter"], "location eq 'northcentralus'")
            self.assertEqual(calls[0][1]["api-version"], "2021-07-01")
            self.assertNotIn("&", calls[0][0][4])
            self.assertEqual(request.call_count, 2)

    def test_untrusted_nextlink_and_loop_are_rejected(self):
        for link in ("https://example.invalid/skus", "https://management.azure.com/repeat"):
            with self.subTest(link=link), patch("azure_snapshot.request", return_value={"value": [], "nextLink": link}):
                with self.assertRaises(ValueError):
                    resource_skus("synthetic", SIZE)
