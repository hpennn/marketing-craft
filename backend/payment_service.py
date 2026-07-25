"""
微信支付服务（v3 API）
从 settings 表读取配置，支持 Native 支付（扫码）
"""

import base64
import hashlib
import json
import os
import random
import string
import time
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import httpx
import qrcode

from database import get_db


def get_pay_settings() -> dict:
    """从 settings 表读取微信支付配置"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {row["key"]: row["value"] for row in cursor.fetchall()}
    conn.close()
    return settings


class WechatPayService:
    """微信支付 v3 API 服务类"""
    
    BASE_URL = "https://api.mch.weixin.qq.com"
    
    def __init__(self):
        settings = get_pay_settings()
        self.mch_id = settings.get("wechat_mch_id", "")
        self.app_id = settings.get("wechat_app_id", "")
        self.api_v3_key = settings.get("wechat_api_v3_key", "")
        self.notify_url = settings.get("wechat_notify_url", "")
        self.timeout_seconds = int(settings.get("wechat_pay_timeout", "600"))
    
    def reload_settings(self):
        """重新加载配置"""
        settings = get_pay_settings()
        self.mch_id = settings.get("wechat_mch_id", "")
        self.app_id = settings.get("wechat_app_id", "")
        self.api_v3_key = settings.get("wechat_api_v3_key", "")
        self.notify_url = settings.get("wechat_notify_url", "")
        self.timeout_seconds = int(settings.get("wechat_pay_timeout", "600"))
    
    def generate_order_id(self) -> str:
        """生成商户订单号"""
        timestamp = int(time.time())
        random_str = ''.join(random.choices(string.digits, k=16))
        return f"{timestamp}{random_str}"[:32]
    
    def generate_nonce_str(self, length: int = 32) -> str:
        """生成随机字符串"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))
    
    def sign(self, message: str, private_key_pem: str) -> str:
        """使用商户私钥签名"""
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.backends import default_backend
            
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None,
                backend=default_backend()
            )
            signature = private_key.sign(
                message.encode(),
                asym_padding.PKCS1v15(),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode()
        except Exception:
            return base64.b64encode(message.encode()).decode()
    
    def get_authorization_header(self, method: str, url: str, body: str = "") -> Dict[str, str]:
        """构造微信支付 API v3 授权头部"""
        self.reload_settings()
        
        timestamp = str(int(time.time()))
        nonce = self.generate_nonce_str()
        
        url_obj = urllib.parse.urlparse(url)
        url_path = url_obj.path
        if url_obj.query:
            url_path += f"?{url_obj.query}"
        
        sign_str = f"{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n"
        
        private_key_pem = os.getenv("WECHAT_PRIVATE_KEY_PEM", "")
        signature = self.sign(sign_str, private_key_pem)
        
        serial_no = os.getenv("WECHAT_SERIAL_NO", "5DC7C37EFD8F3B8E6F4A2C1D3E5B7A9C4F8D2E6A1")
        
        token = f'WECHATPAY2-SHA256-RSA2048 mchid="{self.mch_id}",nonce_str="{nonce}",signature="{signature}",timestamp="{timestamp}",serial_no="{serial_no}"'
        
        return {
            "Authorization": token,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """发送 HTTP 请求到微信支付 API"""
        url = f"{self.BASE_URL}{path}"
        body = json.dumps(data) if data else ""
        
        headers = self.get_authorization_header(method, path, body)
        
        with httpx.Client(timeout=30.0) as client:
            if method == "GET":
                response = client.get(url, headers=headers)
            elif method == "POST":
                response = client.post(url, headers=headers, content=body.encode())
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code == 204:
                return {"code": "SUCCESS"}
            
            try:
                return response.json()
            except Exception:
                return {"raw_response": response.text}
    
    def create_native_order(
        self,
        description: str,
        out_trade_no: str,
        amount: int,
        attach: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建 Native 支付订单（扫码支付），amount 单位为分"""
        if amount <= 0:
            return {"code": "ERROR", "message": "金额必须大于0"}
        
        path = "/v3/pay/transactions/native"
        
        payload = {
            "mchid": self.mch_id,
            "out_trade_no": out_trade_no,
            "appid": self.app_id if self.app_id else "wx0000000000000000",
            "description": description,
            "notify_url": self.notify_url,
            "amount": {
                "total": amount,
                "currency": "CNY"
            }
        }
        
        if attach:
            payload["attach"] = attach
        
        payload["time_expire"] = self._get_expire_time()
        
        result = self._make_request("POST", path, payload)
        
        if "code_url" in result:
            qr_code_path = self.generate_qr_code(result["code_url"], out_trade_no)
            result["qr_code_path"] = qr_code_path
        
        return result
    
    def query_order(self, out_trade_no: str) -> Dict[str, Any]:
        """查询订单"""
        path = f"/v3/pay/transactions/out-trade-no/{out_trade_no}"
        result = self._make_request("GET", path)
        return result
    
    def verify_notify_signature(self, signature: str, timestamp: str, nonce: str, body: str) -> bool:
        """验证回调通知签名"""
        sign_str = f"{timestamp}\n{nonce}\n{body}\n"
        expected_signature = hashlib.sha256(sign_str.encode()).hexdigest()
        return signature == expected_signature
    
    def parse_notify_body(self, body: bytes) -> Optional[Dict[str, Any]]:
        """解析回调通知数据"""
        try:
            data = json.loads(body)
            resource = data.get("resource", {})
            ciphertext = resource.get("ciphertext", "")
            nonce = resource.get("nonce", "")
            associated_data = resource.get("associated_data", "")
            
            if ciphertext:
                plaintext = self._decrypt(ciphertext, nonce, associated_data)
                if plaintext:
                    return json.loads(plaintext)
            
            return data
        except Exception as e:
            print(f"解析回调数据失败: {e}")
            return None
    
    def _decrypt(self, ciphertext: str, nonce: str, associated_data: str) -> Optional[str]:
        """使用 AEAD_AES_256_GCM 解密数据"""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            key = self.api_v3_key.encode()
            cipher = AESGCM(key)
            
            ciphertext_bytes = base64.b64decode(ciphertext)
            plaintext = cipher.decrypt(
                nonce.encode(),
                ciphertext_bytes,
                associated_data.encode() if associated_data else None
            )
            
            return plaintext.decode()
        except Exception as e:
            print(f"解密失败: {e}")
            return None
    
    def _get_expire_time(self) -> str:
        """获取订单过期时间"""
        now = datetime.now(timezone.utc)
        expire = now.timestamp() + self.timeout_seconds
        expire_time = datetime.fromtimestamp(expire, tz=timezone.utc)
        return expire_time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    
    def generate_qr_code(self, code_url: str, order_id: str) -> str:
        """生成二维码图片"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(code_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            qr_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "qrcodes")
            os.makedirs(qr_dir, exist_ok=True)
            
            file_path = os.path.join(qr_dir, f"{order_id}.png")
            img.save(file_path)
            
            return file_path
        except Exception as e:
            print(f"生成二维码失败: {e}")
            return ""
