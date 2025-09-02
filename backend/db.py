import sqlite3
from datetime import datetime
from .config import DB_PATH

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _conn()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS policies(
      topic TEXT PRIMARY KEY,
      section TEXT NOT NULL,
      classification TEXT NOT NULL, -- public|internal|restricted
      text TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS customers(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      full_name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      last4 TEXT,
      order_id TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS customer_policies(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_email TEXT NOT NULL,
      policy_number TEXT NOT NULL UNIQUE,
      first_name TEXT NOT NULL,
      last_name TEXT NOT NULL,
      premium REAL NOT NULL,
      coverage_type TEXT NOT NULL,
      next_due_date TEXT NOT NULL,
      payment_method TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'active', -- active|inactive
      created_at TEXT NOT NULL,
      FOREIGN KEY (customer_email) REFERENCES customers(email)
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS audits(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      actor TEXT NOT NULL,
      event TEXT NOT NULL,
      detail TEXT
    )""")
    conn.commit()
    conn.close()

def seed_many(policies, customers):
    conn = _conn()
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    for p in policies:
        c.execute("""
        INSERT INTO policies(topic, section, classification, text, updated_at)
        VALUES(?,?,?,?,?)
        ON CONFLICT(topic) DO UPDATE SET
          section=excluded.section,
          classification=excluded.classification,
          text=excluded.text,
          updated_at=excluded.updated_at
        """, (p["topic"].strip().lower(), p["section"], p["classification"], p["text"], now))
    for u in customers:
        c.execute("""
        INSERT INTO customers(full_name, email, last4, order_id)
        VALUES(?,?,?,?)
        ON CONFLICT(email) DO UPDATE SET
          full_name=excluded.full_name,
          last4=excluded.last4,
          order_id=excluded.order_id
        """, (u["full_name"], u["email"].lower(), u.get("last4"), u.get("order_id")))
    conn.commit()
    conn.close()

def get_policy(topic: str):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT * FROM policies WHERE topic = ?", (topic.strip().lower(),))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def search_policies(query: str):
    """Search policies by topic with fuzzy matching"""
    conn = _conn()
    c = conn.cursor()
    search_term = f"%{query.strip().lower()}%"
    c.execute("""
        SELECT topic, section, classification, updated_at 
        FROM policies 
        WHERE topic LIKE ? OR section LIKE ? OR text LIKE ?
        ORDER BY topic
    """, (search_term, search_term, search_term))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def list_policies():
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT topic, section, classification, updated_at FROM policies ORDER BY topic")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def verify_customer(email: str, full_name: str = "", last4: str = "", order_id: str = ""):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT * FROM customers WHERE email = ?", (email.lower(),))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    ok_name = (not full_name) or (full_name.strip().lower() == row["full_name"].lower())
    ok_last4 = (not last4) or (last4 == (row["last4"] or ""))
    ok_order = (not order_id) or (order_id == (row["order_id"] or ""))
    return bool(ok_name and ok_last4 and ok_order)

def log(actor: str, event: str, detail: str = ""):
    conn = _conn()
    c = conn.cursor()
    c.execute("INSERT INTO audits(ts, actor, event, detail) VALUES(?,?,?,?)",
              (datetime.utcnow().isoformat(), actor, event, detail))
    conn.commit()
    conn.close()

def list_audits(limit=200):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT * FROM audits ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

# ===== Customer Policy Management =====
def get_customer_policies(email: str):
    """Get all policies for a customer"""
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM customer_policies 
        WHERE customer_email = ? 
        ORDER BY created_at DESC
    """, (email.lower(),))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_policy_by_number(policy_number: str):
    """Get policy details by policy number"""
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT * FROM customer_policies WHERE policy_number = ?", (policy_number,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def add_customer_policy(customer_email: str, policy_number: str, first_name: str, 
                       last_name: str, premium: float, coverage_type: str, 
                       next_due_date: str, payment_method: str, status: str = "active"):
    """Add a new customer policy"""
    conn = _conn()
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("""
        INSERT INTO customer_policies(
            customer_email, policy_number, first_name, last_name, 
            premium, coverage_type, next_due_date, payment_method, 
            status, created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (customer_email.lower(), policy_number, first_name, last_name, 
          premium, coverage_type, next_due_date, payment_method, status, now))
    conn.commit()
    conn.close()

def update_policy_status(policy_number: str, status: str):
    """Update policy status (active/inactive)"""
    conn = _conn()
    c = conn.cursor()
    c.execute("UPDATE customer_policies SET status = ? WHERE policy_number = ?", 
              (status, policy_number))
    conn.commit()
    conn.close()

def seed_customer_policies():
    """Seed realistic P&C insurance policies"""
    sample_policies = [
        # Auto Insurance Policies
        {
            "customer_email": "maria92@example.com",
            "policy_number": "AUTO-2024-847291",
            "first_name": "Heather",
            "last_name": "Gray",
            "premium": 1847.50,
            "coverage_type": "Personal Auto - Full Coverage",
            "next_due_date": "2024-03-15",
            "payment_method": "Auto-Pay Credit Card (*3330)",
            "status": "active"
        },
        {
            "customer_email": "benjamin77@example.org",
            "policy_number": "HOME-2024-293847",
            "first_name": "Judy",
            "last_name": "Griffin",
            "premium": 2340.00,
            "coverage_type": "Homeowners HO-3 Policy",
            "next_due_date": "2024-04-19",
            "payment_method": "Bank Draft",
            "status": "active"
        },
        {
            "customer_email": "martinheather@example.org",
            "policy_number": "AUTO-2024-572813",
            "first_name": "Patrick",
            "last_name": "Jimenez",
            "premium": 1654.25,
            "coverage_type": "Commercial Auto Policy",
            "next_due_date": "2024-06-25",
            "payment_method": "Check Payment",
            "status": "active"
        },
        {
            "customer_email": "qcervantes@example.com",
            "policy_number": "PROP-2024-847392",
            "first_name": "Jason",
            "last_name": "Harrington",
            "premium": 3250.00,
            "coverage_type": "Commercial Property Insurance",
            "next_due_date": "2024-08-10",
            "payment_method": "Wire Transfer",
            "status": "active"
        },
        {
            "customer_email": "andrewstaylor@example.com",
            "policy_number": "UMB-2024-193847",
            "first_name": "Jordan",
            "last_name": "Graves",
            "premium": 1875.00,
            "coverage_type": "Personal Umbrella Policy",
            "next_due_date": "2024-02-28",
            "payment_method": "Auto-Pay Bank Account",
            "status": "active"
        }
    ]
    
    for policy in sample_policies:
        try:
            add_customer_policy(**policy)
        except Exception as e:
            print(f"Policy {policy['policy_number']} already exists or error: {e}")
            pass

def seed_pc_policies():
    """Seed realistic P&C insurance policy documents"""
    pc_policies = [
        {
            "topic": "auto_coverage_limits",
            "section": "Auto Insurance",
            "classification": "public",
            "text": "Standard auto coverage includes: Bodily Injury Liability (minimum $25,000/$50,000), Property Damage Liability ($25,000), Comprehensive and Collision with deductibles ranging from $250-$1,000. Uninsured/Underinsured Motorist coverage available."
        },
        {
            "topic": "homeowners_coverage",
            "section": "Property Insurance",
            "classification": "public",
            "text": "HO-3 Homeowners policy covers dwelling, other structures, personal property, and liability. Standard coverage includes fire, theft, vandalism, and weather-related damage. Flood and earthquake require separate policies."
        },
        {
            "topic": "claims_process",
            "section": "Claims",
            "classification": "internal",
            "text": "Claims must be reported within 24 hours for auto accidents, 72 hours for property damage. Adjuster assignment within 1 business day. Settlement authority: $10,000 for auto, $25,000 for property without supervisor approval."
        },
        {
            "topic": "premium_calculation",
            "section": "Underwriting",
            "classification": "restricted",
            "text": "Auto premiums based on: driving record (35%), credit score (25%), vehicle type (20%), location (15%), coverage limits (5%). Property premiums consider: property value, location risk, claims history, and construction type."
        },
        {
            "topic": "policy_cancellation",
            "section": "Policy Administration",
            "classification": "internal",
            "text": "Policies may be cancelled for non-payment (10-day notice), fraud (immediate), or increased risk (30-day notice). Refunds calculated pro-rata minus $25 administrative fee. Reinstatement possible within 30 days with payment of past due amounts."
        },
        {
            "topic": "commercial_liability",
            "section": "Commercial Lines",
            "classification": "public",
            "text": "General Liability coverage protects against third-party bodily injury and property damage claims. Standard limits $1M per occurrence, $2M aggregate. Professional Liability and Product Liability available as separate coverages."
        }
    ]
    
    conn = _conn()
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    for policy in pc_policies:
        c.execute("""
        INSERT INTO policies(topic, section, classification, text, updated_at)
        VALUES(?,?,?,?,?)
        ON CONFLICT(topic) DO UPDATE SET
          section=excluded.section,
          classification=excluded.classification,
          text=excluded.text,
          updated_at=excluded.updated_at
        """, (policy["topic"], policy["section"], policy["classification"], policy["text"], now))
    
    conn.commit()
    conn.close()