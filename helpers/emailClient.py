from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
import ssl

sender_mail = os.getenv("EMAIL_ADDRESS")
sender_pass = os.getenv("EMAIL_PASSWORD")


def send_verification_email(receiver_email, verification_link, verification_token):
    # 1. Configuration settings
    smtp_server = "smtp.gmail.com"
    port = 465  # SSL standard port
    sender_email = sender_mail
    sender_password = sender_pass

    # 3. Create the multi-part email container
    message = MIMEMultipart("alternative")
    message["Subject"] = "WaitForIt Account Verification"
    message["From"] = sender_email
    message["To"] = receiver_email

    # 4. Craft plain text and HTML bodies
    text_content = f"Click the verification link, to complete your registration: {verification_link}"
    html_content = f"""
    <html>
      <body>
        <h2>User Account Verification</h2>
        <p>Thank you for signing up. Please use the verification link below:</p>
        <h1 style="color: #4A90E2; letter-spacing: 2px;">{verification_link}</h1>
        <p>This link will expire within 24 hours.</p>
      </body>
    </html>
    """

    # Attach both parts (fallback plain text and primary HTML)
    message.attach(MIMEText(text_content, "plain"))
    message.attach(MIMEText(html_content, "html"))

    # 5. Establish secure connection and send the email
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print(f"Verification email sent successfully to {receiver_email}!")
        return verification_token
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def send_password_reset_email(receiver_email, reset_link, reset_token):
    # 1. Configuration settings
    smtp_server = "smtp.gmail.com"
    port = 465  # SSL standard port
    sender_email = sender_mail
    sender_password = sender_pass

    # 3. Create the multi-part email container
    message = MIMEMultipart("alternative")
    message["Subject"] = "Account Password Reset"
    message["From"] = sender_email
    message["To"] = receiver_email

    # 4. Craft plain text and HTML bodies
    text_content = (
        f"Click the password reset link, to reset your account password: {reset_link}"
    )
    html_content = f"""
    <html>
      <body>
        <h2>Account Password Reset</h2>
        <p>Follow this link to reset your password:</p>
        <h1 style="color: #4A90E2; letter-spacing: 2px;">{reset_link}</h1>
        <p>If you did not make this request, ignore this mail</p>
        <p>This link will expire within 24 hours.</p>
      </body>
    </html>
    """

    # Attach both parts (fallback plain text and primary HTML)
    message.attach(MIMEText(text_content, "plain"))
    message.attach(MIMEText(html_content, "html"))

    # 5. Establish secure connection and send the email
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print(f"Password reset email sent successfully to {receiver_email}!")
        return reset_token
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
