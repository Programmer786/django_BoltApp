from django.conf import settings
from django.core.mail import send_mail

def send_account_created_email(email, username, password, first_name, last_name, email_token):
    """
    Email the new user with their account details and activation link
    """
    subject = 'Your Account Has Been Created'
    email_from = settings.EMAIL_HOST_USER
    
    # Create a plain text message
    message = f"""
    Hello {first_name} {last_name},
    
    Your account has been created successfully.
    
    Here are your login details:
    Username: {username}
    Password: {password}
    
    Please activate your account by clicking this link:
    http://{settings.DOMAIN_NAME}/activate/{email_token}
    
    After activation, you can login at: http://{settings.DOMAIN_NAME}/login/
    
    We recommend changing your password after first login.
    
    Best regards,
    {getattr(settings, 'EMAIL_FROM_NAME', 'The Bolt Team')}
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email=email_from,
        recipient_list=[email],
        fail_silently=False,
    )
