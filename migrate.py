"""
APEX — Database Migration Script
Creates all tables. Run once on fresh install.
Usage: python scripts/migrate.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from models.models import Base
from config.settings import settings
from loguru import logger


def run_migrations():
    logger.info(f"Connecting to database: {settings.database_url[:30]}...")
    engine = create_engine(settings.database_url)
    
    logger.info("Creating all tables...")
    Base.metadata.create_all(engine)
    
    tables = list(Base.metadata.tables.keys())
    logger.info(f"✅ Created {len(tables)} tables: {', '.join(tables)}")
    
    # Seed initial AI competitor rows
    from sqlalchemy.orm import Session
    from models.models import AICompetitor
    
    competitors = [
        {"ai_model": "gpt4o",    "display_name": "GPT-4o (OpenAI)"},
        {"ai_model": "claude",   "display_name": "Claude 3.5 (Anthropic)"},
        {"ai_model": "gemini",   "display_name": "Gemini 1.5 Pro (Google)"},
        {"ai_model": "deepseek", "display_name": "DeepSeek-V3"},
        {"ai_model": "grok",     "display_name": "Grok-2 (xAI)"},
        {"ai_model": "qwen",     "display_name": "Qwen-Max (Alibaba)"},
    ]
    
    with Session(engine) as session:
        for comp_data in competitors:
            existing = session.query(AICompetitor).filter_by(ai_model=comp_data["ai_model"]).first()
            if not existing:
                competitor = AICompetitor(**comp_data, virtual_balance=settings.competition.starting_balance)
                session.add(competitor)
        session.commit()
    
    logger.info("✅ Seeded AI competitor records")
    logger.info("🟢 Migrations complete!")


if __name__ == "__main__":
    run_migrations()
