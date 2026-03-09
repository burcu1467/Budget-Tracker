# 💰 Budget Tracker

A full-stack personal finance web application built with **FastAPI** and **JavaScript** that helps users track expenses, manage savings goals, and gain insights into their spending habits.

---

## ✨ Features

- 🔐 **User Authentication** — Secure login and registration with JWT-based authentication
- 📊 **Spending Visualizations** — Interactive pie charts showing expense distribution by category
- 🧾 **OCR Receipt Scanning** — Automatically extract and log expenses by scanning receipts
- 🔁 **Recurring Transactions** — Set up monthly recurring expenses (e.g. subscriptions)
- 🐷 **Savings Goals (Kumbara)** — Track progress toward savings targets with automatic saving rules
- 📄 **Report Generation** — Export financial summaries as PDF or Excel files
- 🏆 **Gamification** — Earn achievement badges for financial milestones
- 🌐 **Multi-language Support** — Available in Turkish and English
- 📂 **Custom Categories** — Add and manage your own spending categories

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI |
| Server | Uvicorn (ASGI) |
| Frontend | HTML, CSS, JavaScript |
| Auth | JWT (python-jose, passlib) |
| OCR | pytesseract, Pillow |
| Reports | reportlab, openpyxl |
| Config | python-dotenv |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Tesseract OCR installed on your system

### Installation

```bash
# Clone the repository
git clone https://github.com/burcu1467/Budget-Tracker.git
cd Budget-Tracker

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the application
uvicorn main:app --reload
```

Then open your browser and go to `http://localhost:8000`

---

## 📁 Project Structure

```
Budget-Tracker/
├── main.py               # FastAPI app entry point
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── static/               # Frontend files (HTML, CSS, JS)
└── ...
```

---

## 🏆 Badge System

| Badge | Condition |
|-------|-----------|
| 🎯 Hedef Avcısı (Goal Hunter) | Complete a savings goal |
| 💰 Tasarruf Ustası (Savings Master) | Income exceeds expenses |
| 🦉 Gece Kuşu (Night Owl) | Make a transaction between 00:00–05:00 |
| 💸 İlk Harcama (First Expense) | Log your first expense |

---

## 📝 Notes

- This project was developed with AI-assisted coding tools.
- OCR accuracy may vary depending on receipt quality and lighting.

---

## 📬 Contact

**Burcu** — [GitHub](https://github.com/burcu1467)
