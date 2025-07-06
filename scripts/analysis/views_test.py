"""
Test views that should be accessible to everyone
"""
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache

@never_cache
def test_donation_view(request):
    """
    Test donation page accessible to everyone - no restrictions
    """
    context = {
        'page_title': 'Test Donation Page',
        'user': request.user,
    }
    return render(request, 'checker/test_donation.html', context)