from django.db import models
from django.contrib.auth import get_user_model
from store.models import Order  # Correct import from store app

User = get_user_model()

# ---------------------------
# Payment Model
# ---------------------------
class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('online', 'Online'),
        ('COD', 'Cash on Delivery'),
        ('Stripe', 'Stripe'),
        ('Paypal', 'Paypal'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('Created', 'Created'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment')
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Created')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.payment_id or 'N/A'} for Order {self.order.order_id}"


# ---------------------------
# Invoice Model
# ---------------------------
class Invoice(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    invoice_number = models.CharField(max_length=20, unique=True)
    pdf_file = models.FileField(upload_to='invoices/')
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice {self.invoice_number} for Order {self.order.order_id}"
