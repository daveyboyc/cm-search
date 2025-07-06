# Trading Bulletin Board Implementation Plan

## 🔒 **DEPLOYMENT ISOLATION STRATEGY**

### ✅ **Current Safe State:**
- Trading board committed to `trades_branch` branch
- Main/master branch unchanged 
- Heroku deployments won't include trading board

### 🚀 **Deployment Safety:**
1. **Feature Branch**: All trading board code is on `trades_branch` 
2. **Main Branch Clean**: Your main/master branch doesn't have the trading board
3. **Heroku Safety**: Only push main/master to Heroku, never feature branches

### 📋 **Next Steps When Ready:**
```bash
# When trading board is ready for production:
git checkout main
git merge trades_branch
git push heroku main
```

### 🔄 **Continue Development:**
- Stay on `trades_branch` branch for trading board work
- Add payment integration, testing, etc. on this branch
- Main app remains unaffected until you're ready to merge

## 🚧 **CURRENT STATUS: HIDDEN FOR TESTING**

### **Navigation Links Temporarily Commented Out:**
The trading board is currently **HIDDEN from all navigation menus** to prevent public access during testing phase.

**Files Modified:**
1. **`/checker/templates/checker/includes/universal_navbar.html` (Lines 79-82)**
   ```html
   <!-- TEMPORARILY HIDDEN FOR TESTING - RESTORE AFTER TESTING -->
   <!-- <li class="nav-item">
       <a class="nav-link" href="{% url 'trades:list' %}"><i class="bi bi-megaphone me-2"></i>Trading Board</a>
   </li> -->
   ```

2. **`/checker/templates/checker/base.html` (Lines 630-633)**
   ```html
   <!-- TEMPORARILY HIDDEN FOR TESTING - RESTORE AFTER TESTING -->
   <!-- <a href="{% url 'trades:list' %}" class="mobile-nav-item">
       <i class="bi bi-megaphone"></i>Trading Board
   </a> -->
   ```

### **Access During Testing:**
- **Direct URL Access Only**: `https://your-app.herokuapp.com/trades/`
- **No Public Navigation**: Links hidden from navbar and mobile menu
- **Admin/Testing Access**: Navigate directly to URLs for testing

### **Why Hidden:**
- Testing payment integration with real Stripe
- Preventing public access before launch
- Validating email system with real Mailgun
- Ensuring everything works in production environment

### **To Restore Public Access:**
1. Uncomment the navigation links in both template files
2. Remove the comment blocks around the `<li>` and `<a>` tags
3. Commit and deploy: Trading board will be publicly accessible

---

## Overview
A simple £5 bulletin board for secondary capacity market trading - no trade facilitation, just advertising.

## MVP Scope
- Basic advert posting (Selling/Buying capacity)
- £5 payment per post via Stripe
- 30-day auto-expiry
- Simple verification (payment = verified)
- No complex search/filtering initially

## Phase 1: Basic Functionality (No Payment)

### Step 1: Create Django App
```bash
python manage.py startapp trades
```

### Step 2: Add to Settings
Add `'trades',` to `INSTALLED_APPS` in `capacity_checker/settings.py`

### Step 3: Create Model
**File:** `trades/models.py`
```python
from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta

class TradingAdvert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_offer = models.BooleanField(default=True)  # True=Selling, False=Buying
    capacity_mw = models.DecimalField(max_digits=7, decimal_places=2)
    delivery_year = models.IntegerField()
    price_gbp_per_kw_yr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(max_length=1000)
    contact_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    is_paid = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = datetime.now() + timedelta(days=30)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
```

### Step 4: Create Views
**File:** `trades/views.py`
```python
from django.views.generic import ListView, CreateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import TradingAdvert
from .forms import TradingAdvertForm

class TradingAdvertListView(ListView):
    model = TradingAdvert
    template_name = 'trades/list.html'
    context_object_name = 'adverts'
    
    def get_queryset(self):
        return TradingAdvert.objects.filter(is_active=True, expires_at__gte=datetime.now())

class TradingAdvertCreateView(LoginRequiredMixin, CreateView):
    model = TradingAdvert
    form_class = TradingAdvertForm
    template_name = 'trades/create.html'
    success_url = reverse_lazy('trades:list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class TradingAdvertDetailView(DetailView):
    model = TradingAdvert
    template_name = 'trades/detail.html'
    context_object_name = 'advert'
```

### Step 5: Create Forms
**File:** `trades/forms.py`
```python
from django import forms
from .models import TradingAdvert

class TradingAdvertForm(forms.ModelForm):
    class Meta:
        model = TradingAdvert
        fields = ['is_offer', 'capacity_mw', 'delivery_year', 'price_gbp_per_kw_yr', 'description', 'contact_email']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def clean_capacity_mw(self):
        capacity = self.cleaned_data['capacity_mw']
        if capacity <= 0:
            raise forms.ValidationError("Capacity must be greater than 0")
        return capacity
    
    def clean_delivery_year(self):
        year = self.cleaned_data['delivery_year']
        current_year = datetime.now().year
        if year < current_year + 1:
            raise forms.ValidationError(f"Delivery year must be {current_year + 1} or later")
        return year
```

### Step 6: Create URLs
**File:** `trades/urls.py`
```python
from django.urls import path
from . import views

app_name = 'trades'

urlpatterns = [
    path('', views.TradingAdvertListView.as_view(), name='list'),
    path('new/', views.TradingAdvertCreateView.as_view(), name='create'),
    path('<int:pk>/', views.TradingAdvertDetailView.as_view(), name='detail'),
]
```

### Step 7: Create Templates
**File:** `trades/templates/trades/list.html`
```html
{% extends "checker/base.html" %}
{% block content %}
<div class="container">
    <h1>Secondary Trading Board</h1>
    <a href="{% url 'trades:create' %}" class="btn btn-primary mb-3">Post Advert</a>
    
    <ul class="nav nav-tabs" id="tradeTabs">
        <li class="nav-item">
            <a class="nav-link active" data-bs-toggle="tab" href="#selling">Selling</a>
        </li>
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="tab" href="#buying">Buying</a>
        </li>
    </ul>
    
    <div class="tab-content">
        <div class="tab-pane active" id="selling">
            <table class="table">
                <thead>
                    <tr>
                        <th>Capacity (MW)</th>
                        <th>Delivery Year</th>
                        <th>Price (£/kW/yr)</th>
                        <th>Description</th>
                        <th>Posted</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {% for advert in adverts %}
                        {% if advert.is_offer %}
                        <tr>
                            <td>{{ advert.capacity_mw }}</td>
                            <td>{{ advert.delivery_year }}</td>
                            <td>{% if advert.price_gbp_per_kw_yr %}£{{ advert.price_gbp_per_kw_yr }}{% else %}POA{% endif %}</td>
                            <td>{{ advert.description|truncatewords:20 }}</td>
                            <td>{{ advert.created_at|date:"d M Y" }}</td>
                            <td><a href="{% url 'trades:detail' advert.pk %}" class="btn btn-sm btn-outline-primary">View</a></td>
                        </tr>
                        {% endif %}
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="tab-pane" id="buying">
            <table class="table">
                <thead>
                    <tr>
                        <th>Capacity (MW)</th>
                        <th>Delivery Year</th>
                        <th>Price (£/kW/yr)</th>
                        <th>Description</th>
                        <th>Posted</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {% for advert in adverts %}
                        {% if not advert.is_offer %}
                        <tr>
                            <td>{{ advert.capacity_mw }}</td>
                            <td>{{ advert.delivery_year }}</td>
                            <td>{% if advert.price_gbp_per_kw_yr %}£{{ advert.price_gbp_per_kw_yr }}{% else %}POA{% endif %}</td>
                            <td>{{ advert.description|truncatewords:20 }}</td>
                            <td>{{ advert.created_at|date:"d M Y" }}</td>
                            <td><a href="{% url 'trades:detail' advert.pk %}" class="btn btn-sm btn-outline-primary">View</a></td>
                        </tr>
                        {% endif %}
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
```

### Step 8: Django Admin
**File:** `trades/admin.py`
```python
from django.contrib import admin
from .models import TradingAdvert

@admin.register(TradingAdvert)
class TradingAdvertAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_type', 'capacity_mw', 'delivery_year', 'price_gbp_per_kw_yr', 'created_at', 'is_active', 'is_paid']
    list_filter = ['is_offer', 'delivery_year', 'is_active', 'is_paid']
    search_fields = ['description', 'user__email', 'contact_email']
    
    def get_type(self, obj):
        return "Selling" if obj.is_offer else "Buying"
    get_type.short_description = 'Type'
```

### Step 9: Include URLs in Main Project
Add to `capacity_checker/urls.py`:
```python
path('trades/', include('trades.urls')),
```

### Step 10: Run Migrations
```bash
python manage.py makemigrations trades
python manage.py migrate
```

### Step 11: Add Navigation Links
- Add to universal navbar
- Add to base template hamburger menu
- Add to homepage

## Phase 2: Payment Integration (£5 per post)

### Step 1: Update Model
Add payment fields:
- `stripe_payment_intent_id`
- `payment_status`

### Step 2: Create Payment Flow
1. User fills form → Create unpaid advert
2. Redirect to Stripe Checkout (£5)
3. On success → Mark as paid and activate
4. On failure → Delete or mark expired

### Step 3: Webhook Handler
Handle Stripe payment confirmations

## Phase 3: Verification System

### Option 1: Email Domain Matching
- Check if user email domain matches company contacts in database
- Auto-verify if match found

### Option 2: Payment = Verification
- Simple: If paid, then verified

### Option 3: Manual Admin Approval
- For edge cases

## Phase 4: Auto-Expiry

### Create Management Command
`trades/management/commands/expire_adverts.py`:
```python
from django.core.management.base import BaseCommand
from trades.models import TradingAdvert
from datetime import datetime

class Command(BaseCommand):
    def handle(self, *args, **options):
        expired = TradingAdvert.objects.filter(
            is_active=True,
            expires_at__lt=datetime.now()
        ).update(is_active=False)
        self.stdout.write(f"Expired {expired} adverts")
```

### Schedule with Cron/Heroku Scheduler
Daily: `python manage.py expire_adverts`

## Testing Checklist
- [ ] Create advert (logged in user)
- [ ] View advert list (selling/buying tabs)
- [ ] View advert detail
- [ ] Form validation (capacity > 0, year >= current+1)
- [ ] Admin interface works
- [ ] Navigation links present
- [ ] Mobile responsive

## Future Enhancements
- Search/filtering
- Email notifications
- Rich text editor for descriptions
- Image uploads
- Auction year field
- Location field
- Technology preferences