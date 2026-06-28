import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection
import bcrypt
from app.config import settings
from app.database import engine, Base
from app.models import User, SenderDomain  # ensures models are loaded into declarative metadata

async def create_vector_extension(conn: AsyncConnection):
    print("Checking and creating pgvector extension...")
    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

async def create_hnsw_indexes(conn: AsyncConnection):
    print("Checking and creating HNSW indices for vector columns...")
    # pgvector HNSW index for lead cosine calculations
    await conn.execute(text(
        "CREATE INDEX IF NOT EXISTS leads_vector_idx ON leads "
        "USING hnsw (vector_profile vector_cosine_ops);"
    ))
    # pgvector HNSW index for log retrieval
    await conn.execute(text(
        "CREATE INDEX IF NOT EXISTS logs_vector_idx ON agent_logs "
        "USING hnsw (vector_log vector_cosine_ops);"
    ))

async def seed_default_admin():
    from app.database import async_session_maker
    from sqlalchemy import select
    
    async with async_session_maker() as session:
        # Check if database user table is already seeded
        result = await session.execute(select(User).where(User.role == "owner"))
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("Seeding default Master Owner account...")
            password = "default_secure_owner_password_change_me_immediately"
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            
            default_admin = User(
                email="owner@uabe.com",
                hashed_password=hashed,
                role="owner",
                is_active=True
            )
            session.add(default_admin)
            await session.commit()
            print("----------------------------------------------------------------------")
            print("Default admin created successfully:")
            print("  Email: owner@uabe.com")
            print(f"  Password: {password}")
            print("----------------------------------------------------------------------")
        else:
            print("Master Owner account already exists. Skipping seed.")

async def seed_default_domains():
    from app.database import async_session_maker
    from sqlalchemy import select
    
    async with async_session_maker() as session:
        result = await session.execute(select(SenderDomain))
        existing_domain = result.scalars().first()
        
        if not existing_domain:
            print("Seeding default Sender Domains...")
            domains = [
                SenderDomain(domain="outreach.uabe.com", from_email="sales@outreach.uabe.com", weight=100, is_active=True),
                SenderDomain(domain="marketing.uabe.com", from_email="info@marketing.uabe.com", weight=100, is_active=True),
            ]
            session.add_all(domains)
            await session.commit()
            print("Seeded 2 default domains successfully.")
        else:
            print("Sender domains already seeded. Skipping.")

async def init_db():
    print("Connecting to database and running migrations...")
    try:
        # Step 1: Run raw SQL operations (extensions) first on connection
        async with engine.begin() as conn:
            await create_vector_extension(conn)
            
        # Step 2: Create all tables defined in metadata
        async with engine.begin() as conn:
            print("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            
        # Step 3: Create HNSW indexes (must occur after tables are built)
        async with engine.begin() as conn:
            await create_hnsw_indexes(conn)
            
        # Step 4: Seed initial admin & sender domains
        await seed_default_admin()
        await seed_default_domains()
        
        print("Database initialization successfully completed.")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize database: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    asyncio.run(init_db())
