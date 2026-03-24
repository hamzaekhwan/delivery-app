import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class GreenAPIService:
    """
    خدمة إرسال رسائل الواتساب عبر Green API
    """

    def __init__(self):
        self.instance_id = getattr(settings, "GREEN_API_INSTANCE_ID", "")
        self.api_token = getattr(settings, "GREEN_API_TOKEN", "")
        self.default_country_code = getattr(
            settings, "GREEN_API_DEFAULT_COUNTRY_CODE", "963"
        )
        self.base_url = f"https://api.green-api.com/waInstance{self.instance_id}"

    def format_phone_number(self, phone_number):
        phone = "".join(filter(str.isdigit, phone_number))

        if phone.startswith("00"):
            phone = phone[2:]
        elif phone.startswith("09") and len(phone) == 10:
            phone = self.default_country_code + phone[1:]
        elif len(phone) == 9 and phone.startswith("9"):
            phone = self.default_country_code + phone
        elif phone.startswith("0") and len(phone) > 10:
            phone = phone[1:]

        return phone + "@c.us"

    def send_message(self, phone_number, message):
        """
        إرسال رسالة واتساب
        """
        if not self.instance_id or not self.api_token:
            return {
                "success": False,
                "error": "Green API credentials not configured",
            }

        url = f"{self.base_url}/sendMessage/{self.api_token}"

        payload = {
            "chatId": self.format_phone_number(phone_number),
            "message": message,
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    def send_otp(self, phone_number, otp_code, otp_type="signup"):
        """
        إرسال رمز OTP عبر الواتساب
        """
        if otp_type == "signup":
            message = f"""🚗 مرحباً بك في Super Driver!

    رمز التحقق الخاص بك هو: *{otp_code}*

    ⏰ هذا الرمز صالح لمدة 10 دقائق.
    ❌ لا تشارك هذا الرمز مع أي شخص."""

        else:
            message = f"""🔑 Super Driver - إعادة تعيين كلمة المرور

    رمز التحقق الخاص بك هو: *{otp_code}*

    ⏰ هذا الرمز صالح لمدة 10 دقائق.
    ❌ إذا لم تطلب هذا الرمز، يرجى تجاهل هذه الرسالة."""

        return self.send_message(phone_number, message)


class AmanGateService:
    """
    خدمة إرسال OTP عبر SMS - Aman Gate
    https://aman-gate.com
    """

    BASE_URL = "https://www.aman-gate.com/api/otp/send/"

    def __init__(self):
        self.api_token = getattr(settings, "AMAN_GATE_API_TOKEN", "")
        self.template_id = getattr(settings, "AMAN_GATE_TEMPLATE_ID", 1)

    def send_otp(self, phone_number, otp_code):
        if not self.api_token:
            return {"success": False, "error": "Aman Gate token not configured"}

        # تنسيق الرقم بصيغة +XXXXXXXXXXX
        phone = "".join(filter(str.isdigit, phone_number))
        if phone.startswith("09") and len(phone) == 10:
            phone = "963" + phone[1:]
        elif phone.startswith("00"):
            phone = phone[2:]
        gsm = phone

        payload = {
            "gsm": gsm,
            "template_id": self.template_id,
            "code": str(otp_code),
            "language": 0,  # Arabic
        }

        headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.BASE_URL, json=payload, headers=headers, timeout=30
            )
            data = response.json() if response.content else {}
            if response.status_code in (200, 201) and data.get("status") == "sent":
                return {"success": True, "data": data, "channel": "sms"}
            logger.error(
                "Aman Gate error %s for %s: %s", response.status_code, gsm, data
            )
            return {"success": False, "error": data}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}


# إنشاء instances
green_api_service = GreenAPIService()
aman_gate_service = AmanGateService()


def send_otp_with_fallback(phone_number, otp_code, otp_type="signup"):
    """
    إرسال OTP عبر SMS حالياً (WhatsApp معطّل مؤقتاً)
    لإعادة تفعيل WhatsApp: فك التعليق عن الكود أدناه
    """
    # # محاولة 1: WhatsApp (معطّل مؤقتاً)
    # result = green_api_service.send_otp(phone_number, otp_code, otp_type)
    # if result.get("success"):
    #     result["channel"] = "whatsapp"
    #     return result
    # logger.warning("WhatsApp OTP failed for %s: %s", phone_number, result.get("error"))

    # SMS via Aman Gate
    result = aman_gate_service.send_otp(phone_number, otp_code)
    if result.get("success"):
        return result

    logger.error("SMS OTP failed for %s: %s", phone_number, result.get("error"))
    return {"success": False, "error": "فشل إرسال رمز التحقق"}
