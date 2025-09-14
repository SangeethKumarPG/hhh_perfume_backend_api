from rest_framework import serializers
from .models import Payment, Invoice
from store.serializers import OrderSerializer 

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ['id', 'payment_id', 'created_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def validate_payment_method(self, value):
        if value not in dict(Payment.PAYMENT_METHOD_CHOICES):
            raise serializers.ValidationError('Invalid payment method.')
        return value

    def validate_status(self, value):
        if value not in dict(Payment.PAYMENT_STATUS_CHOICES):
            raise serializers.ValidationError('Invalid payment status.')
        return value

    def validate(self, data):
        order = data.get('order')
        if not order:
            raise serializers.ValidationError('Order cannot be null.')
        if order.is_paid and self.instance is None:
            raise serializers.ValidationError('Order is already marked as paid.')
        return data

    def update(self, instance, validated_data):
        status = validated_data.get('status', instance.status)
        instance = super().update(instance, validated_data)
        if status == 'Paid' and not instance.order.is_paid:
            instance.order.is_paid = True
            instance.order.save()
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['order'] = OrderSerializer(instance.order).data
        return representation


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'
