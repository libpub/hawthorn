#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from hawthorn.utilities import pascal_case, camel_case, snake_case, kebab_case

class TestTextCaseConverting(unittest.TestCase):
    
    def test_pascal_case(self):
        self.assertEqual(pascal_case('xx-yy'), 'XxYy')
        self.assertEqual(pascal_case('xx-YY'), 'XxYy')
        self.assertEqual(pascal_case('xx_yy'), 'XxYy')
        self.assertEqual(pascal_case('xx_YY'), 'XxYy')
    
    def test_camel_case(self):
        self.assertEqual(camel_case('xx-yy'), 'xxYy')
        self.assertEqual(camel_case('xx-YY'), 'xxYy')
        self.assertEqual(camel_case('xx_yy'), 'xxYy')
        self.assertEqual(camel_case('xx_YY'), 'xxYy')
    
    def test_snake_case(self):
        self.assertEqual(snake_case('XxYy'), 'xx_yy')
        self.assertEqual(snake_case('xxYY'), 'xx_yy')
        self.assertEqual(snake_case('XX-YY'), 'xx_yy')
    
    def test_kebab_case(self):
        self.assertEqual(kebab_case('XxYy'), 'xx-yy')
        self.assertEqual(kebab_case('xxYY'), 'xx-yy')
        self.assertEqual(kebab_case('XX_YY'), 'xx-yy')
    
if __name__ == '__main__':
    unittest.main()
