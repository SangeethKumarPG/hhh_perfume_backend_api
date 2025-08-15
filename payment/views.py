from django.conf import settings
from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
import razorpay

from store.models import Order
from payment.models import Payment, Invoice
from payment.serializers import PaymentSerializer, InvoiceSerializer

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get', 'post'], url_path='checkout', name='checkout')
    def checkout(self, request):
        if request.method == "POST":
            try:
                amount = int(request.data.get("amount", 0)) * 100
                if amount <= 0:
                    return Response({"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

                payment_order = client.order.create({
                    "amount": amount,
                    "currency": "INR",
                    "payment_capture": "1"
                })

                return render(request, 'checkout.html', {
                    'payment': payment_order,
                    'key_id': settings.RAZORPAY_KEY_ID,
                    'amount': amount,
                })
            except Exception as e:
                return render(request, 'home.html', {'error': str(e)})

        return render(request, 'home.html')

    @action(detail=False, methods=['post'], url_path='payment-status')
    def payment_status(self, request):
        try:
            data = request.data
            client.utility.verify_payment_signature({
                'razorpay_order_id': data.get('razorpay_order_id'),
                'razorpay_payment_id': data.get('razorpay_payment_id'),
                'razorpay_signature': data.get('razorpay_signature')
            })

            razorpay_order = client.order.fetch(data.get('razorpay_order_id'))
            amount = razorpay_order['amount'] / 100

            order = Order.objects.filter(razorpay_order_id=data.get('razorpay_order_id')).first()
            if not order:
                return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

            Payment.objects.create(
                user=request.user if request.user.is_authenticated else None,
                payment_id=data.get('razorpay_payment_id'),
                order_id=data.get('razorpay_order_id'),
                amount=amount,
                status='Success',
                payment_method='Razorpay'
            )

            return Response({"message": "Payment successful"}, status=status.HTTP_200_OK)

        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "Signature verification failed."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Assuming Invoice model has a user field related to the user
        return Invoice.objects.filter(user=self.request.user)
