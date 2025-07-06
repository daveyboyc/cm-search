"""
Development email backend that logs emails to console
"""
from django.core.mail.backends.base import BaseEmailBackend
import logging

logger = logging.getLogger(__name__)

class LoggingEmailBackend(BaseEmailBackend):
    """Email backend that logs emails instead of sending them"""
    
    def send_messages(self, email_messages):
        """Log email messages instead of sending them"""
        for message in email_messages:
            logger.info(f"""
╔══════════════════════════════════════════════════════════════╗
║                      EMAIL NOTIFICATION                       ║
╠══════════════════════════════════════════════════════════════╣
║ To: {message.to}
║ From: {message.from_email}
║ Subject: {message.subject}
╠══════════════════════════════════════════════════════════════╣
║ Body:
{message.body}
╚══════════════════════════════════════════════════════════════╝
            """)
            
            # If there's an HTML alternative, log it too
            if hasattr(message, 'alternatives') and message.alternatives:
                for content, mimetype in message.alternatives:
                    if mimetype == 'text/html':
                        logger.info(f"HTML version also available (not shown)")
        
        return len(email_messages)