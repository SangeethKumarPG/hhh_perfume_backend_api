# payment/utils.py

from io import BytesIO
from django.template.loader import get_template, render_to_string
from xhtml2pdf import pisa
from django.core.mail import EmailMessage,send_mail
from django.conf import settings
import random


def render_to_pdf(template_src, context_dict=None):
    """
    Renders an HTML template to a PDF using xhtml2pdf.
    """
    if context_dict is None:
        context_dict = {}

    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), dest=result)

    if not pdf.err:
        return result.getvalue()
    return None


def send_payment_confirmation_emails(Order, customer_email, admin_email):
    """
    Sends payment confirmation emails to both the customer and admin
    with a PDF invoice attached.
    """
    context = {'Order': Order}
    pdf = render_to_pdf('payment_invoices.html', context)

    if not pdf:
        print("❌ Failed to generate PDF invoice.")
        return False

    try:
        # 1️⃣ Customer Email
        customer_subject = f"🧾 Payment Confirmation - Order #{Order.order_id}"
        customer_body_html = render_to_string('payment_confirmation.html', context)

        email_cust = EmailMessage(
            subject=customer_subject,
            body=customer_body_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer_email],
        )
        email_cust.content_subtype = 'html'
        email_cust.attach(f"Invoice_{Order.order_id}.pdf", pdf, "application/pdf")
        email_cust.send()
        print("✅ Customer email sent.")

        # 2️⃣ Admin Email
        admin_subject = f"📥 New Paid Order - #{Order.order_id}"
        admin_body_html = render_to_string('payment_notify.html', {
            'Order': Order,
            'customer_email': customer_email,
        })

        email_admin = EmailMessage(
            subject=admin_subject,
            body=admin_body_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[admin_email],
        )
        email_admin.content_subtype = 'html'
        email_admin.attach(f"Invoice_{Order.order_id}.pdf", pdf, "application/pdf")
        email_admin.send()
        print("✅ Admin email sent.")

        return True

    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False

def generate_otp():
    return str(random.randint(100000,999999))

def send_verification_email(user,code):
    subject="Password ResetVerification Code"
    message=f"Hi{user.username},\n\n Otp for Password reset code is:{code}\nThis code will expire once used.\n\nIf you didn’t request this, please ignore."
    send_mail(
        subject,
        message,
        "no-reply@yourdomain.com",
        [user.email],
        fail_silently=False,
    )