from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Product, Contact, Order, OrderItem, Basket, BasketItem, ProductMedia


# Category Serializer
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


# Product Serializer (WITH IMAGE & CATEGORY DETAILS)
class ProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_detail = CategorySerializer(source='category', read_only=True)
    image = serializers.ImageField(required=False, allow_null=True, use_url=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'description', 'stock', 'category', 'category_detail', 'image']


# User Registration Serializer
class UserRegistrationSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, label='Confirm password')

    class Meta:
        model = User
        fields = ['username', 'email', 'full_name', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': "Passwords must match."})
        return attrs

    def create(self, validated_data):
        full_name = validated_data.pop('full_name', '')
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        if full_name:
            names = full_name.strip().split(' ', 1)
            user.first_name = names[0]
            if len(names) > 1:
                user.last_name = names[1]
            user.save()
        return user


# Contact Form Serializer
class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'


# Cart & Basket Serializers
class CartItemSerializer(serializers.ModelSerializer):
    product_object = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    basket_object = serializers.PrimaryKeyRelatedField(queryset=Basket.objects.all(), required=False)
    item_total = serializers.DecimalField(source='item_total', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = BasketItem
        fields = '__all__'
        # If product_object and basket_object are writable on creation, remove them from read_only_fields
        read_only_fields = ["id", "quantity", "is_active", "is_order_placed"]


class CartSerializer(serializers.ModelSerializer):
    cartitems = CartItemSerializer(many=True, read_only=True)
    get_basket_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Basket
        fields = ["id", "cartitems", 'get_basket_total', 'created_date', 'updated_date']
        read_only_fields = ['id', 'owner', 'created_date', 'updated_date', 'get_basket_total']


# Order & OrderItem Serializers
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"
        read_only_fields = ('id', 'order')
        extra_kwargs = {
            'product_name': {'required': True},
            'quantity': {'required': True},
            'price': {'required': True}
        }


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("id", "user", "order_id", "created_at", "updated_at")
        extra_kwargs = {
            'address': {'required': True},
            'total_amount': {'required': True},
            'status': {'required': True},
            'is_paid': {'required': True},
            'items': {'required': False}
        }


# Invoice Serializer
class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'

# ProductMedia Serializer
class ProductMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = ['id', 'product', 'image1','image2','image3', 'video']