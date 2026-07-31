import unittest

from app.utils.tenant_urls import (
    generate_canonical_subdomain,
    is_valid_canonical_subdomain,
    is_valid_facility_slug,
)


class TenantUrlTest(unittest.TestCase):
    def test_readable_slug_is_preserved(self):
        self.assertEqual(
            generate_canonical_subdomain("sunrise-medical-centre", "tenant-a"),
            "sunrise-medical-centre",
        )

    def test_reserved_and_long_slugs_get_stable_dns_safe_suffixes(self):
        reserved = generate_canonical_subdomain("api", "tenant-a")
        long_slug = generate_canonical_subdomain("a" * 100, "tenant-a")

        self.assertTrue(is_valid_canonical_subdomain(reserved))
        self.assertNotEqual(reserved, "api")
        self.assertTrue(is_valid_canonical_subdomain(long_slug))
        self.assertLessEqual(len(long_slug), 63)
        self.assertEqual(long_slug, generate_canonical_subdomain("a" * 100, "tenant-a"))
        self.assertNotEqual(
            long_slug,
            generate_canonical_subdomain("a" * 100, "tenant-b"),
        )

    def test_invalid_or_reserved_labels_are_rejected(self):
        for value in ["", "API", "api", "-hospital", "hospital-", "bad.host", "a" * 64]:
            self.assertFalse(is_valid_canonical_subdomain(value), value)

    def test_legacy_facility_slug_validation_is_strict_but_allows_reserved_names(self):
        self.assertTrue(is_valid_facility_slug("sunrise-medical-centre"))
        self.assertTrue(is_valid_facility_slug("api"))
        for value in ["", "-hospital", "hospital-", "bad.host", "a" * 101]:
            self.assertFalse(is_valid_facility_slug(value), value)


if __name__ == "__main__":
    unittest.main()
