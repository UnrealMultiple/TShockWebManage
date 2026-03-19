import asyncio
import smtplib
from concurrent.futures import ThreadPoolExecutor
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from app.core.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM_NAME

_smtp_executor = ThreadPoolExecutor(max_workers=2)

def _decode_smtp_err(e: Exception) -> str:
    if isinstance(e, UnicodeDecodeError):
        return "SMTP 握手编码错误，请检查 host/port 是否匹配"
    if hasattr(e, 'smtp_error') and isinstance(e.smtp_error, bytes):
        for enc in ('utf-8', 'gbk', 'gb2312', 'latin-1'):
            try:
                return f"[{e.smtp_code}] {e.smtp_error.decode(enc)}"
            except Exception:
                continue
        return f"[{e.smtp_code}] {e.smtp_error!r}"
    return str(e)

class RobustSMTP_SSL(smtplib.SMTP_SSL):
    @staticmethod
    def _safe_decode(b: bytes) -> str:
        for enc in ('ascii', 'utf-8', 'gbk', 'gb2312', 'latin-1'):
            try:
                return b.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return b.decode('latin-1')

    def ehlo(self, name: str = '') -> tuple:
        self.esmtp_features = {}
        self.putcmd(self.ehlo_msg, name or self.local_hostname)
        (code, msg) = self.getreply()
        if code == -1 and len(msg) == 0:
            self.close()
            raise smtplib.SMTPServerDisconnected("服务器未连接")
        self.ehlo_resp = msg
        if code != 250:
            return (code, msg)
        self.does_esmtp = True
        resp = self._safe_decode(self.ehlo_resp)
        self.ehlo_resp = resp.encode('ascii', errors='ignore')
        return (code, msg)

def _smtp_send_sync(to_email: str, code: str):
    # 构建邮件正文
    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;
                padding:32px;background:#0f172a;color:#e2e8f0;border-radius:12px;">
      <h2 style="color:#60a5fa;margin-bottom:8px;">TShock 管理平台</h2>
      <p style="color:#94a3b8;">您的注册验证码：</p>
      <div style="font-size:36px;font-weight:bold;color:#93c5fd;letter-spacing:10px;
                  padding:20px;background:#1e3a5f;border-radius:8px;text-align:center;margin:16px 0;">
        {code}
      </div>
      <p style="color:#64748b;font-size:13px;">验证码 5 分钟内有效，请勿泄露给他人。</p>
    </div>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header("TShock管理平台 注册验证码", "utf-8")
    msg["From"]    = formataddr((str(Header(SMTP_FROM_NAME, "utf-8")), SMTP_USER))
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        local_h = "localhost"
        if SMTP_PORT == 465:
            # 163 等国内邮箱通常在 465 端口强制使用 SSL
            try:
                with RobustSMTP_SSL(SMTP_HOST, SMTP_PORT, local_hostname=local_h, timeout=10) as smtp:
                    smtp.login(SMTP_USER, SMTP_PASS)
                    smtp.send_message(msg)
            except Exception:
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, local_hostname=local_h, timeout=10) as smtp:
                    smtp.login(SMTP_USER, SMTP_PASS)
                    smtp.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, local_hostname=local_h, timeout=10) as smtp:
                smtp.ehlo()
                if smtp.has_extn('starttls'):
                    smtp.starttls()
                    smtp.ehlo()
                smtp.login(SMTP_USER, SMTP_PASS)
                smtp.send_message(msg)
    except Exception as e:
        raise RuntimeError(_decode_smtp_err(e)) from e

async def send_email_code(to_email: str, code: str):
    if not SMTP_USER:
        print(f"[SMTP 未配置] 验证码 -> {to_email} : {code}")
        return
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_smtp_executor, _smtp_send_sync, to_email, code)
