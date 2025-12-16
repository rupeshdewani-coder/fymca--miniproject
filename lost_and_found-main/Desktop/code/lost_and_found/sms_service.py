"""
Mock SMS service for sending OTPs.
In a real implementation, this would integrate with an actual SMS provider like Twilio.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_sms_via_email(phone, message):
    """
    Send SMS via email-to-SMS gateway.
    This is a mock implementation that just prints to console.
    In a real implementation, you would use an SMS service provider.
    
    Args:
        phone (str): Phone number in +91 format
        message (str): Message to send
    """
    # Extract the 10-digit number from +91 format
    if phone.startswith('+91') and len(phone) == 13:
        phone_number = phone[3:]  # Remove +91 prefix
        logger.info(f"Sending SMS to {phone}: {message}")
        print(f"SMS sent to {phone}: {message}")
        return True
    else:
        logger.error(f"Invalid phone number format: {phone}")
        return False

def send_otp_sms(phone, otp):
    """
    Send OTP via SMS.
    
    Args:
        phone (str): Phone number in +91 format
        otp (str): 6-digit OTP to send
    """
    message = f"Your OTP for Lost and Found registration is: {otp}. Valid for 10 minutes."
    return send_sms_via_email(phone, message)

# For testing purposes
if __name__ == "__main__":
    # Test sending an OTP
    send_otp_sms("+919876543210", "123456")