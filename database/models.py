"""
Database Models Module
SQLAlchemy models for storing scan results and deal history
"""

from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging
from config import Config

logger = logging.getLogger(__name__)

Base = declarative_base()

class Deal(Base):
    """Model for storing qualified deals"""
    __tablename__ = 'deals'
    
    id = Column(Integer, primary_key=True)
    item_id = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    price = Column(Float, nullable=False)
    shipping_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    
    # Silver content info
    coin_type = Column(String(100))
    coin_name = Column(String(200))
    silver_weight_oz = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)
    face_value = Column(Float, default=0.0)
    
    # Deal metrics
    spot_price = Column(Float, nullable=False)
    cost_per_oz = Column(Float, nullable=False)
    discount_percent = Column(Float, nullable=False)
    savings_per_oz = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    
    # Seller info
    seller_username = Column(String(100))
    seller_feedback = Column(Float)
    
    # Listing info
    condition = Column(String(100))
    item_url = Column(String(500), nullable=False)
    image_url = Column(String(500))
    time_listed = Column(DateTime)  # When the listing was created on eBay
    
    # Metadata
    scan_id = Column(String(50))
    qualified_at = Column(DateTime, default=datetime.utcnow)
    confidence = Column(Float)
    is_valid = Column(Boolean, default=True)
    is_hidden = Column(Boolean, default=False)  # User manually hidden/archived
    hidden_at = Column(DateTime)  # When the deal was hidden
    
    def __repr__(self):
        return f"<Deal {self.title[:50]}... ${self.cost_per_oz:.2f}/oz>"

class ScanHistory(Base):
    """Model for storing scan history"""
    __tablename__ = 'scan_history'
    
    id = Column(Integer, primary_key=True)
    scan_id = Column(String(50), unique=True, nullable=False, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    
    # Scan parameters
    spot_price = Column(Float)
    threshold = Column(Float)
    
    # Results
    total_listings_scanned = Column(Integer, default=0)
    qualified_deals_found = Column(Integer, default=0)
    items_rejected = Column(Integer, default=0)
    
    # Statistics
    best_discount = Column(Float, default=0.0)
    avg_discount = Column(Float, default=0.0)
    total_savings = Column(Float, default=0.0)
    
    # Status
    status = Column(String(20), default='running')  # running, completed, failed
    error_message = Column(Text)
    
    def __repr__(self):
        return f"<ScanHistory {self.scan_id}: {self.qualified_deals_found} deals>"

class SellerBlacklist(Base):
    """Model for storing blacklisted sellers"""
    __tablename__ = 'seller_blacklist'
    
    id = Column(Integer, primary_key=True)
    seller_username = Column(String(100), unique=True, nullable=False, index=True)
    reason = Column(String(500))
    added_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SellerBlacklist {self.seller_username}>"

class AlertHistory(Base):
    """Model for tracking alert notifications"""
    __tablename__ = 'alert_history'
    
    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, nullable=False)
    item_id = Column(String(50), nullable=False)
    alert_type = Column(String(50))  # email, app, sms
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='sent')  # sent, failed
    error_message = Column(Text)
    
    def __repr__(self):
        return f"<AlertHistory {self.item_id} {self.alert_type}>"

class PriceHistory(Base):
    """Model for storing silver spot price history"""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    price = Column(Float, nullable=False)
    source = Column(String(200))  # URL of the source
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PriceHistory ${self.price:.2f} at {self.timestamp}>"


class Settings(Base):
    """Model for storing user settings"""
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(500))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Settings {self.key}={self.value}>"


class DatabaseManager:
    """Manages database operations"""
    
    def __init__(self):
        # Use DATABASE_URL from config (supports both PostgreSQL and SQLite)
        database_url = Config.DATABASE_URL
        
        # For SQLite, create directory if needed
        if database_url.startswith('sqlite:///'):
            db_path = database_url.replace('sqlite:///', '')
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
        
        # Create engine with appropriate settings
        if database_url.startswith('postgresql'):
            # PostgreSQL settings
            self.engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False
            )
        else:
            # SQLite settings
            self.engine = create_engine(database_url)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created/verified successfully")
        
        # Create session factory
        self.Session = sessionmaker(bind=self.engine)
        
    def get_session(self):
        """Get a new database session"""
        return self.Session()
    
    def save_deal(self, deal_data: Dict) -> bool:
        """Save a deal to the database"""
        session = self.get_session()
        try:
            # Check if deal already exists
            existing = session.query(Deal).filter_by(item_id=deal_data['item_id']).first()
            if existing:
                logger.info(f"Deal already exists: {deal_data['item_id']}")
                return False
            
            deal = Deal(
                item_id=deal_data['item_id'],
                title=deal_data['title'],
                price=deal_data['price'],
                shipping_cost=deal_data['shipping_cost'],
                total_cost=deal_data['total_cost'],
                coin_type=deal_data.get('asw_info', {}).get('coin_type'),
                coin_name=deal_data.get('asw_info', {}).get('coin_name'),
                silver_weight_oz=deal_data.get('asw_info', {}).get('asw'),
                quantity=deal_data.get('asw_info', {}).get('quantity', 1),
                face_value=deal_data.get('asw_info', {}).get('face_value', 0.0),
                spot_price=deal_data.get('metrics', {}).get('spot_price'),
                cost_per_oz=deal_data.get('metrics', {}).get('cost_per_oz'),
                discount_percent=deal_data.get('metrics', {}).get('discount_percent'),
                savings_per_oz=deal_data.get('metrics', {}).get('savings_per_oz'),
                threshold=deal_data.get('metrics', {}).get('threshold'),
                seller_username=deal_data.get('seller_username'),
                seller_feedback=deal_data.get('seller_feedback'),
                condition=deal_data.get('condition'),
                item_url=deal_data.get('item_url'),
                image_url=deal_data.get('image_url'),
                scan_id=deal_data.get('scan_id'),
                confidence=deal_data.get('asw_info', {}).get('confidence')
            )
            
            session.add(deal)
            session.commit()
            logger.info(f"Saved deal: {deal.title[:50]}...")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving deal: {e}")
            return False
        finally:
            session.close()
    
    def save_scan_history(self, scan_data: Dict) -> bool:
        """Save scan history to database"""
        session = self.get_session()
        try:
            history = ScanHistory(
                scan_id=scan_data['scan_id'],
                start_time=scan_data.get('start_time', datetime.utcnow()),
                end_time=scan_data.get('end_time'),
                spot_price=scan_data.get('spot_price'),
                threshold=scan_data.get('threshold'),
                total_listings_scanned=scan_data.get('total_listings', 0),
                qualified_deals_found=scan_data.get('total_deals', 0),
                items_rejected=scan_data.get('items_rejected', 0),
                best_discount=scan_data.get('best_discount', 0.0),
                avg_discount=scan_data.get('avg_discount', 0.0),
                total_savings=scan_data.get('total_savings', 0.0),
                status=scan_data.get('status', 'completed')
            )
            
            session.add(history)
            session.commit()
            logger.info(f"Saved scan history: {history.scan_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving scan history: {e}")
            return False
        finally:
            session.close()
    
    def get_recent_deals(self, limit: int = 50) -> list:
        """Get recent deals from database"""
        session = self.get_session()
        try:
            deals = session.query(Deal).filter(
                Deal.is_hidden == False
            ).order_by(
                Deal.qualified_at.desc()
            ).limit(limit).all()
            
            return [self._deal_to_dict(deal) for deal in deals]
            
        except Exception as e:
            logger.error(f"Error getting recent deals: {e}")
            return []
        finally:
            session.close()
    
    def _deal_to_dict(self, deal: Deal) -> Dict:
        """Convert Deal model to dictionary"""
        from datetime import datetime
        import pytz
        
        # Calculate time_since_listed
        time_since_listed = None
        if deal.time_listed:
            try:
                # Use user timezone if configured, otherwise UTC
                user_timezone = Config.USER_TIMEZONE if hasattr(Config, 'USER_TIMEZONE') else 'UTC'
                tz = pytz.timezone(user_timezone)
                
                now = datetime.now(tz)
                listed = deal.time_listed.astimezone(tz) if deal.time_listed.tzinfo else tz.localize(deal.time_listed)
                diff = now - listed
                
                seconds = diff.total_seconds()
                if seconds < 60:
                    time_since_listed = 'Just now'
                elif seconds < 3600:
                    mins = int(seconds // 60)
                    time_since_listed = f'{mins}m ago'
                elif seconds < 86400:
                    hours = int(seconds // 3600)
                    time_since_listed = f'{hours}h ago'
                elif seconds < 604800:
                    days = int(seconds // 86400)
                    time_since_listed = f'{days}d ago'
                else:
                    time_since_listed = 'Unknown'
            except Exception as e:
                logger.debug(f"Error calculating time_since_listed: {e}")
                time_since_listed = 'Unknown'
        else:
            time_since_listed = 'Unknown'
        
        # Parse condition tags from title
        condition_tags = []
        if deal.title:
            title_upper = deal.title.upper()
            # Common condition tags
            tags_to_check = [
                'PCGS', 'NGC', 'ANACS', 'ICG',
                'MS60', 'MS61', 'MS62', 'MS63', 'MS64', 'MS65', 'MS66', 'MS67', 'MS68', 'MS69', 'MS70',
                'BU', 'UNC', 'UNCIRCULATED',
                'MINT STATE', 'PROOF',
                'VF', 'XF', 'AU', 'F', 'G', 'AG',
                'SLAB', 'GRADED', 'CERTIFIED'
            ]
            for tag in tags_to_check:
                if tag in title_upper:
                    condition_tags.append(tag)
        
        return {
            'id': deal.id,
            'item_id': deal.item_id,
            'title': deal.title,
            'price': deal.price,
            'shipping_cost': deal.shipping_cost,
            'total_cost': deal.total_cost,
            'coin_name': deal.coin_name,
            'silver_weight_oz': deal.silver_weight_oz,
            'spot_price': deal.spot_price,
            'cost_per_oz': deal.cost_per_oz,
            'discount_percent': deal.discount_percent,
            'seller_username': deal.seller_username,
            'seller_feedback': deal.seller_feedback,
            'condition': deal.condition,
            'item_url': deal.item_url,
            'image_url': deal.image_url,
            'qualified_at': deal.qualified_at.isoformat() if deal.qualified_at else None,
            'time_listed': deal.time_listed.isoformat() if deal.time_listed else None,
            'time_since_listed': time_since_listed,
            'condition_tags': condition_tags
        }
    
    def is_seller_blacklisted(self, seller_username: str) -> bool:
        """Check if seller is blacklisted"""
        session = self.get_session()
        try:
            blacklisted = session.query(SellerBlacklist).filter_by(
                seller_username=seller_username
            ).first()
            return blacklisted is not None
        except Exception as e:
            logger.error(f"Error checking blacklist: {e}")
            return False
        finally:
            session.close()
    
    def blacklist_seller(self, seller_username: str, reason: str = "") -> bool:
        """Add seller to blacklist"""
        session = self.get_session()
        try:
            existing = session.query(SellerBlacklist).filter_by(
                seller_username=seller_username
            ).first()
            
            if existing:
                return False
            
            blacklist = SellerBlacklist(
                seller_username=seller_username,
                reason=reason
            )
            
            session.add(blacklist)
            session.commit()
            logger.info(f"Blacklisted seller: {seller_username}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error blacklisting seller: {e}")
            return False
        finally:
            session.close()
    
    def save_price_history(self, price: float, source: str = None) -> bool:
        """Save a price history entry (every other scrape)"""
        session = self.get_session()
        try:
            price_history = PriceHistory(
                price=price,
                source=source
            )
            
            session.add(price_history)
            session.commit()
            logger.debug(f"Saved price history: ${price:.2f} from {source}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving price history: {e}")
            return False
        finally:
            session.close()
    
    def get_price_history(self, days: int = 30) -> list:
        """Get price history for the last N days"""
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            price_history = session.query(PriceHistory).filter(
                PriceHistory.timestamp >= cutoff_date
            ).order_by(PriceHistory.timestamp.asc()).all()
            
            return [
                {
                    'timestamp': ph.timestamp.isoformat() if ph.timestamp else None,
                    'price': ph.price,
                    'source': ph.source
                }
                for ph in price_history
            ]
            
        except Exception as e:
            logger.error(f"Error getting price history: {e}")
            return []
        finally:
            session.close()
    
    def cleanup_old_price_history(self, days: int = 30) -> int:
        """Remove price history records older than N days"""
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted = session.query(PriceHistory).filter(
                PriceHistory.timestamp < cutoff_date
            ).delete()
            
            session.commit()
            logger.info(f"Cleaned up {deleted} old price history records")
            return deleted
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up price history: {e}")
            return 0
        finally:
            session.close()
    
    def get_latest_price(self):
        """Get the most recent price record from price_history table"""
        session = self.get_session()
        try:
            latest_price = session.query(PriceHistory).order_by(
                PriceHistory.timestamp.desc()
            ).first()
            
            if latest_price:
                logger.debug(f"Latest price from database: ${latest_price.price}/oz from {latest_price.source}")
            else:
                logger.debug("No price history records found in database")
            
            return latest_price
            
        except Exception as e:
            logger.error(f"Error getting latest price from database: {e}")
            return None
        finally:
            session.close()
    
    def hide_deal(self, item_id: str) -> bool:
        """Hide a deal (archive it from view)"""
        session = self.get_session()
        try:
            deal = session.query(Deal).filter_by(item_id=item_id).first()
            if deal:
                deal.is_hidden = True
                deal.hidden_at = datetime.utcnow()
                session.commit()
                logger.info(f"Deal hidden: {item_id}")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error hiding deal: {e}")
            return False
        finally:
            session.close()
    
    def unhide_deal(self, item_id: str) -> bool:
        """Unhide a deal (restore it to view)"""
        session = self.get_session()
        try:
            deal = session.query(Deal).filter_by(item_id=item_id).first()
            if deal:
                deal.is_hidden = False
                deal.hidden_at = None
                session.commit()
                logger.info(f"Deal unhidden: {item_id}")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error unhiding deal: {e}")
            return False
        finally:
            session.close()
    
    def get_hidden_deals(self, limit: int = 50) -> list:
        """Get hidden/archived deals"""
        session = self.get_session()
        try:
            deals = session.query(Deal).filter(
                Deal.is_hidden == True
            ).order_by(
                Deal.hidden_at.desc()
            ).limit(limit).all()
            
            return [self._deal_to_dict(deal) for deal in deals]
        except Exception as e:
            logger.error(f"Error getting hidden deals: {e}")
            return []
        finally:
            session.close()
    
    def cleanup_expired_deals(self) -> int:
        """Remove deals that are no longer active on eBay (older than 7 days)"""
        session = self.get_session()
        try:
            cutoff = datetime.utcnow() - timedelta(days=7)
            expired_deals = session.query(Deal).filter(
                Deal.qualified_at < cutoff
            ).delete()
            
            session.commit()
            logger.info(f"Cleaned up {expired_deals} expired deals")
            return expired_deals
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up expired deals: {e}")
            return 0
        finally:
            session.close()
    
    def get_last_scan(self):
        """Get the most recent scan record from scan_history table"""
        session = self.get_session()
        try:
            last_scan = session.query(ScanHistory).order_by(
                ScanHistory.start_time.desc()
            ).first()
            
            if last_scan:
                # Calculate duration if end_time is available
                duration = None
                if last_scan.end_time:
                    diff = last_scan.end_time - last_scan.start_time
                    seconds = diff.total_seconds()
                    if seconds < 60:
                        duration = f"{int(seconds)}s"
                    elif seconds < 3600:
                        minutes = int(seconds / 60)
                        seconds = int(seconds % 60)
                        duration = f"{minutes}m {seconds}s"
                    else:
                        hours = int(seconds / 3600)
                        minutes = int((seconds % 3600) / 60)
                        duration = f"{hours}h {minutes}m"
                    
                    # Add duration to the object
                    last_scan.duration = duration
                
                logger.debug(f"Last scan from database: {last_scan.scan_id} at {last_scan.start_time}")
            else:
                logger.debug("No scan history records found in database")
            
            return last_scan
            
        except Exception as e:
            logger.error(f"Error getting last scan from database: {e}")
            return None
        finally:
            session.close()
    
    def save_setting(self, key: str, value: str) -> bool:
        """Save or update a setting in the database"""
        session = self.get_session()
        try:
            setting = session.query(Settings).filter_by(key=key).first()
            
            if setting:
                setting.value = value
                setting.updated_at = datetime.utcnow()
            else:
                setting = Settings(key=key, value=value)
                session.add(setting)
            
            session.commit()
            logger.info(f"Setting saved: {key}={value}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving setting {key}: {e}")
            return False
        finally:
            session.close()
    
    def get_setting(self, key: str, default=None):
        """Get a setting from the database"""
        session = self.get_session()
        try:
            setting = session.query(Settings).filter_by(key=key).first()
            
            if setting:
                return setting.value
            else:
                return default
                
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default
        finally:
            session.close()
    
    def get_all_settings(self) -> dict:
        """Get all settings as a dictionary"""
        session = self.get_session()
        try:
            settings = session.query(Settings).all()
            return {s.key: s.value for s in settings}
            
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
        finally:
            session.close()