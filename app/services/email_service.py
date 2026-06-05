import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def _send_via_smtp(email: str, code: str) -> bool:
        host = (settings.SMTP_HOST or "").strip()
        from_email = (settings.SMTP_FROM_EMAIL or "").strip()
        username = (settings.SMTP_USERNAME or "").strip()
        password = settings.SMTP_PASSWORD or ""

        if not host or not from_email:
            return False

        msg = EmailMessage()
        msg["Subject"] = "CookWise Email Dogrulama Kodunuz"
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{from_email}>"
        msg["To"] = email
        msg.set_content(
            (
                "CookWise'a hos geldiniz!\n\n"
                "Hesabinizi dogrulamak icin asagidaki 6 haneli kodu uygulamaya girin:\n\n"
                f"{code}\n\n"
                "Kodunuz 10 dakika boyunca gecerlidir."
            )
        )

        try:
            if settings.SMTP_USE_SSL:
                with smtplib.SMTP_SSL(host, settings.SMTP_PORT, timeout=15) as server:
                    if username and password:
                        server.login(username, password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(host, settings.SMTP_PORT, timeout=15) as server:
                    if settings.SMTP_USE_TLS:
                        server.starttls()
                    if username and password:
                        server.login(username, password)
                    server.send_message(msg)
            logger.info(f"REAL EMAIL SENT TO: {email}")
            return True
        except Exception as exc:
            logger.error(f"SMTP send failed, fallback to simulation. Error: {exc}")
            return False

    @staticmethod
    def send_verification_email(email: str, code: str):
        """
        SMTP ayarlıysa gerçek mail gönderir; değilse simülasyon fallback.
        """
        if EmailService._send_via_smtp(email, code):
            return True

        # Display the code prominently in the terminal for the user to see and use
        logger.info("=" * 50)
        logger.info(f"SIMULATED EMAIL SENT TO: {email}")
        logger.info(f"SUBJECT: CookWise Email Dogrulama Kodunuz")
        logger.info(f"BODY:")
        logger.info(f"CookWise'a hos geldiniz! Hesabinizi dogrulamak icin")
        logger.info(f"asagidaki 6 haneli kodu uygulamaniza giriniz:")
        logger.info(f"")
        logger.info(f"  [ {code} ]  ")
        logger.info(f"")
        logger.info(f"Kodunuz 10 dakika boyunca gecerlidir.")
        logger.info("=" * 50)
        
        # We can also print to console directly so it's impossible to miss
        print(f"\n\n{'*'*50}")
        print(f"📧 EMAIL DOGRULAMA KODU (SIMULASYON):")
        print(f"Gonderilen adres: {email}")
        print(f"DOGRULAMA KODU: {code}")
        print(f"{'*'*50}\n\n")

        return True
