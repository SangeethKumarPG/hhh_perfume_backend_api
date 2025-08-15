# store/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductCreateAPIView


# ---------- Import ViewSets ----------
from .views import (
    CategoryViewSet,
    ProductViewSet,
    BasketItemViewSet,
    OrderViewSet,
    InvoiceViewSet,
    ContactView,
    register_view,
    login_view,
    product_dashboard,
    product_detail_view,
    product_dashboard_view,
    product_detail_html_view,
    product_edit_view,
    product_delete_view,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'basket-items', BasketItemViewSet, basename='basketitem')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'invoices', InvoiceViewSet, basename='invoice')

urlpatterns = [
    # API routes from DRF router
    path('', include(router.urls)),

    # Auth routes
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),

    # Contact form API
    path('contact/', ContactView.as_view(), name='contact'),

    # Product dashboard & details (HTML views)
    path('dashboard/', product_dashboard, name='product_dashboard'),
    path('dashboard/view/', product_dashboard_view, name='product_dashboard_view'),
    path('dashboard/view/<int:pk>/', product_detail_view, name='product_detail_view'),
    path('dashboard/view/html/<int:pk>/', product_detail_html_view, name='product_detail_html_view'),
    path('dashboard/edit/<int:pk>/', product_edit_view, name='product_edit_view'),
    path('dashboard/delete/<int:pk>/', product_delete_view, name='product_delete_view'),

    # product insert
    path('api/products/create/', ProductCreateAPIView.as_view(), name='product-create'),
]

