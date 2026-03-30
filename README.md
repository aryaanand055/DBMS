# 🍲 FoodShare — Online Food Donation and Distribution System

A full-stack web application built with **Flask** and **MySQL** that connects food donors with NGOs and receivers to reduce food waste and fight hunger.

---

## ✨ Features

| Role | Capabilities |
|------|-------------|
| **Donor** | Register, list surplus food donations, edit/delete pending donations, track status |
| **NGO** | Browse available donations, claim them, update delivery status (pending → in-transit → delivered) |
| **Receiver** | View available donations, submit requests, track delivery progress |
| **Admin** | View all users, activate/block accounts, see donation reports, top donors, feedback |

**Common features:**
- Session-based authentication with hashed passwords (Werkzeug)
- Flash message notifications
- Role-based access control
- Feedback / star-rating system for delivered donations
- `/init-db` seeding route with demo accounts
- Responsive Bootstrap 5 UI with custom CSS

---

## 🛠️ Tech Stack

- **Backend:** Python 3, Flask 3.0, PyMySQL 1.1
- **Frontend:** Bootstrap 5.3, Font Awesome 6.5, Jinja2 templates
- **Database:** MySQL 8+ (schema in `schema.sql`)
- **Security:** Werkzeug `generate_password_hash` / `check_password_hash`

---

## 📁 Project Structure

```
DBMS/
├── app.py                  # Flask application (all routes)
├── schema.sql              # MySQL DDL — creates all 5 tables
├── requirements.txt        # Python dependencies
├── static/
│   └── css/
│       └── style.css       # Custom styles
└── templates/
    ├── base.html           # Shared layout + navbar
    ├── index.html          # Landing page with stats
    ├── feedback.html       # Feedback form + listing
    ├── auth/
    │   ├── login.html
    │   └── register.html
    ├── donor/
    │   ├── dashboard.html
    │   ├── add_donation.html
    │   └── edit_donation.html
    ├── ngo/
    │   ├── dashboard.html
    │   └── my_requests.html
    ├── admin/
    │   ├── dashboard.html
    │   ├── users.html
    │   └── reports.html
    └── receiver/
        └── dashboard.html
```

---

## 🗄️ Database Schema

```
Users ──< Food_Donations ──< Requests ──< Delivery
                   └──────────────────< Feedback
```

| Table | Purpose |
|-------|---------|
| `Users` | Stores all user accounts with role (`donor`, `ngo`, `admin`, `receiver`) |
| `Food_Donations` | Donation listings with status lifecycle |
| `Requests` | NGO/receiver claim requests per donation |
| `Delivery` | Delivery tracking per request |
| `Feedback` | Star ratings + comments on delivered donations |

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.9+
- MySQL 8.0+

### 1. Clone the repo
```bash
git clone <repo-url>
cd DBMS
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up the database
```bash
mysql -u root -p < schema.sql
```

### 4. Configure environment variables (optional)
```bash
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=food_donation_db
export SECRET_KEY=your-secret-key
```

### 5. Run the application
```bash
python app.py
```

Visit **http://localhost:5000** in your browser.

### 6. Seed demo data
Navigate to **http://localhost:5000/init-db** to populate the database with sample users and donations.

---

## 🔑 Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@fooddonation.com | test123 |
| Donor | donor@test.com | test123 |
| NGO | ngo@test.com | test123 |
| Receiver | receiver@test.com | test123 |

---

## 🔗 Key Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Landing page with stats |
| `/register` | GET/POST | User registration |
| `/login` | GET/POST | Login |
| `/logout` | GET | Logout |
| `/dashboard` | GET | Role-based redirect |
| `/donor/dashboard` | GET | Donor's donation list |
| `/donor/add` | GET/POST | Add new donation |
| `/donor/edit/<id>` | GET/POST | Edit donation |
| `/donor/delete/<id>` | POST | Delete pending donation |
| `/ngo/dashboard` | GET | Browse available donations |
| `/ngo/claim/<id>` | POST | Claim a donation |
| `/ngo/requests` | GET | View claimed donations |
| `/ngo/update_delivery/<id>` | POST | Update delivery status |
| `/admin/dashboard` | GET | Admin overview |
| `/admin/users` | GET | Manage all users |
| `/admin/toggle_user/<id>` | POST | Block/activate user |
| `/admin/reports` | GET | Reports + top donors + feedback |
| `/receiver/dashboard` | GET | Browse & request donations |
| `/receiver/request/<id>` | POST | Request a donation |
| `/feedback` | GET/POST | Submit & view feedback |
| `/init-db` | GET | Seed database with demo data |