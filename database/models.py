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
                time_listed=deal_data.get('time_listed'),
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
                start_time=datetime.utcnow(),
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
    
    def get_last_scan(self) -> Dict:
        """Get details of the last completed scan"""
        session = self.get_session()
        try:
            last_scan = session.query(ScanHistory).order_by(
                ScanHistory.start_time.desc()
            ).first()
            
            if not last_scan:
                return None
            
            # Calculate duration
            duration = None
            if last_scan.end_time and last_scan.start_time:
                duration = (last_scan.end_time - last_scan.start_time).total_seconds()
            
            return {
                'scan_id': last_scan.scan_id,
                'start_time': last_scan.start_time.isoformat() if last_scan.start_time else None,
                'end_time': last_scan.end_time.isoformat() if last_scan.end_time else None,
                'duration_seconds': duration,
                'total_listings_scanned': last_scan.total_listings_scanned,
                'qualified_deals_found': last_scan.qualified_deals_found,
                'items_rejected': last_scan.items_rejected,
                'status': last_scan.status
            }
            
        except Exception as e:
            logger.error(f"Error getting last scan: {e}")
            return None
        finally:
            session.close()
    
    def get_recent_deals(self, limit: int = 50) -> list:
        """Get recent deals from database"""
        session = self.get_session()
        try:
            deals = session.query(Deal).order_by(
                Deal.qualified_at.desc()
            ).limit(limit).all()
            
            return [self._deal_to_dict(deal) for deal in deals]
            
        except Exception as e:
            logger.error(f"Error getting recent deals: {e}")
            return []
        finally:
            session.close()
    
    def get_deals_last_24h(self) -> int:
        """Get count of deals from the last 24 hours"""
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(hours=24)
            
            count = session.query(Deal).filter(
                Deal.qualified_at >= cutoff_date
            ).count()
            
            return count
            
        except Exception as e:
            logger.error(f"Error getting deals count for last 24h: {e}")
            return 0
        finally:
            session.close()
    
    def _deal_to_dict(self, deal: Deal) -> Dict:
        """Convert Deal model to dictionary"""
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
            'time_listed': deal.time_listed.isoformat() if deal.time_listed else None,
            'qualified_at': deal.qualified_at.isoformat() if deal.qualified_at else None
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
        """
        Save a price history entry with safety buffer.
        Only saves if price moved > $0.05 OR 1 hour has passed since last entry.
        """
        session = self.get_session()
        try:
            # Get the most recent price history entry
            last_entry = session.query(PriceHistory).order_by(
                PriceHistory.timestamp.desc()
            ).first()
            
            should_save = True
            
            if last_entry:
                # Check time difference
                time_diff = datetime.utcnow() - last_entry.timestamp
                time_diff_hours = time_diff.total_seconds() / 3600
                
                # Check price difference
                price_diff = abs(price - last_entry.price)
                
                # Safety buffer: Only save if price moved > $0.05 OR 1 hour passed
                if time_diff_hours < 1.0 and price_diff <= 0.05:
                    should_save = False
                    logger.debug(
                        f"Skipping price history update: "
                        f"Price change ${price_diff:.2f} <= $0.05 and "
                        f"Time {time_diff_hours:.2f}h < 1h"
                    )
            
            if should_save:
                price_history = PriceHistory(
                    price=price,
                    source=source
                )
                
                session.add(price_history)
                session.commit()
                logger.info(f"Saved price history: ${price:.2f} from {source}")
            
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