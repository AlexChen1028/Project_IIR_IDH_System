# interface/utils.py
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from django.conf import settings

KEY_FILE_PATH = os.path.join(settings.BASE_DIR, 'secret.key')

class CryptoManager:
    _key = None

    @classmethod
    def get_key(cls):
        """讀取原始金鑰 (bytes)"""
        if cls._key is None:
            if not os.path.exists(KEY_FILE_PATH):
                key = Fernet.generate_key()
                with open(KEY_FILE_PATH, 'wb') as f:
                    f.write(key)
            else:
                with open(KEY_FILE_PATH, 'rb') as f:
                    key = f.read()
            cls._key = key
        return cls._key

    @classmethod
    def get_fernet(cls):
        """取得原本的隨機加密器 (用於姓名等不需當PK的欄位)"""
        return Fernet(cls.get_key())

    @classmethod
    def encrypt_deterministic(cls, text):
        """
        [決定性加密] 用於 ID
        相同的輸入永遠產生相同的亂碼
        """
        if not text: return text
        text = str(text)
        
        # 1. 準備金鑰 (解碼 base64 獲得 32 bytes raw key)
        raw_key = base64.urlsafe_b64decode(cls.get_key())
        
        # 2. 設定固定 IV (初始化向量)
        # 為了讓結果固定，IV 必須固定。這裡使用 16 個 0，或您可以自訂
        iv = b'0' * 16 
        
        # 3. 建立加密器 (AES-CBC)
        backend = default_backend()
        cipher = Cipher(algorithms.AES(raw_key), modes.CBC(iv), backend=backend)
        encryptor = cipher.encryptor()
        
        # 4. 填充資料 (Padding) 到 128 bit 倍數
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(text.encode()) + padder.finalize()
        
        # 5. 加密並回傳 Base64 字串
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return base64.urlsafe_b64encode(encrypted).decode()

    @classmethod
    def decrypt_deterministic(cls, text):
        """
        [決定性解密]
        """
        if not text: return text
        try:
            # 1. 準備金鑰與 IV
            raw_key = base64.urlsafe_b64decode(cls.get_key())
            iv = b'0' * 16
            
            # 2. 解碼 Base64
            data = base64.urlsafe_b64decode(text)
            
            # 3. 建立解密器
            backend = default_backend()
            cipher = Cipher(algorithms.AES(raw_key), modes.CBC(iv), backend=backend)
            decryptor = cipher.decryptor()
            
            # 4. 解密與移除 Padding
            padded_data = decryptor.update(data) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()
            
            return data.decode()
        except Exception as e:
            return text