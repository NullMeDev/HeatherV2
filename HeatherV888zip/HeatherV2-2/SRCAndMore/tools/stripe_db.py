import os
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Text, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timezone
from typing import List, Dict, Optional

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class StripeSite(Base):
    __tablename__ = 'stripe_sites'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    url = Column(Text)
    pk_key = Column(String(255))
    key_valid = Column(Boolean, default=False)
    status = Column(String(50), default='pending')
    last_scanned = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine)

def normalize_domain(url: str) -> str:
    from urllib.parse import urlparse
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split('/')[0]
    domain = domain.lower().replace('www.', '')
    return domain

def add_stripe_sites_bulk(urls: List[str]) -> Dict:
    session = Session()
    added = 0
    skipped = 0
    errors = 0
    
    try:
        for url in urls:
            try:
                domain = normalize_domain(url)
                if not domain:
                    errors += 1
                    continue
                
                existing = session.query(StripeSite).filter_by(domain=domain).first()
                if existing:
                    skipped += 1
                    continue
                
                site = StripeSite(
                    domain=domain,
                    url=url.strip(),
                    status='pending'
                )
                session.add(site)
                added += 1
                
                if added % 500 == 0:
                    session.commit()
                    
            except Exception:
                errors += 1
                continue
        
        session.commit()
        return {'added': added, 'skipped': skipped, 'errors': errors}
    finally:
        session.close()

def get_stripe_sites_to_scan(limit: int = 100) -> List[Dict]:
    session = Session()
    try:
        sites = session.query(StripeSite).filter_by(status='pending').limit(limit).all()
        return [{'id': s.id, 'domain': s.domain, 'url': s.url} for s in sites]
    finally:
        session.close()

def update_stripe_site(domain: str, pk_key: Optional[str], key_valid: bool, status: str, error_msg: str = None):
    session = Session()
    try:
        site = session.query(StripeSite).filter_by(domain=domain).first()
        if site:
            site.pk_key = pk_key
            site.key_valid = key_valid
            site.status = status
            site.error_message = error_msg
            site.last_scanned = datetime.now(timezone.utc)
            session.commit()
    finally:
        session.close()

def count_stripe_sites() -> Dict:
    session = Session()
    try:
        total = session.query(StripeSite).count()
        ready = session.query(StripeSite).filter_by(status='ready', key_valid=True).count()
        pending = session.query(StripeSite).filter_by(status='pending').count()
        error = session.query(StripeSite).filter(StripeSite.status.in_(['error', 'no_stripe'])).count()
        return {'total': total, 'ready': ready, 'pending': pending, 'error': error}
    finally:
        session.close()

def get_valid_stripe_keys(limit: int = 10) -> List[Dict]:
    session = Session()
    try:
        sites = session.query(StripeSite).filter_by(status='ready', key_valid=True).limit(limit).all()
        return [{'domain': s.domain, 'pk_key': s.pk_key} for s in sites]
    finally:
        session.close()

def get_random_stripe_key() -> Optional[Dict]:
    session = Session()
    try:
        from sqlalchemy.sql.expression import func
        site = session.query(StripeSite).filter_by(status='ready', key_valid=True).order_by(func.random()).first()
        if site:
            return {'domain': site.domain, 'pk_key': site.pk_key}
        return None
    finally:
        session.close()
