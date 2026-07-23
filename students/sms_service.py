import requests
from dotenv import load_dotenv
import os
load_dotenv()

SMS_LOGIN = os.getenv('SMS_LOGIN')
SMS_PASSWORD = os.getenv('SMS_PASSWORD')

def send_sms(phone_number, text):
    if not phone_number:
        return False
    
    number = phone_number.strip()
    if number.startswith('0'):
        number = '+92' + number[1:]
    elif not number.startswith('+'):
        number = '+92' + number

    try:
        response = requests.post(
            'https://api.sms-gate.app/3rdparty/v1/messages',
            auth=(SMS_LOGIN, SMS_PASSWORD),
            json={
                'message': text,
                'phoneNumbers': [number]
            }
        )
        print(f"SMS to {number}: {response.json()['state']}")
        return True
    except Exception as e:
        print(f"SMS failed: {e}")
        return False