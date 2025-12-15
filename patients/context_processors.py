from django.conf import settings # <--- ایمپورت یادت نره
import requests

def sms_credit_balance(request):
    try:
        url = f"{settings.SMS_BASE_URL}credit" # <--- استفاده از Base URL
        headers = {"X-API-KEY": settings.SMS_API_KEY} # <--- استفاده از Key
        
        response = requests.get(url, headers=headers, timeout=3)
        
        if response.status_code == 200 and response.json()['status'] == 1:
            credit = response.json()['data']
            formatted_credit = "{:,}".format(credit)
        else:
            formatted_credit = "---"
            
    except:
        formatted_credit = "آفلاین"

    return {'sms_balance': formatted_credit}