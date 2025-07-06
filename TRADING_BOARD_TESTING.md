# Trading Board Testing Documentation

## 🧪 **Current Testing Phase**

The trading board is **HIDDEN from public navigation** and accessible only via direct URLs for testing purposes.

## 📍 **Testing URLs**

### **Production Testing URLs (Heroku):**
- **Main Trading Board**: `https://your-app.herokuapp.com/trades/`
- **Post New Advert**: `https://your-app.herokuapp.com/trades/new/`
- **View Specific Advert**: `https://your-app.herokuapp.com/trades/[ID]/`
- **Send Message**: `https://your-app.herokuapp.com/trades/[ID]/message/`

### **Local Development URLs:**
- **Main Trading Board**: `http://localhost:8000/trades/`
- **Post New Advert**: `http://localhost:8000/trades/new/`
- **View Specific Advert**: `http://localhost:8000/trades/[ID]/`
- **Send Message**: `http://localhost:8000/trades/[ID]/message/`

## 🔧 **What to Test on Heroku:**

### **1. Payment Integration (£5 Stripe)**
- [ ] Fill out complete advert form
- [ ] Add password for new account creation
- [ ] Click "Continue to Secure Payment (£5)"
- [ ] Complete Stripe checkout process
- [ ] Verify advert appears in listings after payment
- [ ] Check success message displays correctly

### **2. Email System (Mailgun)**
- [ ] Post advert with email privacy disabled (show email directly)
- [ ] Post advert with email privacy enabled (messaging system)
- [ ] Send test message to advert with private messaging
- [ ] Verify email delivery to actual email address
- [ ] Check email formatting and content

### **3. Account Creation**
- [ ] Post advert while logged out with new email
- [ ] Verify account creation with chosen password
- [ ] Post advert while logged out with existing email
- [ ] Verify existing account linking

### **4. User Experience**
- [ ] Test responsive design on mobile/desktop
- [ ] Verify all form validation works
- [ ] Check sorting functionality (date, capacity, price)
- [ ] Test pagination with 50+ adverts
- [ ] Verify flexibility indicators (asterisks)

## 🚨 **Pre-Deployment Checklist:**

Before deploying to Heroku, ensure:

1. **Create Stripe Product/Price:**
   ```bash
   heroku run python manage.py create_trading_stripe_product
   ```

2. **Set Environment Variables:**
   ```bash
   heroku config:set STRIPE_TRADING_ADVERT_PRICE_ID=price_XXXXXXXX
   ```

3. **Verify Mailgun Configuration:**
   ```bash
   heroku run python manage.py test_email your@email.com
   ```

## ⚠️ **Testing Precautions:**

- **DO NOT** share testing URLs publicly
- **Use test email addresses** for testing messages
- **Test with small amounts** first (£5 is real money)
- **Document any issues** found during testing
- **Verify all functionality** before making public

## 📋 **Post-Testing Actions:**

After successful testing:

1. **Uncomment Navigation Links** (when ready for public access)
2. **Update Documentation** with any changes
3. **Create Final Deployment Plan**
4. **Set up Monitoring/Analytics** if needed

## 🔄 **Restoration Instructions:**

To make trading board publicly accessible again:

1. **Uncomment in `universal_navbar.html`:**
   ```html
   <li class="nav-item">
       <a class="nav-link" href="{% url 'trades:list' %}"><i class="bi bi-megaphone me-2"></i>Trading Board</a>
   </li>
   ```

2. **Uncomment in `base.html`:**
   ```html
   <a href="{% url 'trades:list' %}" class="mobile-nav-item">
       <i class="bi bi-megaphone"></i>Trading Board
   </a>
   ```

3. **Commit and Deploy:**
   ```bash
   git add -A
   git commit -m "Restore trading board navigation - ready for public access"
   git push heroku trades_branch:main
   ```

## 📊 **Testing Results Log:**

| Feature | Status | Notes |
|---------|--------|-------|
| Stripe Payment | ⏳ | Testing in progress |
| Email Delivery | ⏳ | Testing in progress |
| Account Creation | ⏳ | Testing in progress |
| Form Validation | ⏳ | Testing in progress |
| Responsive Design | ⏳ | Testing in progress |

*Update this table as testing progresses*