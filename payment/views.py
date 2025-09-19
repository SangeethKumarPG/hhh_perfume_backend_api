from django.conf import settings
from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
import razorpay
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from django.utils.crypto import get_random_string
from store.models import Basket, Order, OrderItem
from store.serializers import CartItemSerializer
from payment.models import Payment
from rest_framework.permissions import IsAuthenticated
from store.models import Order, BasketItem
from payment.models import Payment, Invoice
from payment.serializers import PaymentSerializer, InvoiceSerializer

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


# class PaymentViewSet(viewsets.ModelViewSet):
#     queryset = Payment.objects.all()
#     serializer_class = PaymentSerializer
#     permission_classes = [permissions.AllowAny]

#     @action(detail=False, methods=['get', 'post'], url_path='checkout', name='checkout')
#     def checkout(self, request):
#         if request.method == "POST":
#             try:
#                 amount = int(request.data.get("amount", 0)) * 100
#                 if amount <= 0:
#                     return Response({"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

#                 payment_order = client.order.create({
#                     "amount": amount,
#                     "currency": "INR",
#                     "payment_capture": "1"
#                 })

#                 return render(request, 'checkout.html', {
#                     'payment': payment_order,
#                     'key_id': settings.RAZORPAY_KEY_ID,
#                     'amount': amount,
#                 })
#             except Exception as e:
#                 return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#                 # return render(request,'home.html', {'error': str(e)})
#         # return render(request, 'home.html')

#     @action(detail=False, methods=['post'], url_path='payment-status')
#     def payment_status(self, request):
#         try:
#             data = request.data
#             client.utility.verify_payment_signature({
#                 'razorpay_order_id': data.get('razorpay_order_id'),
#                 'razorpay_payment_id': data.get('razorpay_payment_id'),
#                 'razorpay_signature': data.get('razorpay_signature')
#             })

#             razorpay_order = client.order.fetch(data.get('razorpay_order_id'))
#             amount = razorpay_order['amount'] / 100

#             order = Order.objects.filter(razorpay_order_id=data.get('razorpay_order_id')).first()
#             if not order:
#                 return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

#             Payment.objects.create(
#                 user=request.user if request.user.is_authenticated else None,
#                 payment_id=data.get('razorpay_payment_id'),
#                 order_id=data.get('razorpay_order_id'),
#                 amount=amount,
#                 status='Success',
#                 payment_method='Razorpay'
#             )

#             return Response({"message": "Payment successful"}, status=status.HTTP_200_OK)

#         except razorpay.errors.SignatureVerificationError:
#             return Response({"error": "Signature verification failed."}, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Assuming Invoice model has a user field related to the user
        return Invoice.objects.filter(user=self.request.user)

# Fetch payment details from Razorpay API and create a Payment object
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='user-cart-checkout', permission_classes=[IsAuthenticated])
    def user_cart_checkout(self, request):
        try:
            basket = Basket.objects.filter(owner=request.user, is_active=True).first()
            if not basket:
                return Response({"error": "No active basket found"}, status=status.HTTP_404_NOT_FOUND)

            items = basket.cartitems.filter(is_active=True, is_order_placed=False)
            if not items.exists():
                return Response({"error": "Basket is empty"}, status=status.HTTP_404_NOT_FOUND)

            total_amount = sum([item.product_object.price * item.quantity for item in items])
            razorpay_amount = int(total_amount * 100)  # Razorpay expects paise

            payment_order = client.order.create({
                "amount": razorpay_amount,
                "currency": "INR",
                "payment_capture": "1",
            })

            order = Order.objects.create(
                user=request.user,
                order_id=get_random_string(12),
                razorpay_order_id=payment_order["id"],
                amount=total_amount,
                status="Pending",
                first_name=request.data.get("first_name"),
                last_name=request.data.get("last_name"),
                phone_number=request.data.get("phone_number"),
                city=request.data.get("city"),
                state=request.data.get("state"),
                pincode=request.data.get("pincode"),
                shipping_address=request.data.get("shipping_address"),
                billing_address=request.data.get("billing_address"),
                notes=request.data.get("notes"),
            )

            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product_object,
                    quantity=item.quantity,
                    price=item.product_object.price
                )

            Payment.objects.create(
                user=request.user,
                order=order,
                amount=total_amount,
                status="Created",
                payment_method="online",   # Razorpay
                payment_id=payment_order["id"]
            )

            items_data = CartItemSerializer(items, many=True).data

            return Response({
                "order_id": order.order_id,
                "basket_items": items_data,
                "total_amount": float(total_amount),
                "razorpay_order": payment_order,
                "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    @action(detail=False, methods=['post'], url_path='payment-status')
    def payment_status(self, request):
        try:
            data = request.data

            
            client.utility.verify_payment_signature({
                'razorpay_order_id': data.get('razorpay_order_id'),
                'razorpay_payment_id': data.get('razorpay_payment_id'),
                'razorpay_signature': data.get('razorpay_signature'),
            })

            
            order = Order.objects.filter(razorpay_order_id=data.get('razorpay_order_id')).first()
            if not order:
                return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

           
            payment = Payment.objects.filter(order=order).first()
            if payment:
                payment.payment_id = data.get("razorpay_payment_id")
                payment.status = "Paid"
                payment.save()

           
            order.status = "Paid"
            order.save()

         
            BasketItem.objects.filter(
                basket_object__owner=order.user,
                is_active=True,
                is_order_placed=False
            ).update(is_order_placed=True)


            order_items = order.items.all()  # related_name='items' in OrderItem model
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <style>
                body {{
                font-family: Arial, sans-serif;
                background: #f9f9f9;
                padding: 20px;
                color: #333;
                }}
                .container {{
                max-width: 600px;
                margin: auto;
                background: #fff;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0px 2px 8px rgba(0,0,0,0.1);
                }}
                h2 {{ color: #2c3e50; }}
                table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                }}
                th, td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
                }}
                th {{
                background: #2c3e50;
                color: #fff;
                }}
                tfoot td {{
                font-weight: bold;
                }}
                .address {{
                margin-top: 20px;
                background: #f2f2f2;
                padding: 10px;
                border-radius: 5px;
                }}
                .footer {{
                margin-top: 20px;
                font-size: 12px;
                color: #777;
                text-align: center;
                }}
            </style>
            </head>
            <body>
            <div class="container">
                <h2>Thank you for your purchase, {order.first_name}!</h2>
                <p>Your order <strong>{order.order_id}</strong> has been confirmed.</p>

                <h3>Order Details:</h3>
                <table>
                <thead>
                    <tr>
                    <th>Product</th>
                    <th>Price (₹)</th>
                    <th>Qty</th>
                    <th>Total (₹)</th>
                    </tr>
                </thead>
                <tbody>
            """

            # Loop through order items
            for item in order_items:
                html_content += f"""
                    <tr>
                    <td>{item.product.name}</td>
                    <td>{item.price}</td>
                    <td>{item.quantity}</td>
                    <td>{item.get_total_price()}</td>
                    </tr>
                """

            html_content += f"""
                </tbody>
                <tfoot>
                    <tr>
                    <td colspan="3">Total</td>
                    <td>{order.amount}</td>
                    </tr>
                </tfoot>
                </table>

                <div class="address">
                <h3>Shipping Address</h3>
                <p>{order.shipping_address}<br>
                    {order.city}, {order.state} - {order.pincode}<br>
                    Phone: {order.phone_number}
                </p>
                </div>

                <div class="footer">
                <p>HHH Perfumes &copy; {order.created_at.year}</p>
                </div>
            </div>
            </body>
            </html>
            """

            # Send email
            email = EmailMessage(
                subject=f"Order Confirmation - {order.order_id}",
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[order.user.email],
                cc=["info@hhhperfumes.in"],  
            )
            email.content_subtype = "html" 
            email.send()


            return Response({
                "message": "Payment verified and updated successfully",
                "order_id": order.order_id,
                "payment_id": data.get("razorpay_payment_id")
            }, status=status.HTTP_200_OK)

        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "Signature verification failed"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print("error", str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
