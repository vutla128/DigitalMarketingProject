import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
# The secret key is used to encrypt sessions. Keep it secure!
app.secret_key = 'marketmate_super_secret_key_for_session_management'

# Database Configuration
DATABASE_FILE = 'database.db'

def get_db_connection():
    """
    Establishes a connection to the SQLite database.
    Configures row_factory to return results like dictionaries for easier access in templates.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the database by creating tables if they do not exist.
    Also pre-seeds the tables with dummy data if they are empty.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Create Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL
        )
    ''')

    # 2. Create Campaigns Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            platform TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            budget REAL DEFAULT 0.0,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            leads INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Planned',
            revenue REAL DEFAULT 0.0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # 3. Create Social Posts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS social_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            platform TEXT NOT NULL,
            content TEXT NOT NULL,
            post_date TEXT,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Draft',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # 4. Create Leads Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            source TEXT NOT NULL,
            status TEXT DEFAULT 'New',
            date_added TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()

    # Pre-seed Admin Account
    cursor.execute("SELECT * FROM users WHERE email = 'admin@marketmate.com'")
    admin = cursor.fetchone()
    if not admin:
        # Create default admin user
        # Note: In a real-world app, you should hash passwords using a library like Werkzeug.
        # For beginner simplicity, we store it as plain text.
        cursor.execute(
            "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
            ('admin@marketmate.com', 'admin123', 'Default Admin')
        )
        conn.commit()
        # Retrieve the newly created user's ID
        cursor.execute("SELECT id FROM users WHERE email = 'admin@marketmate.com'")
        admin = cursor.fetchone()

    admin_id = admin['id']

    # Pre-seed Campaign Data
    cursor.execute("SELECT COUNT(*) as count FROM campaigns")
    if cursor.fetchone()['count'] == 0:
        campaigns_seed = [
            ('Instagram Spring Promo', 'Instagram', '2026-03-01', '2026-03-31', 500.0, 15000, 850, 120, 45, 'Completed', 1250.0),
            ('Google Ads Search Launch', 'Google Ads', '2026-04-01', '2026-06-30', 1200.0, 28000, 1600, 240, 95, 'Active', 3500.0),
            ('Facebook Retargeting Ads', 'Facebook', '2026-05-15', '2026-06-15', 300.0, 9500, 620, 85, 30, 'Completed', 850.0),
            ('LinkedIn Professional Outreach', 'LinkedIn', '2026-08-01', '2026-09-30', 800.0, 12000, 280, 40, 12, 'Active', 600.0),
            ('YouTube Video Review Ad', 'YouTube', '2026-09-01', '2026-10-15', 600.0, 40000, 1100, 150, 50, 'Planned', 0.0)
        ]
        cursor.executemany(
            "INSERT INTO campaigns (name, platform, start_date, end_date, budget, impressions, clicks, leads, conversions, status, revenue, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(*c, admin_id) for c in campaigns_seed]
        )
        conn.commit()

    # Pre-seed Social Media Posts
    cursor.execute("SELECT COUNT(*) as count FROM social_posts")
    if cursor.fetchone()['count'] == 0:
        posts_seed = [
            ('Product Launch Teaser', 'Instagram', 'Get ready for our new release coming this Summer! Stay tuned for the reveal. #comingsoon', '2026-08-05', 450, 32, 18, 'Published'),
            ('Top 5 Design Tips', 'LinkedIn', 'We share 5 design tips to double your click-through-rates on social creatives.', '2026-08-10', 120, 15, 25, 'Published'),
            ('Weekend Sale Alert', 'Facebook', 'Get 25% off everything this weekend only! Use code WEEKEND25.', '2026-08-19', 0, 0, 0, 'Scheduled')
        ]
        cursor.executemany(
            "INSERT INTO social_posts (title, platform, content, post_date, likes, comments, shares, status, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(*p, admin_id) for p in posts_seed]
        )
        conn.commit()

    # Pre-seed Leads
    cursor.execute("SELECT COUNT(*) as count FROM leads")
    if cursor.fetchone()['count'] == 0:
        leads_seed = [
            ('Alice Smith', 'alice@gmail.com', '+1 555-0101', 'Instagram', 'Converted', '2026-08-02'),
            ('Bob Miller', 'bob.miller@yahoo.com', '+1 555-0102', 'Facebook', 'Contacted', '2026-08-04'),
            ('Charlie Davis', 'charlie@daviscorp.com', '+1 555-0103', 'Website', 'New', '2026-08-10'),
            ('Diana Ross', 'diana@rossdesign.com', '+1 555-0104', 'Google', 'Lost', '2026-08-11'),
            ('Edward Green', 'edward.green@gmail.com', '+1 555-0105', 'Referral', 'New', '2026-08-15')
        ]
        cursor.executemany(
            "INSERT INTO leads (name, email, phone, source, status, date_added, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(*l, admin_id) for l in leads_seed]
        )
        conn.commit()

    conn.close()

# Initialize the database on application startup
init_db()

# --- HELPER FUNCTIONS ---
def get_campaign_metrics(campaign):
    """
    Computes key performance metrics for a campaign: CTR, Conversion Rate, and ROI.
    Safely prevents DivisionByZero errors.
    """
    # Convert Row object to standard python dictionary
    c_dict = dict(campaign)
    
    # 1. Click Through Rate (CTR) = Clicks / Impressions * 100
    impressions = c_dict.get('impressions', 0) or 0
    clicks = c_dict.get('clicks', 0) or 0
    if impressions > 0:
        c_dict['ctr'] = (clicks / impressions) * 100.0
    else:
        c_dict['ctr'] = 0.0

    # 2. Conversion Rate (CR) = Conversions / Clicks * 100
    conversions = c_dict.get('conversions', 0) or 0
    if clicks > 0:
        c_dict['conv_rate'] = (conversions / clicks) * 100.0
    else:
        c_dict['conv_rate'] = 0.0

    # 3. Return on Investment (ROI) = (Revenue - Budget) / Budget * 100
    budget = c_dict.get('budget', 0.0) or 0.0
    revenue = c_dict.get('revenue', 0.0) or 0.0
    if budget > 0:
        c_dict['roi'] = ((revenue - budget) / budget) * 100.0
    else:
        c_dict['roi'] = 0.0

    return c_dict

# --- CONTROLLER ROUTE ENDPOINTS ---

@app.route('/')
def index():
    """
    Landing / Welcome page. Accessible publicly.
    """
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login screen. Checks email and password directly in the SQLite database.
    Redirection happens to Dashboard on successful match.
    """
    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('login.html')

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and user['password'] == password:
            # Login successful: save user info in session
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            flash('Welcome back to MarketMate!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')

    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    """
    Creates a new user in the SQLite database.
    """
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    if not name or not email or not password:
        flash('Please fill in all registration fields.', 'error')
        return redirect(url_for('login'))

    if len(password) < 6:
        flash('Password must be at least 6 characters long.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, password)
        )
        conn.commit()
        flash('Registration successful! You can now log in.', 'success')
    except sqlite3.IntegrityError:
        flash('An account with that email already exists.', 'error')
    finally:
        conn.close()

    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """
    Destroys the session and logs the user out.
    """
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """
    Main analytics workspace dashboard compiling total sums, progress percentages,
    recent campaigns, social media posts and dynamic arrays for JavaScript charts.
    """
    user_id = session.get('user_id')
    if not user_id:
        flash('Please login to access the dashboard.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()

    # 1. Fetch Aggregated Statistics
    stats = {}
    stats['total_campaigns'] = conn.execute("SELECT COUNT(*) FROM campaigns WHERE user_id = ?", (user_id,)).fetchone()[0]
    stats['active_campaigns'] = conn.execute("SELECT COUNT(*) FROM campaigns WHERE user_id = ? AND status = 'Active'", (user_id,)).fetchone()[0]
    stats['total_leads'] = conn.execute("SELECT COUNT(*) FROM leads WHERE user_id = ?", (user_id,)).fetchone()[0]
    stats['total_posts'] = conn.execute("SELECT COUNT(*) FROM social_posts WHERE user_id = ?", (user_id,)).fetchone()[0]
    
    total_budget_row = conn.execute("SELECT SUM(budget) FROM campaigns WHERE user_id = ?", (user_id,)).fetchone()
    stats['total_budget'] = total_budget_row[0] if total_budget_row[0] else 0.0

    total_clicks_row = conn.execute("SELECT SUM(clicks) FROM campaigns WHERE user_id = ?", (user_id,)).fetchone()
    stats['total_clicks'] = total_clicks_row[0] if total_clicks_row[0] else 0

    total_conv_row = conn.execute("SELECT SUM(conversions) FROM campaigns WHERE user_id = ?", (user_id,)).fetchone()
    stats['total_conversions'] = total_conv_row[0] if total_conv_row[0] else 0

    # 2. Fetch Recent Records
    recent_campaigns_rows = conn.execute(
        "SELECT * FROM campaigns WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,)
    ).fetchall()
    recent_campaigns = [get_campaign_metrics(c) for c in recent_campaigns_rows]

    recent_posts = conn.execute(
        "SELECT * FROM social_posts WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,)
    ).fetchall()

    # 3. Chart Data Compilation (Campaign-wise Clicks & Conversions)
    chart_campaigns = conn.execute(
        "SELECT name, clicks, conversions FROM campaigns WHERE user_id = ? LIMIT 6", (user_id,)
    ).fetchall()
    
    chart_data = {
        'campaign_names': [row['name'] for row in chart_campaigns],
        'campaign_clicks': [row['clicks'] for row in chart_campaigns],
        'campaign_conversions': [row['conversions'] for row in chart_campaigns],
        'leads_labels': [],
        'leads_counts': []
    }

    # Leads breakdown grouped by Status (e.g. New, Contacted, Converted, Lost)
    leads_status_rows = conn.execute(
        "SELECT status, COUNT(*) as count FROM leads WHERE user_id = ? GROUP BY status", (user_id,)
    ).fetchall()
    for row in leads_status_rows:
        chart_data['leads_labels'].append(row['status'])
        chart_data['leads_counts'].append(row['count'])

    conn.close()
    return render_template(
        'dashboard.html',
        stats=stats,
        recent_campaigns=recent_campaigns,
        recent_posts=recent_posts,
        chart_data=chart_data,
        active_page='dashboard'
    )

# --- CAMPAIGNS CRUD ROUTES ---

@app.route('/campaigns')
def campaigns():
    """
    Lists all campaigns with calculated metrics (CTR, CR, ROI).
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    campaigns_rows = conn.execute(
        "SELECT * FROM campaigns WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()

    # Calculate metrics on the fly for each campaign Row
    campaigns_list = [get_campaign_metrics(c) for c in campaigns_rows]

    return render_template('campaigns.html', campaigns=campaigns_list, active_page='campaigns')

@app.route('/campaigns/add', methods=['GET', 'POST'])
def add_campaign():
    """
    Creates a new campaign.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        platform = request.form.get('platform', '')
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        budget = float(request.form.get('budget', 0.0) or 0.0)
        revenue = float(request.form.get('revenue', 0.0) or 0.0)
        impressions = int(request.form.get('impressions', 0) or 0)
        clicks = int(request.form.get('clicks', 0) or 0)
        leads = int(request.form.get('leads', 0) or 0)
        conversions = int(request.form.get('conversions', 0) or 0)
        status = request.form.get('status', 'Planned')

        if not name or not platform:
            flash('Campaign Name and Platform are required fields.', 'error')
            return render_template('campaign_form.html', campaign=None)

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO campaigns (name, platform, start_date, end_date, budget, revenue, impressions, clicks, leads, conversions, status, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, platform, start_date, end_date, budget, revenue, impressions, clicks, leads, conversions, status, user_id))
        conn.commit()
        conn.close()

        flash('Campaign created successfully!', 'success')
        return redirect(url_for('campaigns'))

    return render_template('campaign_form.html', campaign=None, active_page='campaigns')

@app.route('/campaigns/edit/<int:id>', methods=['GET', 'POST'])
def edit_campaign(id):
    """
    Edits campaign metrics and info.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    campaign = conn.execute(
        "SELECT * FROM campaigns WHERE id = ? AND user_id = ?", (id, user_id)
    ).fetchone()

    if not campaign:
        conn.close()
        flash('Campaign not found.', 'error')
        return redirect(url_for('campaigns'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        platform = request.form.get('platform', '')
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        budget = float(request.form.get('budget', 0.0) or 0.0)
        revenue = float(request.form.get('revenue', 0.0) or 0.0)
        impressions = int(request.form.get('impressions', 0) or 0)
        clicks = int(request.form.get('clicks', 0) or 0)
        leads = int(request.form.get('leads', 0) or 0)
        conversions = int(request.form.get('conversions', 0) or 0)
        status = request.form.get('status', 'Planned')

        if not name or not platform:
            flash('Campaign Name and Platform are required fields.', 'error')
            return render_template('campaign_form.html', campaign=campaign)

        conn.execute('''
            UPDATE campaigns 
            SET name = ?, platform = ?, start_date = ?, end_date = ?, budget = ?, revenue = ?, impressions = ?, clicks = ?, leads = ?, conversions = ?, status = ?
            WHERE id = ? AND user_id = ?
        ''', (name, platform, start_date, end_date, budget, revenue, impressions, clicks, leads, conversions, status, id, user_id))
        conn.commit()
        conn.close()

        flash('Campaign updated successfully!', 'success')
        return redirect(url_for('campaigns'))

    conn.close()
    return render_template('campaign_form.html', campaign=campaign, active_page='campaigns')

@app.route('/campaigns/delete/<int:id>', methods=['POST'])
def delete_campaign(id):
    """
    Deletes campaign record from database.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM campaigns WHERE id = ? AND user_id = ?", (id, user_id))
    conn.commit()
    conn.close()

    flash('Campaign deleted.', 'success')
    return redirect(url_for('campaigns'))


# --- SOCIAL MEDIA POSTS CRUD ROUTES ---

@app.route('/social-posts')
def social_posts():
    """
    Displays scheduled and published organic social updates.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    posts = conn.execute(
        "SELECT * FROM social_posts WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()

    return render_template('social_posts.html', posts=posts, active_page='social_posts')

@app.route('/social-posts/add', methods=['GET', 'POST'])
def add_social_post():
    """
    Adds a new social media update log.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        platform = request.form.get('platform', '')
        content = request.form.get('content', '').strip()
        post_date = request.form.get('post_date', '')
        likes = int(request.form.get('likes', 0) or 0)
        comments = int(request.form.get('comments', 0) or 0)
        shares = int(request.form.get('shares', 0) or 0)
        status = request.form.get('status', 'Draft')

        if not title or not platform or not content:
            flash('Title, Platform, and Content are required fields.', 'error')
            return render_template('social_post_form.html', post=None)

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO social_posts (title, platform, content, post_date, likes, comments, shares, status, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, platform, content, post_date, likes, comments, shares, status, user_id))
        conn.commit()
        conn.close()

        flash('Social media post logged successfully!', 'success')
        return redirect(url_for('social_posts'))

    return render_template('social_post_form.html', post=None, active_page='social_posts')

@app.route('/social-posts/edit/<int:id>', methods=['GET', 'POST'])
def edit_social_post(id):
    """
    Updates post text content or engagement status counts.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    post = conn.execute(
        "SELECT * FROM social_posts WHERE id = ? AND user_id = ?", (id, user_id)
    ).fetchone()

    if not post:
        conn.close()
        flash('Post not found.', 'error')
        return redirect(url_for('social_posts'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        platform = request.form.get('platform', '')
        content = request.form.get('content', '').strip()
        post_date = request.form.get('post_date', '')
        likes = int(request.form.get('likes', 0) or 0)
        comments = int(request.form.get('comments', 0) or 0)
        shares = int(request.form.get('shares', 0) or 0)
        status = request.form.get('status', 'Draft')

        if not title or not platform or not content:
            flash('Title, Platform, and Content are required.', 'error')
            return render_template('social_post_form.html', post=post)

        conn.execute('''
            UPDATE social_posts
            SET title = ?, platform = ?, content = ?, post_date = ?, likes = ?, comments = ?, shares = ?, status = ?
            WHERE id = ? AND user_id = ?
        ''', (title, platform, content, post_date, likes, comments, shares, status, id, user_id))
        conn.commit()
        conn.close()

        flash('Post updated successfully!', 'success')
        return redirect(url_for('social_posts'))

    conn.close()
    return render_template('social_post_form.html', post=post, active_page='social_posts')

@app.route('/social-posts/delete/<int:id>', methods=['POST'])
def delete_social_post(id):
    """
    Deletes social post item.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM social_posts WHERE id = ? AND user_id = ?", (id, user_id))
    conn.commit()
    conn.close()

    flash('Post deleted.', 'success')
    return redirect(url_for('social_posts'))


# --- LEADS CRUD ROUTES ---

@app.route('/leads')
def leads():
    """
    Displays the leads table.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    leads = conn.execute(
        "SELECT * FROM leads WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()

    return render_template('leads.html', leads=leads, active_page='leads')

@app.route('/leads/add', methods=['GET', 'POST'])
def add_lead():
    """
    Adds a new user lead.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        source = request.form.get('source', '')
        status = request.form.get('status', 'New')
        date_added = request.form.get('date_added', '')

        if not name or not email or not source:
            flash('Name, Email, and Acquisition Source are required fields.', 'error')
            return render_template('lead_form.html', lead=None, today_date=datetime.today().strftime('%Y-%m-%d'))

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO leads (name, email, phone, source, status, date_added, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, phone, source, status, date_added, user_id))
        conn.commit()
        conn.close()

        flash('Lead registered successfully!', 'success')
        return redirect(url_for('leads'))

    today_date = datetime.today().strftime('%Y-%m-%d')
    return render_template('lead_form.html', lead=None, today_date=today_date, active_page='leads')

@app.route('/leads/edit/<int:id>', methods=['GET', 'POST'])
def edit_lead(id):
    """
    Modifies status, telephone, source details for captured contact.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    lead = conn.execute(
        "SELECT * FROM leads WHERE id = ? AND user_id = ?", (id, user_id)
    ).fetchone()

    if not lead:
        conn.close()
        flash('Lead not found.', 'error')
        return redirect(url_for('leads'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        source = request.form.get('source', '')
        status = request.form.get('status', 'New')
        date_added = request.form.get('date_added', '')

        if not name or not email or not source:
            flash('Name, Email, and Acquisition Source are required.', 'error')
            return render_template('lead_form.html', lead=lead)

        conn.execute('''
            UPDATE leads
            SET name = ?, email = ?, phone = ?, source = ?, status = ?, date_added = ?
            WHERE id = ? AND user_id = ?
        ''', (name, email, phone, source, status, date_added, id, user_id))
        conn.commit()
        conn.close()

        flash('Lead updated successfully!', 'success')
        return redirect(url_for('leads'))

    conn.close()
    return render_template('lead_form.html', lead=lead, active_page='leads')

@app.route('/leads/delete/<int:id>', methods=['POST'])
def delete_lead(id):
    """
    Deletes lead info.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM leads WHERE id = ? AND user_id = ?", (id, user_id))
    conn.commit()
    conn.close()

    flash('Lead deleted.', 'success')
    return redirect(url_for('leads'))


# --- DETAILED ANALYTICS ROUTE ---

@app.route('/analytics')
def analytics():
    """
    Compiles average metrics calculations across campaigns and structures groupings
    by marketing source and posts for 4 visual graphs.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # 1. Basic Averages Calculations
    campaigns = conn.execute("SELECT * FROM campaigns WHERE user_id = ?", (user_id,)).fetchall()
    
    total_budget = 0.0
    total_revenue = 0.0
    total_clicks = 0
    total_impressions = 0
    total_conversions = 0

    campaign_names = []
    campaign_clicks = []
    campaign_conversions = []

    for c in campaigns:
        total_budget += c['budget'] or 0.0
        total_revenue += c['revenue'] or 0.0
        total_clicks += c['clicks'] or 0
        total_impressions += c['impressions'] or 0
        total_conversions += c['conversions'] or 0

        # Compile values for Campaign charts
        campaign_names.append(c['name'])
        campaign_clicks.append(c['clicks'] or 0)
        campaign_conversions.append(c['conversions'] or 0)

    # Click-Through Rate Average
    avg_ctr = (total_clicks / total_impressions * 100.0) if total_impressions > 0 else 0.0
    # Conversion Rate Average
    avg_conv_rate = (total_conversions / total_clicks * 100.0) if total_clicks > 0 else 0.0
    # Average Return on Investment
    avg_roi = ((total_revenue - total_budget) / total_budget * 100.0) if total_budget > 0 else 0.0

    analytics_stats = {
        'avg_ctr': avg_ctr,
        'avg_conv_rate': avg_conv_rate,
        'avg_roi': avg_roi,
        'total_budget': total_budget
    }

    # 2. Leads by Acquisition Source Breakdown
    source_labels = []
    source_counts = []
    source_rows = conn.execute(
        "SELECT source, COUNT(*) as count FROM leads WHERE user_id = ? GROUP BY source", (user_id,)
    ).fetchall()
    for row in source_rows:
        source_labels.append(row['source'])
        source_counts.append(row['count'])

    # 3. Social Media Organic Engagement Breakdown (Likes & Comments per Post)
    posts = conn.execute(
        "SELECT title, likes, comments FROM social_posts WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,)
    ).fetchall()
    
    post_titles = [row['title'] for row in posts]
    post_likes = [row['likes'] for row in posts]
    post_comments = [row['comments'] for row in posts]

    chart_data = {
        'campaign_names': campaign_names,
        'campaign_clicks': campaign_clicks,
        'campaign_conversions': campaign_conversions,
        'source_labels': source_labels,
        'source_counts': source_counts,
        'post_titles': post_titles,
        'post_likes': post_likes,
        'post_comments': post_comments
    }

    conn.close()

    return render_template(
        'analytics.html',
        analytics=analytics_stats,
        data=chart_data,
        active_page='analytics'
    )


# Start Flask Server
if __name__ == '__main__':
    # Running in debug mode allows automatic reloading of code modifications
    app.run(debug=True, port=5000)
