"""
Email Notification Module
Handles instant alerts and scheduled digest emails for silver deals
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
from config import Config
from database.models import DatabaseManager, AlertHistory

logger = logging.getLogger(__name__)

class EmailNotifier:
    """Handles email notifications for silver deals"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()
        self.enabled = Config.ENABLE_EMAIL_NOTIFICATIONS
        
        if self.enabled:
            self._validate_config()
    
    def _validate_config(self):
        """Validate email configuration"""
        if not Config.SMTP_USERNAME:
            logger.error("SMTP_USERNAME not configured")
            self.enabled = False
        if not Config.SMTP_PASSWORD:
            logger.error("SMTP_PASSWORD not configured")
            self.enabled = False
        if not Config.EMAIL_TO:
            logger.error("EMAIL_TO not configured")
            self.enabled = False
    
    def send_fire_alarm_alert(self, deal: Dict) -> bool:
        """
        Send instant alert for exceptional deals (≥15% discount)
        
        Args:
            deal: Dictionary containing deal information
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Email notifications disabled")
            return False
        
        # Check if already sent alert for this deal
        if self._alert_already_sent(deal['item_id'], 'fire_alarm'):
            logger.info(f"Fire alarm already sent for {deal['item_id']}")
            return False
        
        try:
            discount = deal.get('metrics', {}).get('discount_percent', 0)
            
            subject = f"🚨 [EXCEPTIONAL DEAL] - {deal['title'][:50]}... at {discount:.1f}% Off!"
            
            html_body = self._create_fire_alarm_html(deal)
            
            success = self._send_email(subject, html_body)
            
            if success:
                self._record_alert(deal['item_id'], 'fire_alarm')
                logger.info(f"Fire alarm sent for {deal['title'][:50]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending fire alarm: {e}")
            return False
    
    def send_digest_email(self, deals: List[Dict]) -> bool:
        """
        Send scheduled digest email with all qualifying deals
        
        Args:
            deals: List of deal dictionaries
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Email notifications disabled")
            return False
        
        if not deals:
            logger.info("No deals to send in digest")
            return False
        
        try:
            subject = f"📊 Silver Scanner Digest: {len(deals)} New Deals Found"
            
            html_body = self._create_digest_html(deals)
            
            success = self._send_email(subject, html_body)
            
            if success:
                # Record digest sent for all deals
                for deal in deals:
                    self._record_alert(deal['item_id'], 'digest')
                logger.info(f"Digest sent with {len(deals)} deals")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending digest: {e}")
            return False
    
    def _send_email(self, subject: str, html_body: str) -> bool:
        """
        Send email via SMTP
        
        Args:
            subject: Email subject line
            html_body: HTML content of email
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = Config.EMAIL_FROM or Config.SMTP_USERNAME
            msg['To'] = Config.EMAIL_TO
            msg['Subject'] = subject
            
            # Attach HTML body
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _create_fire_alarm_html(self, deal: Dict) -> str:
        """Create HTML template for fire alarm alert"""
        
        metrics = deal.get('metrics', {})
        asw_info = deal.get('asw_info', {})
        
        discount = metrics.get('discount_percent', 0)
        cost_per_oz = metrics.get('cost_per_oz', 0)
        spot_price = metrics.get('spot_price', 0)
        savings_per_oz = metrics.get('savings_per_oz', 0)
        
        silver_weight = asw_info.get('asw', 0)
        coin_name = asw_info.get('coin_name', 'Unknown')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .alert-badge {{
                    background: #ff4444;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 20px;
                    display: inline-block;
                    margin-top: 10px;
                    font-weight: bold;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .deal-card {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin: 20px 0;
                }}
                .deal-title {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #2c3e50;
                    margin-bottom: 15px;
                }}
                .deal-stats {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                    margin: 20px 0;
                }}
                .stat {{
                    padding: 10px;
                    background: #f0f0f0;
                    border-radius: 5px;
                }}
                .stat-label {{
                    font-size: 12px;
                    color: #666;
                    text-transform: uppercase;
                }}
                .stat-value {{
                    font-size: 20px;
                    font-weight: bold;
                    color: #2c3e50;
                    margin-top: 5px;
                }}
                .discount-highlight {{
                    background: #ff4444;
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                    font-size: 24px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .cta-button {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .cta-button:hover {{
                    background: #5568d3;
                }}
                .footer {{
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚨 EXCEPTIONAL DEAL ALERT!</h1>
                <div class="alert-badge">FIRE ALARM - ACT FAST!</div>
            </div>
            
            <div class="content">
                <div class="deal-card">
                    <div class="deal-title">{deal['title']}</div>
                    
                    <div class="discount-highlight">
                        {discount:.1f}% OFF SPOT PRICE!
                    </div>
                    
                    <div class="deal-stats">
                        <div class="stat">
                            <div class="stat-label">Total Price</div>
                            <div class="stat-value">${deal['total_cost']:.2f}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Cost Per Oz</div>
                            <div class="stat-value">${cost_per_oz:.2f}/oz</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Silver Weight</div>
                            <div class="stat-value">{silver_weight:.3f} oz</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Spot Price</div>
                            <div class="stat-value">${spot_price:.2f}/oz</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Savings Per Oz</div>
                            <div class="stat-value">${savings_per_oz:.2f}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Coin Type</div>
                            <div class="stat-value" style="font-size: 14px;">{coin_name}</div>
                        </div>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{deal['item_url']}" class="cta-button">
                            🛒 VIEW ON EBAY NOW
                        </a>
                    </div>
                    
                    <div style="margin-top: 20px; padding: 15px; background: #fff3cd; border-radius: 5px;">
                        <strong>⚡ Why This is Exceptional:</strong><br>
                        This deal is {discount:.1f}% below spot price, which is extremely rare. 
                        Deals this good typically sell within minutes. Act fast!
                    </div>
                </div>
                
                <div class="footer">
                    <p>This alert was sent because a deal met your exceptional criteria (≥15% discount).</p>
                    <p>SuperNinja Silver Scanner © 2024</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_digest_html(self, deals: List[Dict]) -> str:
        """Create HTML template for digest email"""
        
        # Calculate summary stats
        total_deals = len(deals)
        avg_discount = sum(d.get('metrics', {}).get('discount_percent', 0) for d in deals) / total_deals
        best_discount = max(d.get('metrics', {}).get('discount_percent', 0) for d in deals)
        
        # Generate deal rows
        deal_rows = ""
        for deal in deals:
            metrics = deal.get('metrics', {})
            asw_info = deal.get('asw_info', {})
            
            discount = metrics.get('discount_percent', 0)
            cost_per_oz = metrics.get('cost_per_oz', 0)
            silver_weight = asw_info.get('asw', 0)
            coin_name = asw_info.get('coin_name', 'Unknown')
            
            deal_rows += f"""
            <tr>
                <td style="padding: 15px; border-bottom: 1px solid #ddd;">
                    <div style="font-weight: bold; color: #2c3e50; margin-bottom: 5px;">
                        {deal['title'][:80]}...
                    </div>
                    <div style="font-size: 12px; color: #666;">
                        {coin_name} • {silver_weight:.3f} oz ASW
                    </div>
                </td>
                <td style="padding: 15px; border-bottom: 1px solid #ddd; text-align: center;">
                    <div style="font-size: 18px; font-weight: bold; color: #2c3e50;">
                        ${cost_per_oz:.2f}/oz
                    </div>
                    <div style="font-size: 12px; color: #666;">
                        ${deal['total_cost']:.2f} total
                    </div>
                </td>
                <td style="padding: 15px; border-bottom: 1px solid #ddd; text-align: center;">
                    <span style="background: #28a745; color: white; padding: 5px 10px; border-radius: 15px; font-weight: bold;">
                        {discount:.1f}% off
                    </span>
                </td>
                <td style="padding: 15px; border-bottom: 1px solid #ddd; text-align: center;">
                    <a href="{deal['item_url']}" style="background: #667eea; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; font-size: 12px;">
                        View
                    </a>
                </td>
            </tr>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                .summary {{
                    background: #f9f9f9;
                    padding: 20px;
                    display: grid;
                    grid-template-columns: 1fr 1fr 1fr;
                    gap: 15px;
                }}
                .summary-stat {{
                    text-align: center;
                    padding: 15px;
                    background: white;
                    border-radius: 8px;
                }}
                .summary-label {{
                    font-size: 12px;
                    color: #666;
                    text-transform: uppercase;
                }}
                .summary-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #2c3e50;
                    margin-top: 5px;
                }}
                .content {{
                    background: white;
                    padding: 30px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                    margin-top: 30px;
                    padding: 20px;
                    background: #f9f9f9;
                    border-radius: 0 0 10px 10px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Silver Scanner Digest</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">
                    {datetime.now().strftime('%B %d, %Y at %I:%M %p CST')}
                </p>
            </div>
            
            <div class="summary">
                <div class="summary-stat">
                    <div class="summary-label">Total Deals</div>
                    <div class="summary-value">{total_deals}</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-label">Avg Discount</div>
                    <div class="summary-value">{avg_discount:.1f}%</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-label">Best Discount</div>
                    <div class="summary-value">{best_discount:.1f}%</div>
                </div>
            </div>
            
            <div class="content">
                <h2 style="color: #2c3e50; margin-bottom: 20px;">Deals Found</h2>
                
                <table>
                    <thead>
                        <tr style="background: #f0f0f0;">
                            <th style="padding: 12px; text-align: left;">Item</th>
                            <th style="padding: 12px; text-align: center;">Price</th>
                            <th style="padding: 12px; text-align: center;">Discount</th>
                            <th style="padding: 12px; text-align: center;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {deal_rows}
                    </tbody>
                </table>
            </div>
            
            <div class="footer">
                <p>This digest includes all deals that met your threshold but were not sent as instant alerts.</p>
                <p>You receive this digest twice daily at 12:00 PM and 8:00 PM CST.</p>
                <p>SuperNinja Silver Scanner © 2024</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _alert_already_sent(self, item_id: str, alert_type: str) -> bool:
        """Check if alert was already sent for this item"""
        session = self.db_manager.get_session()
        try:
            # Check if alert sent in last 24 hours
            cutoff = datetime.utcnow() - timedelta(hours=24)
            existing = session.query(AlertHistory).filter(
                AlertHistory.item_id == item_id,
                AlertHistory.alert_type == alert_type,
                AlertHistory.sent_at >= cutoff
            ).first()
            
            return existing is not None
            
        except Exception as e:
            logger.error(f"Error checking alert history: {e}")
            return False
        finally:
            session.close()
    
    def _record_alert(self, item_id: str, alert_type: str) -> bool:
        """Record that an alert was sent"""
        session = self.db_manager.get_session()
        try:
            alert = AlertHistory(
                deal_id=0,  # We don't have deal_id at this point
                item_id=item_id,
                alert_type=alert_type,
                sent_at=datetime.utcnow(),
                status='sent'
            )
            
            session.add(alert)
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error recording alert: {e}")
            return False
        finally:
            session.close()
    
    def get_pending_digest_deals(self) -> List[Dict]:
        """
        Get deals that qualify for digest but haven't been sent yet
        
        Returns:
            List of deal dictionaries
        """
        deals = self.db_manager.get_recent_deals(limit=100)
        
        pending = []
        for deal in deals:
            # Skip if already sent in digest
            if self._alert_already_sent(deal['item_id'], 'digest'):
                continue
            
            # Skip if sent as fire alarm
            if self._alert_already_sent(deal['item_id'], 'fire_alarm'):
                continue
            
            # Check if deal is recent (within last 12 hours)
            if deal.get('qualified_at'):
                qualified_time = datetime.fromisoformat(deal['qualified_at'])
                if datetime.utcnow() - qualified_time > timedelta(hours=12):
                    continue
            
            pending.append(deal)
        
        return pending