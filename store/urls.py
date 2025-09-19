# store/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductCreateAPIView, ProductDeleteAPIView, ProductDetailAPIView, ProductListAPIView, ProductMediaCreateView, SingleProductMediaById
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


# ---------- Import ViewSets ----------
from .views import (
    CategoryViewSet,
    ProductViewSet,
    BasketItemViewSet,
    OrderViewSet,
    #InvoiceViewSet,
    ContactView,
    register_view,
    login_view,
    admin_login_view,
    product_dashboard,
    product_detail_view,
    product_dashboard_view,
    product_detail_html_view,
    product_edit_view,
    product_delete_view,
    dashboard_stats
)
from payment.views import InvoiceViewSet


router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'basket-items', BasketItemViewSet, basename='basketitem')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'contact', ContactView, basename='contact')


urlpatterns = [
    # API routes from DRF router
    path('', include(router.urls)),

    # Auth routes
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('admin-login/', admin_login_view, name='admin-login'),

    # Contact form API
    # path('contact/', ContactView.as_view(), name='contact'),

    # Product dashboard & details (HTML views)
    path('dashboard/', product_dashboard, name='product_dashboard'),
    path('dashboard/view/', product_dashboard_view, name='product_dashboard_view'),
    path('dashboard/view/<int:pk>/', product_detail_view, name='product_detail_view'),
    path('dashboard/view/html/<int:pk>/', product_detail_html_view, name='product_detail_html_view'),
    path('dashboard/edit/<int:pk>/', product_edit_view, name='product_edit_view'),
    path('dashboard/delete/<int:pk>/', product_delete_view, name='product_delete_view'),

    # product insert
    path('create-product/', ProductCreateAPIView.as_view(), name='product-create'),

    # single product view
     path('view-product/<int:pk>/', ProductDetailAPIView.as_view(), name='product-detail'),

    # all products view
    path('view-products/', ProductListAPIView.as_view(), name='product-list'),

    # delete single product
    path('delete-product/<int:pk>/', ProductDeleteAPIView.as_view(), name='product-delete'),

    #insert product media
    path('add-product-media', ProductMediaCreateView.as_view(), name="product-media-insert"),

    #fetch single product media
    path('get-product-media/<int:product_id>', SingleProductMediaById.as_view(), name='single-product-media'),


    # fetch products by category
    path('categories/<int:category_id>/products/',ProductListAPIView.as_view(), name='product-list-by-category'),

    #JWT token refresh
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    #############################ADMIN DASHBOARD####################################
    path('dashboard-stats/',dashboard_stats, name='dashboard_stats'),
]

