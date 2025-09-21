import datetime
from itertools import product
from random import random
import string
from urllib import request
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
from rest_framework.generics import RetrieveAPIView, CreateAPIView,ListAPIView, DestroyAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated,AllowAny
# from django.contrib.auth.models import Userfrom

from store.permissions import IsSuperUser

from store.models import (                    
    Category, CustomUser, Product, Contact,
    Order, OrderItem,
    Basket, BasketItem, ProductMedia,Wishlist,PasswordReset,EmailVerificationCode,OTPVerification
)
from payment.models import Invoice            

from store.serializers import (
    CategorySerializer, ProductSerializer, ContactSerializer,
    UserRegistrationSerializer, OrderSerializer, OrderItemSerializer,
    CartItemSerializer, ProductMediaSerializer,WishListSerializer,
    CustomUserSerializer
)
from payment.serializers import InvoiceSerializer   

from store.forms import ProductForm
from store.utils import render_to_pdf,send_mail
from django.core.mail import send_mail
from rest_framework import status
from django.utils import timezone
from .utils import generate_otp, send_verification_email
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt



User=get_user_model()
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

    def get_permissions(self):
        """
        Allow everyone (authenticated) to view products,
        but only superusers can create, update, or delete.
        """
        if self.action in ["list", "retrieve"]:  # GET requests
            permission_classes = [permissions.AllowAny]  # anyone can view
        else:  # POST, PATCH, PUT, DELETE
            permission_classes = [permissions.IsAuthenticated, IsSuperUser]
        return [permission() for permission in permission_classes]


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

        if not user.is_active:
            return Response(
                {"error": "User is blocked. Please contact support."},
                status=status.HTTP_403_FORBIDDEN
            )

  
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Login successful",
            "email": user.email,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_200_OK)
    return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
def admin_login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')
    user = authenticate(email=email, password=password)

    if user:
        if not user.is_active:
            return Response(
                {"error": "User is blocked. Please contact support."},
                status=status.HTTP_403_FORBIDDEN
            )

        if not user.is_superuser:
            return Response(
                {"error": "You do not have admin access."},
                status=status.HTTP_403_FORBIDDEN
            )

        
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Admin login successful",
            "email": user.email,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_200_OK)

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

        item = BasketItem.objects.filter(
            product_object=product,
            basket_object=basket,
            is_order_placed=False
        ).first()

        if item:
            
            if not item.is_active:
                item.is_active = True
                item.quantity = 1  
            else:
                item.quantity += 1
            item.save()
        else:
            item = BasketItem.objects.create(
                product_object=product,
                basket_object=basket,
                quantity=1,
                is_active=True,
                is_order_placed=False
            )

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
    
    #For updaing order status
    @action(detail=False, methods=['patch'], url_path='update-status')
    def update_status(self, request):
        order_id = request.data.get("order_id")
        new_status = request.data.get("status")

        if not order_id or not new_status:
            return Response({"error": "order_id and status are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if request.user.is_superuser:
                # Superuser can update any order
                order = Order.objects.get(order_id=order_id)
            else:
                # Normal user can only update their own orders
                order = Order.objects.get(order_id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        order.status = new_status
        order.save()

        return Response({
            "message": f"Order {order.order_id} updated to {new_status}",
            "order_id": order.order_id,
            "status": order.status
        }, status=status.HTTP_200_OK)

# Product insert
class ProductCreateAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, IsSuperUser]

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

#Delete Product Media View
class ProductMediaDeleteView(DestroyAPIView):
    queryset = ProductMedia.objects.all()
    serializer_class = ProductMediaSerializer

# fetch single product media
class SingleProductMediaById(ListAPIView):
    serializer_class = ProductMediaSerializer
    def get_queryset(self):
        product_id = self.kwargs.get('product_id')
        try:
            return ProductMedia.objects.filter(product_id=product_id)
        except ProductMedia.DoesNotExist:
            raise NotFound(detail="Product media does not exist for the product id")


#Dashboard API
@api_view(['GET'])
@authentication_classes([JWTAuthentication])        
@permission_classes([IsAuthenticated])  
def dashboard_stats(request):
    total_orders = Order.objects.count()

    total_sales_value = Order.objects.aggregate(total=Sum("amount"))["total"] or 0

    total_active_users = CustomUser.objects.filter(is_active=True, is_superuser=False).count()

    total_blocked_users = CustomUser.objects.filter(is_active=False, is_superuser=False).count()

    orders_per_month = (
        Order.objects.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(order_count=Count("id"))
        .order_by("month")
    )

    sales_per_month = (
        Order.objects.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total_sales=Sum("amount"))
        .order_by("month")
    )

    top_products = (
        OrderItem.objects.values("product__id", "product__name")
        .annotate(total_quantity=Sum("quantity"), total_sales=Sum("price"))
        .order_by("-total_quantity")[:5]  # Top 5 products
    )

    return Response({
        "total_orders": total_orders,
        "total_sales_value": float(total_sales_value),
        "total_active_users": total_active_users,
        "total_blocked_users": total_blocked_users,
        "orders_per_month": [
            {"month": o["month"].strftime("%B %Y"), "count": o["order_count"]}
            for o in orders_per_month
        ],
        "sales_per_month": [
            {"month": s["month"].strftime("%B %Y"), "total": float(s["total_sales"] or 0)}
            for s in sales_per_month
        ],
        "top_selling_products": [
            {
                "id": p["product__id"],
                "name": p["product__name"],
                "total_quantity": p["total_quantity"],
                "total_sales": float(p["total_sales"] or 0),
            }
            for p in top_products
        ],
    })
class WishListViewSet(viewsets.ModelViewSet):
    serializer_class=WishListSerializer
    permission_classes=[IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        product_id = request.data.get("product")

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        # check if already exists
        if Wishlist.objects.filter(user=request.user, product=product).exists():
            return Response({"message": "Product already exists in your wishlist"}, status=status.HTTP_200_OK)

        # create wishlist entry
        wishlist_item = Wishlist.objects.create(user=request.user, product=product)
        serializer = self.get_serializer(wishlist_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True,methods=['post'],url_path='add_to_wishlist')
    def add_to_wishlist(self,request,pk=None):
        product_id=pk
        if not product_id:
            return Response({"error":"Product ID is required"},status=status.HTTP_400_BAD_REQUEST)
        try:
            product=Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error":"Product Not Found"},status=status.HTTP_404_NOT_FOUND)
        if Wishlist.objects.filter(user=request.user,product=product).exists():
            return Response({"message":"Product already in your wishlist"},status=status.HTTP_200_OK)

        # create wishlist entry
        wishlist_item = Wishlist.objects.create(user=request.user, product=product)
        serializer = self.get_serializer(wishlist_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='remove_from_wishlist')
    def remove_from_wishlist(self, request, pk=None):
        try:
            wishlist_item = Wishlist.objects.get(id=pk, user=request.user)
            wishlist_item.delete()
            return Response({"message": "Product removed from wishlist"}, status=status.HTTP_200_OK)
        except Wishlist.DoesNotExist:
            return Response({"error": "Product not in wishlist"}, status=status.HTTP_404_NOT_FOUND)
        

@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    email=request.data.get("email")
    if not email:
        return Response({"error":"Email is required"},status=status.HTTP_400_BAD_REQUEST)
    try:
        user=User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error":"Email not registered"},status=status.HTTP_404_NOT_FOUND)
    otp=generate_otp()
    PasswordReset.objects.create(user=user,otp=otp)

    send_mail(
        subject="Password Reset OTP",
        message=f"Your OTP for password reset is: {otp}.Valid for 5 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )
    return Response({"message":"OTP sent to your email"},status=status.HTTP_200_OK)


@csrf_exempt
def request_password_reset(request):
    if request.method=='POST':
        email=request.POST.get('email')
        try:
            user=User.objects.get(email=email)
            otp=generate_otp()
            PasswordReset.objects.create(user=user,code=otp)
            send_verification_email(user,otp)
            return JsonResponse({"message":"Verification code sent to your email"})
        except User.DoesNotExist:
            return JsonResponse({"error":"No user found with this email."},status=status.HTTP_400_BAD_REQUEST)
    return JsonResponse({"error":"Invalid Request"},status=status.HTTP_405_METHOD_NOT_ALLOWED)


# def reset_password(request):
#     if request.method=='POST':
#         email=request.POST.get("email")
#         otp=request.POST.get("otp")
#         new_password=request.POST.get("new_password")
#         try:
#             user=User.objects.get(email=email)
#             otp=PasswordReset.objects.filter(user=user,otp=otp,is_used=False).first()
#             if not otp:
#                 return JsonResponse({"error":"Invalid OTP"},status=status.HTTP_400_BAD_REQUEST)
            
#             user.password=make_password(new_password)
#             user.save()

#             otp.is_used=True
#             otp.save()
#             return JsonResponse({"message":"Password Reset Successfully"})
#         except User.DoesNotExist:
#             return JsonResponse({"error":"Invalid Email"},status=status.HTTP_400_BAD_REQUEST)
#     return JsonResponse({"error":"Invalid Request"},status=status.HTTP_405_METHOD_NOT_ALLOWED)

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    email = request.data.get("email")
    otp = request.data.get("otp")
    new_password = request.data.get("new_password")

    if not all([email, otp, new_password]):
        return Response({"error": "Email, OTP, and new password are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response({"error": "Invalid email"}, status=status.HTTP_404_NOT_FOUND)

    # validate OTP
    verification = PasswordReset.objects.filter(user=user, otp=otp).order_by("-created_at").first()
    if not verification:
        return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

    if timezone.now() > verification.created_at + datetime.timedelta(minutes=10):
        return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

    # update password
    user.set_password(new_password)
    user.save()

    return Response({"message": "Password reset successful"}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_email(request):
    email=request.data.get("email")
    if not email:
        return Response({"error":"Email is required"},status=status.HTTP_400_BAD_REQUEST)
    try:
        user=User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error":"Email not registered"},status=status.HTTP_404_NOT_FOUND)
    code=generate_otp()
    EmailVerificationCode.objects.create(user=user,code=code)

    send_mail(
        subject="Email Verification Code",
        message=f"Hi {user.username},\n\nYour verification code is: {code}\nThis code will expire once used.\n\nIf you didn’t request this, please ignore.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )
    return Response({"message":"Verification code sent to your email"},status=status.HTTP_200_OK)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    email = request.data.get("email")
    code = request.data.get("code")

    if not all([email, code]):
        return Response({"error": "Email and code required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "Invalid email"}, status=status.HTTP_404_NOT_FOUND)

    try:
        verification = EmailVerificationCode.objects.filter(user=user, code=code, is_used=False).latest("created_at")
    except EmailVerificationCode.DoesNotExist:
        return Response({"error": "Invalid verification code"}, status=status.HTTP_400_BAD_REQUEST)

    if verification.is_expired():
        return Response({"error": "Verification code expired"}, status=status.HTTP_400_BAD_REQUEST)

    user.is_active = True
    user.save()

    verification.is_used = True
    verification.save()

    return Response({"message": "Email verified successfully."})

@api_view(["POST"])
@permission_classes([AllowAny])
def send_otp(request):
    email = request.data.get("email")
    if not email:
        return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "User with this email does not exist"}, status=status.HTTP_404_NOT_FOUND)

    otp = "".join(random.choices(string.digits, k=6))  
    OTPVerification.objects.create(user=user, otp=otp)

    send_mail(
        "Your OTP Code",
        f"Your OTP is {otp}. It will expire in 5 minutes.",
        "noreply@example.com",
        [email],
        fail_silently=False,
    )

    return Response({"message": "OTP sent to email."})



# @api_view(["POST"])
# @permission_classes([AllowAny])
# def verify_otp(request):
#     email = request.data.get("email")
#     otp = request.data.get("otp")

#     if not all([email, otp]):
#         return Response({"error": "Email and OTP are required"}, status=status.HTTP_400_BAD_REQUEST)

#     try:
#         user = User.objects.get(email=email)
#     except User.DoesNotExist:
#         return Response({"error": "Invalid email"}, status=status.HTTP_404_NOT_FOUND)

#     try:
#         verification = OTPVerification.objects.filter(user=user, otp=otp, is_used=False).latest("created_at")
#     except OTPVerification.DoesNotExist:
#         return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

#     if verification.is_expired():
#         return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

#     verification.is_used = True
#     verification.save()

#     return Response({"message": "OTP verified successfully."})

@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    email = request.data.get("email")
    otp = request.data.get("otp")

    if not all([email, otp]):
        return Response({"error": "Email and OTP are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response({"error": "Invalid email"}, status=status.HTTP_404_NOT_FOUND)

    # get the latest unused OTP
    verification = PasswordReset.objects.filter(user=user, otp=otp).order_by("-created_at").first()

    if not verification:
        return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

    # check expiry (10 minutes)
    if timezone.now() > verification.created_at + datetime.timedelta(minutes=10):
        return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)







# Fetch custom user details
class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all().order_by("-date_joined")
    serializer_class = CustomUserSerializer
    permission_classes = [IsSuperUser]

#Fetch orders in admin page
class OrderDetailsViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Order.objects.none()  # dummy queryset

    def list(self, request, *args, **kwargs):
        orders = Order.objects.select_related("user").prefetch_related("items__product")

        data = []
        for order in orders:
            order_data = {
                "order_id": order.order_id,
                "razorpay_order_id": order.razorpay_order_id,
                "user": {
                    "id": order.user.id,
                    "email": order.user.email,
                    "first_name": order.first_name,
                    "last_name": order.last_name,
                },
                "phone_number": order.phone_number,
                "shipping_address": order.shipping_address,
                "city": order.city,
                "state": order.state,
                "pincode": order.pincode,
                "amount": str(order.amount),
                "status": order.status,
                "total_amount": str(order.order_total),
                "created_at": order.created_at,
                "updated_at": order.updated_at,
                "items": [
                    {
                        "id": item.id,
                        "product_id": item.product.id,
                        "product_name": item.product.name,
                        "product_price": str(item.product.price),
                        "quantity": item.quantity,
                        "price": str(item.price),
                        "total": str(item.get_total_price()),
                    }
                    for item in order.items.all()
                ],
            }
            data.append(order_data)

        return Response(data)