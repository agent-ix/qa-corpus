import unittest
import os, unittest as ut
from unittest import TestCase
from unittest import TestCase as BaseCase

class TestNativeChecks(unittest.TestCase):
    def test_native(self):
        """TC-001. Native assertion."""
        self.assertEqual(2 + 2, 4)

    def helper(self):
        return 4

class TestModuleAliasChecks(ut.TestCase):
    def test_module_alias(self):
        """TC-001. Native assertion."""
        self.assertTrue(True)

class TestImportedChecks(TestCase):
    def test_imported(self):
        """TC-001. Native assertion."""
        self.assertEqual("a".upper(), "A")

class TestImportedAliasChecks(BaseCase):
    def test_import_alias(self):
        """TC-001. Native assertion."""
        self.assertIn(1, [1])

class OrdinaryHelper:
    def test_named_helper(self):
        return False

def ordinary_function():
    return False

class Lookalike:
    TestCase = object

class QualifiedImpostor(Lookalike.TestCase):
    def test_helper(self):
        return False

TestCase = object

class ShadowedImportedBase(TestCase):
    def test_helper(self):
        return False

import unittest as shadow
shadow = Lookalike

class ShadowedModuleBase(shadow.TestCase):
    def test_helper(self):
        return False
