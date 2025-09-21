from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser,User
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import datetime
import random


# ---------------------------
# Custom User Model
# ---------------------------
class CustomUser(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    USERNAME_FIELD = 'email'           # login with email
    REQUIRED_FIELDS = ['username']     # username still required on createsuperuser

    def __str__(self):
        return self.email


# ---------------------------
# Category Model
# ---------------------------
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


# ---------------------------
# Product Model
# ---------------------------
class Product(models.Model):
    brand = models.CharField(max_length=100, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/',null=True,blank=True)
    stock = models.PositiveIntegerField()
    available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.category.name})"


# ---------------------------
# Product Media (Multiple Images/Videos)
# ---------------------------
class ProductMedia(models.Model):
    MEDIA_TYPE_CHOICES=[
        ('image','Image'),
        ('video','Video'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='media')
    media_type=models.CharField(max_length=10,choices=MEDIA_TYPE_CHOICES,null=True,blank=True)
    file=models.FileField(upload_to='product_images/',null=True,blank=True)
    def __str__(self):
        return f"Media for {self.product.name}"


# ---------------------------
# Contact Model (Contact Us Form)
# ---------------------------
class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.subject}"


# ---------------------------
# Basket Model
# ---------------------------
class Basket(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, default=None)
    created_date = models.DateTimeField(auto_now=True)
    updated_date = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.owner.email if self.owner else "Guest Basket"

    @property
    def get_cart_items(self):
        return self.cartitems.filter(is_order_placed=False)

    @property
    def get_cart_total(self):
        return sum(item.item_total for item in self.get_cart_items)

    def basket_total(self):
        return sum(item.item_total for item in self.cartitems.filter(is_order_placed=False))

    @property
    def get_basket_total(self):
        return sum(item.item_total for item in self.get_cart_items)


# ---------------------------
# Basket Item
# ---------------------------
class BasketItem(models.Model):
    basket_object = models.ForeignKey(Basket, on_delete=models.CASCADE, related_name="cartitems")
    product_object = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    created_date = models.DateTimeField(auto_now=True)
    updated_date = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_order_placed = models.BooleanField(default=False)

    @property
    def item_total(self):
        return self.product_object.price * self.quantity if self.product_object else 0

    def __str__(self):
        return f"{self.quantity} x {self.product_object.name if self.product_object else 'Unknown'} in Basket {self.basket_object.id}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_basket(sender, instance, created, **kwargs):
    if created:
        Basket.objects.create(owner=instance)


# ---------------------------
# Order Model
# ---------------------------
ORDER_STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Processing', 'Processing'),
    ('Shipped', 'Shipped'),
    ('Delivered', 'Delivered'),
    ('Cancelled', 'Cancelled'),
]

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='Pending')

    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)

    shipping_address = models.TextField(blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def order_total(self):
        return sum(item.get_total_price() for item in self.items.all())

    def __str__(self):
        return f"Order {self.order_id} by {self.user.email}"

    class Meta:
        ordering = ['-created_at']

# ---------------------------
# Order Item
# ---------------------------
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.order_id}"

    def get_total_price(self):
        return self.quantity * self.price

class Wishlist(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="wishlists")
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name="wishlisted_by")
    added_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together=('user','product')
        ordering=['added_at']

        def __str__(self):
            return f"({self.user.username}'s wishlist-{self.product.name})"
    
class PasswordReset(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    otp=models.CharField(max_length=6)
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email}-{self.otp}"
    


    @staticmethod
    def generate_otp():
        return str(random.randint(100000,999999))
    

class EmailVerificationCode(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    code=models.CharField(max_length=6)
    created_at=models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now()>self.created_at+datetime.timedelta(minutes=10)
    
class OTPVerification(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    otp=models.CharField(max_length=6)
    created_at=models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    def is_expired(self):
        return timezone.now()>self.created_at+datetime.timedelta(minutes=10)



    
  