from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from database import init_db, get_db_connection
import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_lab_key'  # In a real app, use a secure random key
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=30)

# Initialize database
init_db()

# Decorators for access control
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'student':
            flash('Student access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ============================== PUBLIC ROUTES ==============================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        department = request.form.get('department')

        valid_departments = [
            'Information Technology',
            'Computer Science and Engineering',
            'Electronics and Communication Engineering',
            'Electrical and Electronics Engineering',
            'Mechanical Engineering',
            'Civil Engineering',
            'Aeronautical Engineering'
        ]

        if not name or not email or not password or not confirm_password or not department:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        if department not in valid_departments:
            flash('Invalid department selected.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user:
            conn.close()
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        conn.execute('INSERT INTO users (name, email, password, role, department) VALUES (?, ?, ?, ?, ?)',
                     (name, email, hashed_password, 'student', department))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session.permanent = True
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            session['department'] = user['department']
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ============================== STUDENT ROUTES ==============================

@app.route('/student/dashboard')
@student_required
def student_dashboard():
    conn = get_db_connection()
    user_id = session['user_id']
    
    total_bookings = conn.execute('SELECT COUNT(*) FROM bookings WHERE user_id = ?', (user_id,)).fetchone()[0]
    pending = conn.execute('SELECT COUNT(*) FROM bookings WHERE user_id = ? AND status = "Pending"', (user_id,)).fetchone()[0]
    approved = conn.execute('SELECT COUNT(*) FROM bookings WHERE user_id = ? AND status = "Approved"', (user_id,)).fetchone()[0]
    active = conn.execute('SELECT COUNT(*) FROM bookings WHERE user_id = ? AND status = "Active"', (user_id,)).fetchone()[0]
    completed = conn.execute('SELECT COUNT(*) FROM bookings WHERE user_id = ? AND status = "Completed"', (user_id,)).fetchone()[0]
    
    recent_bookings = conn.execute('''
        SELECT b.id, e.name as equipment_name, b.booking_date, b.start_time, b.status 
        FROM bookings b JOIN equipment e ON b.equipment_id = e.id 
        WHERE b.user_id = ? 
        ORDER BY b.created_at DESC LIMIT 5
    ''', (user_id,)).fetchall()
    
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overdue = conn.execute('''
        SELECT COUNT(*) FROM bookings 
        WHERE user_id = ? AND status = "Active" 
        AND (expected_return_date || ' ' || expected_return_time) < ?
    ''', (user_id, now_str)).fetchone()[0]
    
    conn.close()
    
    return render_template('student/dashboard.html', 
                           total=total_bookings, pending=pending, 
                           approved=approved, active=active, 
                           completed=completed, overdue=overdue, recent_bookings=recent_bookings)

@app.route('/student/profile')
@student_required
def student_profile():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('student/profile.html', user=user)

@app.route('/student/equipment')
@student_required
def student_equipment():
    conn = get_db_connection()
    equipment = conn.execute('SELECT * FROM equipment WHERE department = ?', (session['department'],)).fetchall()
    conn.close()
    
    labs = sorted(list(set([eq['lab_name'] for eq in equipment])))
    return render_template('student/equipment.html', equipment=equipment, labs=labs)

@app.route('/student/book/<int:equipment_id>', methods=['GET', 'POST'])
@student_required
def book_equipment(equipment_id):
    conn = get_db_connection()
    equipment = conn.execute('SELECT * FROM equipment WHERE id = ?', (equipment_id,)).fetchone()
    
    if not equipment:
        conn.close()
        flash('Equipment not found.', 'danger')
        return redirect(url_for('student_equipment'))
        
    if equipment['department'] != session.get('department'):
        conn.close()
        flash('You can only book equipment assigned to your department.', 'danger')
        return redirect(url_for('student_equipment'))
        
    if request.method == 'POST':
        booking_date = request.form['booking_date']
        start_time = request.form['start_time']
        expected_return_date = request.form.get('expected_return_date')
        expected_return_time = request.form.get('expected_return_time')
        purpose = request.form['purpose']
        try:
            quantity = int(request.form.get('quantity', 1))
        except ValueError:
            quantity = 1
            
        # Fallbacks for backwards compatibility if needed
        if not expected_return_date:
            expected_return_date = booking_date
        if not expected_return_time:
            # Fallback to end_time if it exists in form
            expected_return_time = request.form.get('end_time', start_time)
            
        # Validation
        if not booking_date or not start_time or not expected_return_date or not expected_return_time or not purpose:
            flash('All fields are required.', 'danger')
            conn.close()
            return redirect(url_for('book_equipment', equipment_id=equipment_id))
            
        # Basic time validation
        req_start = f"{booking_date} {start_time}"
        req_end = f"{expected_return_date} {expected_return_time}"
        
        if req_start >= req_end:
            flash('Start time must be earlier than expected return time.', 'danger')
            conn.close()
            return redirect(url_for('book_equipment', equipment_id=equipment_id))
            
        # Conflict Detection Check
        # Summing the quantity of 'Approved' and 'Active' bookings that overlap
        overlapping_quantity = conn.execute('''
            SELECT COALESCE(SUM(quantity), 0) FROM bookings 
            WHERE equipment_id = ? 
            AND status IN ('Approved', 'Active')
            AND (
                (booking_date || ' ' || start_time < ?) AND 
                (COALESCE(expected_return_date, booking_date) || ' ' || COALESCE(expected_return_time, end_time) > ?)
            )
        ''', (equipment_id, req_end, req_start)).fetchone()[0]
        
        if overlapping_quantity + quantity > equipment['quantity']:
            flash(f'Only {equipment["quantity"] - overlapping_quantity} units are available during the selected time slot. Please choose another time or reduce quantity.', 'danger')
            conn.close()
            return redirect(url_for('book_equipment', equipment_id=equipment_id))
            
        # Insert booking
        conn.execute('''
            INSERT INTO bookings (user_id, equipment_id, booking_date, start_time, end_time, expected_return_date, expected_return_time, purpose, quantity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], equipment_id, booking_date, start_time, expected_return_time, expected_return_date, expected_return_time, purpose, quantity))
        
        conn.commit()
        conn.close()
        
        flash('Booking request submitted successfully.', 'success')
        return redirect(url_for('student_bookings'))
        
    conn.close()
    return render_template('student/book_equipment.html', equipment=equipment)

@app.route('/student/bookings')
@student_required
def student_bookings():
    conn = get_db_connection()
    bookings = conn.execute('''
        SELECT b.*, e.name as equipment_name, e.lab_name
        FROM bookings b JOIN equipment e ON b.equipment_id = e.id
        WHERE b.user_id = ?
        ORDER BY b.created_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('student/my_bookings.html', bookings=bookings)

@app.route('/student/booking/<int:booking_id>/cancel', methods=['POST'])
@student_required
def cancel_booking(booking_id):
    conn = get_db_connection()
    booking = conn.execute('SELECT * FROM bookings WHERE id = ? AND user_id = ?', (booking_id, session['user_id'])).fetchone()
    
    if not booking:
        flash('Booking not found.', 'danger')
    elif booking['status'] not in ['Pending', 'Approved']:
        flash('Only pending or approved bookings can be cancelled.', 'danger')
    else:
        conn.execute('UPDATE bookings SET status = "Cancelled" WHERE id = ?', (booking_id,))
        
        # If it was approved or active, we need to increment available quantity
        if booking['status'] == 'Approved' or booking['status'] == 'Active':
             conn.execute('UPDATE equipment SET available_quantity = available_quantity + ? WHERE id = ?', (booking['quantity'], booking['equipment_id']))
             
        conn.commit()
        flash('Booking cancelled successfully.', 'success')
        
    conn.close()
    return redirect(url_for('student_bookings'))

# ============================== ADMIN ROUTES ==============================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    
    total_equipment = conn.execute('SELECT COUNT(*) FROM equipment').fetchone()[0]
    total_bookings = conn.execute('SELECT COUNT(*) FROM bookings').fetchone()[0]
    pending = conn.execute('SELECT COUNT(*) FROM bookings WHERE status = "Pending"').fetchone()[0]
    approved = conn.execute('SELECT COUNT(*) FROM bookings WHERE status = "Approved"').fetchone()[0]
    active = conn.execute('SELECT COUNT(*) FROM bookings WHERE status = "Active"').fetchone()[0]
    completed = conn.execute('SELECT COUNT(*) FROM bookings WHERE status = "Completed"').fetchone()[0]
    
    recent_requests = conn.execute('''
        SELECT b.id, u.name as user_name, e.name as equipment_name, b.booking_date, b.status 
        FROM bookings b 
        JOIN users u ON b.user_id = u.id
        JOIN equipment e ON b.equipment_id = e.id 
        ORDER BY b.created_at DESC LIMIT 5
    ''').fetchall()
    
    dept_stats = conn.execute('''
        SELECT department, SUM(quantity) as count 
        FROM equipment 
        GROUP BY department
        ORDER BY count DESC
    ''').fetchall()
    
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overdue = conn.execute('''
        SELECT COUNT(*) FROM bookings 
        WHERE status = "Active" 
        AND (expected_return_date || ' ' || expected_return_time) < ?
    ''', (now_str,)).fetchone()[0]
    
    conn.close()
    return render_template('admin/dashboard.html', 
                           total_equipment=total_equipment,
                           total_bookings=total_bookings,
                           pending=pending, approved=approved,
                           active=active, completed=completed, overdue=overdue,
                           recent_requests=recent_requests,
                           dept_stats=dept_stats)

@app.route('/admin/equipment')
@admin_required
def admin_equipment():
    conn = get_db_connection()
    equipment = conn.execute('SELECT * FROM equipment').fetchall()
    conn.close()
    return render_template('admin/equipment.html', equipment=equipment)

@app.route('/admin/equipment/add', methods=['GET', 'POST'])
@admin_required
def add_equipment():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        department = request.form.get('department')
        lab_name = request.form['lab_name']
        quantity = int(request.form['quantity'])
        status = request.form['status']
        
        if not department:
            flash('Department is required.', 'danger')
            return redirect(url_for('add_equipment'))

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO equipment (name, description, department, lab_name, quantity, available_quantity, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, department, lab_name, quantity, quantity, status))
        conn.commit()
        conn.close()
        
        flash('Equipment added successfully.', 'success')
        return redirect(url_for('admin_equipment'))
        
    return render_template('admin/add_equipment.html')

@app.route('/admin/equipment/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_equipment(id):
    conn = get_db_connection()
    equipment = conn.execute('SELECT * FROM equipment WHERE id = ?', (id,)).fetchone()
    
    if not equipment:
        conn.close()
        flash('Equipment not found.', 'danger')
        return redirect(url_for('admin_equipment'))
        
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        department = request.form.get('department')
        lab_name = request.form['lab_name']
        new_quantity = int(request.form['quantity'])
        status = request.form['status']
        
        if not department:
            flash('Department is required.', 'danger')
            return redirect(url_for('edit_equipment', id=id))
            
        # Calculate new available quantity based on difference
        diff = new_quantity - equipment['quantity']
        new_available = equipment['available_quantity'] + diff
        
        if new_available < 0:
             flash('Cannot reduce quantity below currently booked items.', 'danger')
             conn.close()
             return redirect(url_for('edit_equipment', id=id))
             
        conn.execute('''
            UPDATE equipment 
            SET name = ?, description = ?, department = ?, lab_name = ?, quantity = ?, available_quantity = ?, status = ?
            WHERE id = ?
        ''', (name, description, department, lab_name, new_quantity, new_available, status, id))
        conn.commit()
        conn.close()
        
        flash('Equipment updated successfully.', 'success')
        return redirect(url_for('admin_equipment'))
        
    conn.close()
    return render_template('admin/edit_equipment.html', equipment=equipment)

@app.route('/admin/equipment/delete/<int:id>', methods=['POST'])
@admin_required
def delete_equipment(id):
    conn = get_db_connection()
    
    # Check for active bookings
    active_bookings = conn.execute('''
        SELECT COUNT(*) FROM bookings 
        WHERE equipment_id = ? AND status IN ('Pending', 'Approved', 'Active')
    ''', (id,)).fetchone()[0]
    
    if active_bookings > 0:
        flash('Cannot delete equipment with active or pending bookings.', 'danger')
    else:
        conn.execute('DELETE FROM equipment WHERE id = ?', (id,))
        conn.commit()
        flash('Equipment deleted successfully.', 'success')
        
    conn.close()
    return redirect(url_for('admin_equipment'))

@app.route('/admin/equipment/<int:id>/history')
@admin_required
def equipment_history(id):
    conn = get_db_connection()
    equipment = conn.execute('SELECT * FROM equipment WHERE id = ?', (id,)).fetchone()
    
    if not equipment:
        flash('Equipment not found.', 'danger')
        conn.close()
        return redirect(url_for('admin_equipment'))
        
    history = conn.execute('''
        SELECT r.*, b.booking_date, b.start_time, b.expected_return_date, b.expected_return_time, b.quantity, u.name as student_name
        FROM returns r
        JOIN bookings b ON r.booking_id = b.id
        JOIN users u ON b.user_id = u.id
        WHERE b.equipment_id = ?
        ORDER BY r.returned_date DESC, r.returned_time DESC
    ''', (id,)).fetchall()
    
    conn.close()
    return render_template('admin/equipment_history.html', equipment=equipment, history=history)

@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    conn = get_db_connection()
    bookings = conn.execute('''
        SELECT b.*, u.name as student_name, e.name as equipment_name, e.lab_name
        FROM bookings b 
        JOIN users u ON b.user_id = u.id
        JOIN equipment e ON b.equipment_id = e.id
        ORDER BY b.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/admin/booking/<int:id>/approve', methods=['POST'])
@admin_required
def approve_booking(id):
    conn = get_db_connection()
    booking = conn.execute('SELECT * FROM bookings WHERE id = ?', (id,)).fetchone()
    
    if not booking or booking['status'] != 'Pending':
        flash('Invalid booking or booking not pending.', 'danger')
        conn.close()
        return redirect(url_for('admin_bookings'))
        
    # Fetch equipment to get total quantity
    equipment = conn.execute('SELECT * FROM equipment WHERE id = ?', (booking['equipment_id'],)).fetchone()

    # Check conflict again
    overlapping_count = conn.execute('''
        SELECT COUNT(id) FROM bookings 
        WHERE equipment_id = ? AND booking_date = ? 
        AND status IN ('Approved', 'Active')
        AND (
            (start_time < ? AND end_time > ?) OR
            (start_time < ? AND end_time > ?) OR
            (start_time >= ? AND end_time <= ?)
        )
        AND id != ?
    ''', (booking['equipment_id'], booking['booking_date'], booking['end_time'], booking['start_time'], booking['end_time'], booking['start_time'], booking['start_time'], booking['end_time'], id)).fetchone()[0]
    
    if overlapping_count >= equipment['quantity']:
        flash('Conflict detected. All units of this equipment have already been approved for this time slot.', 'danger')
        conn.close()
        return redirect(url_for('admin_bookings'))
        
    # Check available quantity (as a secondary check)
    if equipment['available_quantity'] <= 0:
        flash('No more available units for this equipment overall.', 'danger')
        conn.close()
        return redirect(url_for('admin_bookings'))
        
    # Approve and update quantity
    conn.execute('UPDATE bookings SET status = "Approved" WHERE id = ?', (id,))
    conn.execute('UPDATE equipment SET available_quantity = available_quantity - 1 WHERE id = ?', (booking['equipment_id'],))
    
    # We can also automatically set to Active if the date/time is now, but for simplicity let's stick to status updates by admin or just consider Approved to mean Active. Let's provide a way to mark Active if needed. Or just use Approved -> Returned workflow. Actually, let's keep it simple: Approved blocks availability. Active is when they pick it up. I'll just change status to Approved, availability is reduced.

    conn.commit()
    conn.close()
    
    flash('Booking approved.', 'success')
    return redirect(url_for('admin_bookings'))

@app.route('/admin/booking/<int:id>/reject', methods=['POST'])
@admin_required
def reject_booking(id):
    conn = get_db_connection()
    conn.execute('UPDATE bookings SET status = "Rejected" WHERE id = ? AND status = "Pending"', (id,))
    conn.commit()
    conn.close()
    flash('Booking rejected.', 'info')
    return redirect(url_for('admin_bookings'))

@app.route('/admin/booking/<int:id>/issue', methods=['GET', 'POST'])
@admin_required
def issue_equipment(id):
    conn = get_db_connection()
    booking = conn.execute('''
        SELECT b.*, e.name as equipment_name, u.name as student_name
        FROM bookings b 
        JOIN equipment e ON b.equipment_id = e.id
        JOIN users u ON b.user_id = u.id
        WHERE b.id = ?
    ''', (id,)).fetchone()
    
    if not booking or booking['status'] != 'Approved':
        flash('Invalid booking or booking not approved.', 'danger')
        conn.close()
        return redirect(url_for('admin_bookings'))
        
    if request.method == 'POST':
        issued_date = datetime.datetime.now().strftime("%Y-%m-%d")
        issued_time = datetime.datetime.now().strftime("%H:%M:%S")
        issued_by = session['name']
        issue_condition = request.form['issue_condition']
        issue_remarks = request.form['issue_remarks']
        
        conn.execute('''
            UPDATE bookings 
            SET status = "Active", issued_date = ?, issued_time = ?, issued_by = ?, issue_condition = ?, issue_remarks = ?
            WHERE id = ?
        ''', (issued_date, issued_time, issued_by, issue_condition, issue_remarks, id))
        conn.commit()
        conn.close()
        
        flash('Equipment issued successfully.', 'success')
        return redirect(url_for('admin_bookings'))
        
    conn.close()
    return render_template('admin/issue_equipment.html', booking=booking)

@app.route('/admin/returns')
@admin_required
def admin_returns():
    conn = get_db_connection()
    active_bookings = conn.execute('''
        SELECT b.*, u.name as student_name, e.name as equipment_name, e.lab_name
        FROM bookings b 
        JOIN users u ON b.user_id = u.id
        JOIN equipment e ON b.equipment_id = e.id
        WHERE b.status IN ('Approved', 'Active')
        ORDER BY b.booking_date ASC
    ''').fetchall()
    
    recent_returns = conn.execute('''
        SELECT r.*, b.booking_date, e.name as equipment_name, u.name as student_name
        FROM returns r
        JOIN bookings b ON r.booking_id = b.id
        JOIN equipment e ON b.equipment_id = e.id
        JOIN users u ON b.user_id = u.id
        ORDER BY r.returned_date DESC LIMIT 10
    ''').fetchall()
    
    conn.close()
    return render_template('admin/returns.html', active_bookings=active_bookings, recent_returns=recent_returns)

@app.route('/admin/return/<int:booking_id>', methods=['GET', 'POST'])
@admin_required
def return_equipment(booking_id):
    conn = get_db_connection()
    booking = conn.execute('''
        SELECT b.*, e.name as equipment_name, u.name as student_name
        FROM bookings b 
        JOIN equipment e ON b.equipment_id = e.id
        JOIN users u ON b.user_id = u.id
        WHERE b.id = ?
    ''', (booking_id,)).fetchone()
    
    if not booking or booking['status'] not in ['Active', 'Overdue', 'Approved']:
        flash('Invalid booking for return.', 'danger')
        conn.close()
        return redirect(url_for('admin_returns'))
        
    if request.method == 'POST':
        condition = request.form['condition']
        remarks = request.form['remarks']
        returned_date = datetime.datetime.now().strftime("%Y-%m-%d")
        returned_time = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Insert return record
        conn.execute('''
            INSERT INTO returns (booking_id, returned_date, returned_time, condition, remarks)
            VALUES (?, ?, ?, ?, ?)
        ''', (booking_id, returned_date, returned_time, condition, remarks))
        
        # Update booking status
        conn.execute('UPDATE bookings SET status = "Completed" WHERE id = ?', (booking_id,))
        
        # Increase available quantity
        conn.execute('UPDATE equipment SET available_quantity = available_quantity + ? WHERE id = ?', (booking['quantity'], booking['equipment_id']))
        
        conn.commit()
        conn.close()
        flash('Equipment returned successfully.', 'success')
        return redirect(url_for('admin_returns'))
        
    conn.close()
    return render_template('admin/return_equipment.html', booking=booking)

if __name__ == '__main__':
    app.run(debug=True)
