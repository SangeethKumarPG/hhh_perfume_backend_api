from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import EmailMessage

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.generics import RetrieveAPIView, CreateAPIView

from store.models import (                    # store app models, except Invoice
    Category, Product, Contact,
    Order, OrderItem,
    Basket, BasketItem, ProductMedia
)
from payment.models import Invoice            # import Invoice from payment app

from store.serializers import (
    CategorySerializer, ProductSerializer, ContactSerializer,
    UserRegistrationSerializer, OrderSerializer, OrderItemSerializer,
    CartItemSerializer, ProductMediaSerializer
)
from payment.serializers import InvoiceSerializer   # import InvoiceSerializer from payment app

from store.forms import ProductForm
from store.utils import render_to_pdf


# -------------------------------------------
# CATEGORY / PRODUCT / CONTACT API
# -------------------------------------------
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


    @action(detail=True,methods=['get'])
    def products(self,request,pk=None):
        category=self.get_object()
        products=Product.objects.filter(category=category)
        serializer=ProductSerializer(products,many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class ContactView(viewsets.ViewSet):
    def create(self, request):
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Contact message submitted successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def register_view(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')
    user = authenticate(email=email, password=password)
    if user:
        return Response({"message": "Login successful", "email": user.email})
    return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)



def product_dashboard(request):
    products = Product.objects.all()
    return render(request, 'store/product_dashboard.html', {'products': products})



def product_detail_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_detail.html', {'product': product})


# -------------------------------------------
# PRODUCT TEMPLATE VIEWS
# -------------------------------------------
def product_dashboard_view(request):
    products = Product.objects.all()
    return render(request, 'store/product_dashboard.html', {'products': products})


def product_detail_html_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'store/product_detail.html', {'product': product})


def product_edit_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product-dashboard-html')
    else:
        form = ProductForm(instance=product)
    return render(request, 'store/product_form.html', {'form': form, 'product': product})


def product_delete_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        return redirect('product-dashboard-html')
    return render(request, 'store/product_confirm_delete.html', {'product': product})


# -------------------------------------------
# CART / BASKET API
# -------------------------------------------
class BasketItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BasketItem.objects.filter(
            basket_object__owner=self.request.user,
            is_active=True,
            is_order_placed=False
        )

    def perform_create(self, serializer):
        basket, _ = Basket.objects.get_or_create(owner=self.request.user)
        serializer.save(basket_object=basket)

    @action(detail=True, methods=['post'], url_path='add-to-cart')
    def add_to_cart(self, request, pk=None):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        basket, _ = Basket.objects.get_or_create(owner=request.user)
        item, created = BasketItem.objects.get_or_create(
            product_object=product,
            basket_object=basket,
            is_order_placed=False,
            defaults={'quantity': 1}
        )

        if not created:
            item.quantity += 1
            item.save()

        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='remove-from-cart')
    def remove_from_cart(self, request, pk=None):
        try:
            item = BasketItem.objects.get(pk=pk, basket_object__owner=request.user, is_order_placed=False)
            item.is_active = False
            item.save()
            return Response({'detail': 'Item removed from cart'}, status=status.HTTP_204_NO_CONTENT)
        except BasketItem.DoesNotExist:
            return Response({'detail': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['patch'], url_path='update-quantity')
    def update_quantity(self, request, pk=None):
        quantity = request.data.get('quantity')
        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError
        except (TypeError, ValueError):
            return Response({'detail': 'Quantity must be an integer >= 1'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            item = BasketItem.objects.get(pk=pk, basket_object__owner=request.user, is_order_placed=False)
            item.quantity = quantity
            item.save()
            return Response(CartItemSerializer(item).data)
        except BasketItem.DoesNotExist:
            return Response({'detail': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='view-cart')
    def view_cart(self, request):
        basket = Basket.objects.filter(owner=request.user).first()
        if not basket:
            return Response({'detail': 'Cart is empty'}, status=status.HTTP_404_NOT_FOUND)
        items = basket.cartitems.filter(is_order_placed=False, is_active=True)
        return Response(CartItemSerializer(items, many=True).data)


# -------------------------------------------
# ORDER API
# -------------------------------------------
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def confirm_order(self, request, pk=None):
        order = get_object_or_404(Order, id=pk, user=request.user)
        order_items = OrderItem.objects.filter(order=order)

        pdf = render_to_pdf('payment_invoices.html', {
            'order': order,
            'order_items': order_items,
            'customer_name': request.user.get_full_name() or request.user.username,
        })

        if not pdf:
            return Response({'error': 'Failed to generate invoice PDF'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        success = self.send_invoice_email(
            order, pdf, request.user.email, request.user.get_full_name() or request.user.username
        )

        return Response(
            {'message': 'Invoice sent via email'} if success else {'error': 'Invoice failed to send'},
            status=status.HTTP_200_OK if success else status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    def send_invoice_email(self, order, pdf, customer_email, customer_name):
        try:
            subject = f"Invoice for Order #{order.id}"
            message = f"Dear {customer_name},\n\nThank you for your purchase."
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER),
                to=[customer_email],
                cc=['info@nibhasitsolutions.com'],
            )
            filename = f"Invoice_{order.id}.pdf"
            email.attach(filename, pdf, 'application/pdf')
            email.send()
            return True
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False

# Product insert
class ProductCreateAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# Single product view
class ProductDetailAPIView(RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

# Get all products
class ProductListAPIView(APIView):
    def get(self, request):
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
    
# Delete product
class ProductDeleteAPIView(APIView):
    def delete(self, request, pk):
        product = Product.objects.get(pk=pk)
        product.delete()
        return Response({'message': 'Product deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    
#product media insert 
class ProductMediaCreateView(CreateAPIView):
    queryset = ProductMedia.objects.all()
    serializer_class = ProductMediaSerializer

# fetch single product media
class SingleProductMediaById(RetrieveAPIView):
    serializer_class = ProductMediaSerializer
    def get_object(self):
        product_id = self.kwargs.get('product_id')
        try:
            return ProductMedia.objects.get(product_id=product_id)
        except ProductMedia.DoesNotExist:
            raise NotFound(detail="Product media does not exist for the product id")