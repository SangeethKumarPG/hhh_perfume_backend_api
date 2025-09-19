from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from django.conf.urls.static import static


# ---------- Import ViewSets ----------
from store.views import (
    BasketItemViewSet,
    CategoryViewSet,
    ProductViewSet,
    ContactView,
    OrderViewSet,
    register_view,
    login_view,
    product_dashboard,
    product_detail_view,
    product_dashboard_view,
    product_detail_html_view,
    product_edit_view,
    product_delete_view,
    WishListViewSet
)
from payment.views import PaymentViewSet, InvoiceViewSet

# ---------- DRF Router ----------
router = DefaultRouter()

# Store endpoints
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'products', ProductViewSet, basename='products')
router.register(r'cart', BasketItemViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'contact', ContactView, basename='contact')
router.register(r'wishlist',WishListViewSet,basename='wishlist')

# Payment endpoints
router.register(r'payments', PaymentViewSet, basename='payments')
router.register(r'invoices', InvoiceViewSet, basename='invoices')

# ---------- API Root ----------
@api_view(['GET'])
def api_root(request, format=None):
    base = request.build_absolute_uri
    return Response({
        "Auth Endpoints": {
            "Register": base('register/'),
            "Login": base('login/'),
            "Admin Panel": base('admin/')
        },
        "Store Endpoints": {
            "Categories": base('categories/'),
            "Products": base('products/'),
            "Product Dashboard (API)": base('product_dashboard/'),
            "Product Detail (Example)": base('product/1/'),
            "Contact Form": base('contact/'),
            "WishList":base('Wishlist/'),
        },
        "Cart Endpoints": {
            "Cart": base('cart/'),
        },
        "Order Endpoints": {
            "Orders": base('orders/'),
        },
        "Payment Endpoints": {
            "Payments": base('payments/'),
            "Invoices": base('invoices/')
        }
    })

# ---------- URL Patterns ----------
urlpatterns = [
    path('admin/', admin.site.urls),

    # API root
    path('', api_root, name='api-root'),

    # Authentication
    path('register/', register_view, name='user-register'),
    path('login/', login_view, name='user-login'),

    # HTML product dashboard & detail
    path('product_dashboard/', product_dashboard, name='product-dashboard'),
    path('product/<int:pk>/', product_detail_view, name='product-detail-view'),
    path('dashboard/', product_dashboard_view, name='product-dashboard-html'),
    path('product/<int:pk>/detail/', product_detail_html_view, name='product-detail-html'),
    path('product/<int:pk>/edit/', product_edit_view, name='product-edit'),
    path('product/<int:pk>/delete/', product_delete_view, name='product-delete'),
    path('api/', include('store.urls')),

    # All ViewSets from router
    path('', include(router.urls)),
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)