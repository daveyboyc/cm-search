from django.test import SimpleTestCase

# Create your tests here.

class BasicTestCase(SimpleTestCase):
    """Basic tests that don't require database access"""
    
    def test_basic_functionality(self):
        """Test that basic Python functionality works"""
        self.assertEqual(1 + 1, 2)
        self.assertTrue(True)
        
    def test_django_import(self):
        """Test that Django can be imported"""
        import django
        self.assertIsNotNone(django.VERSION)
