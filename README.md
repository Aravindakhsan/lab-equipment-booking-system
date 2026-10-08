# Lab Equipment Booking System

A web-based application built for college students and administrators to manage and book laboratory equipment digitally. 

## Features

### Student Features
- User registration and authentication
- Browse available laboratory equipment
- Real-time search and filter capabilities
- Booking requests with specific dates and times
- Automatic conflict detection for double bookings
- Track booking status and manage past requests

### Administrator Features
- Centralized dashboard with analytics
- Manage equipment inventory (Add, Edit, Delete)
- Approve or reject booking requests
- Process equipment returns and record conditions
- Track all bookings across the system

## Technology Stack
- **Backend:** Python 3, Flask
- **Frontend:** HTML5, CSS3, Bootstrap 5, Vanilla JavaScript
- **Database:** SQLite3

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows:
  ```bash
  venv\Scripts\activate
  ```
- Mac/Linux:
  ```bash
  source venv/bin/activate
  ```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```
*The database (`lab_booking.db`) will be automatically created and populated with sample data upon the first run.*

5. Open the application in your browser:
```text
http://127.0.0.1:5000
```

## Default Admin Credentials
- **Email:** admin@lab.com
- **Password:** admin123
