from django.contrib import admin
from .models import TradingAdvert


@admin.register(TradingAdvert)
class TradingAdvertAdmin(admin.ModelAdmin):
    list_display = ['get_type', 'capacity_display', 'delivery_year', 'price_display', 'user', 'created_at', 'is_active', 'is_paid']
    list_filter = ['is_offer', 'delivery_year', 'is_active', 'is_paid', 'created_at']
    search_fields = ['description', 'user__email', 'user__username', 'contact_email']
    readonly_fields = ['created_at', 'stripe_payment_intent_id']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'is_offer', 'capacity_mw', 'capacity_flexible', 'delivery_year', 'price_gbp_per_kw_yr', 'price_estimate')
        }),
        ('Contact & Description', {
            'fields': ('contact_email', 'description')
        }),
        ('Status', {
            'fields': ('is_active', 'is_paid', 'expires_at')
        }),
        ('Payment', {
            'fields': ('stripe_payment_intent_id',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def get_type(self, obj):
        return obj.type_display
    get_type.short_description = 'Type'
    get_type.admin_order_field = 'is_offer'
    
    actions = ['mark_as_paid', 'mark_as_expired', 'mark_as_active']
    
    def mark_as_paid(self, request, queryset):
        queryset.update(is_paid=True)
    mark_as_paid.short_description = "Mark selected adverts as paid"
    
    def mark_as_expired(self, request, queryset):
        queryset.update(is_active=False)
    mark_as_expired.short_description = "Mark selected adverts as expired"
    
    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)
    mark_as_active.short_description = "Mark selected adverts as active"
