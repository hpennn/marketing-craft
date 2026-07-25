"""
短信服务模块 - 阿里云SMS对接，开发模式支持
"""

import os
import logging

logger = logging.getLogger(__name__)

# 阿里云SMS配置（通过环境变量读取）
SMS_ACCESS_KEY_ID = os.getenv("SMS_ACCESS_KEY_ID", "")
SMS_ACCESS_KEY_SECRET = os.getenv("SMS_ACCESS_KEY_SECRET", "")
SMS_SIGN_NAME = os.getenv("SMS_SIGN_NAME", "")
SMS_TEMPLATE_CODE = os.getenv("SMS_TEMPLATE_CODE", "")

# 是否为开发模式（未配置SMS环境变量时自动开启）
DEV_MODE = not (SMS_ACCESS_KEY_ID and SMS_ACCESS_KEY_SECRET and SMS_SIGN_NAME and SMS_TEMPLATE_CODE)


def send_sms(phone: str, code: str) -> dict:
    """发送短信验证码
    
    开发模式：验证码打印到日志，不实际发送
    生产模式：调用阿里云SMS API
    
    返回: {"success": bool, "message": str, "code": str|None}
    """
    if DEV_MODE:
        # 开发模式：不发送短信，验证码通过日志和返回值传递
        logger.info(f"[DEV MODE] 验证码: {code} -> 手机号: {phone}")
        print(f"[SMS DEV] 手机号: {phone}, 验证码: {code}")
        return {
            "success": True,
            "message": "验证码已发送（开发模式）",
            "code": code,  # 开发模式返回验证码，前端可直接展示
        }

    # 生产模式：调用阿里云SMS
    try:
        from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest
        from aliyunsdkcore.client import AcsClient

        client = AcsClient(SMS_ACCESS_KEY_ID, SMS_ACCESS_KEY_SECRET, "cn-hangzhou")
        request = SendSmsRequest.SendSmsRequest()
        request.set_PhoneNumbers(phone)
        request.set_SignName(SMS_SIGN_NAME)
        request.set_TemplateCode(SMS_TEMPLATE_CODE)
        request.set_TemplateParam(f'{{"code":"{code}"}}')

        response = client.do_action_with_exception(request)
        import json
        result = json.loads(response.decode("utf-8"))

        if result.get("Code") == "OK":
            logger.info(f"短信发送成功: {phone}")
            return {"success": True, "message": "验证码已发送"}
        else:
            logger.error(f"短信发送失败: {phone}, 原因: {result.get('Message', '未知')}")
            return {"success": False, "message": f"短信发送失败: {result.get('Message', '未知')}"}

    except ImportError:
        logger.warning("阿里云SMS SDK未安装，回退到开发模式")
        print(f"[SMS FALLBACK] 手机号: {phone}, 验证码: {code}")
        return {"success": True, "message": "验证码已发送（SDK未安装，开发模式）", "code": code}
    except Exception as e:
        logger.error(f"短信发送异常: {e}")
        return {"success": False, "message": f"短信发送异常: {str(e)}"}
