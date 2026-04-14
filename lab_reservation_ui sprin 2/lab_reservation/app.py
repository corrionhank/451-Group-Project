from flask import Flask, render_template, request, jsonify, g
import sqlite3
import os

app = Flask(__name__)
DATABASE = 'lab_reservation.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with open('schema.sql', 'r') as f:
            db.executescript(f.read())
        # Seed sample data if empty
        if db.execute("SELECT COUNT(*) FROM Users").fetchone()[0] == 0:
            db.executescript("""
                INSERT INTO Users (first_name, last_name, email, password_hash, role, is_verified)
                VALUES
                  ('Alice', 'Admin', 'alice@uni.edu', 'hashed_pw', 'admin', 1),
                  ('Bob', 'Student', 'bob@uni.edu', 'hashed_pw', 'student', 1),
                  ('Carol', 'Davis', 'carol@uni.edu', 'hashed_pw', 'researcher', 1),
                  ('Grace', 'Lee', 'grace@uni.edu', 'hashed_pw', 'student', 0);
                INSERT INTO Admins (admin_id) VALUES (1);
                INSERT INTO Equipment (name, description, serial_number, tags, availability, building, room_no)
                VALUES
                  ('Microscope', 'High resolution microscope', 'SN12345', 'bio,optics', 'available', 'Science Hall', '101'),
                  ('Centrifuge', 'High-speed centrifuge', 'SN67890', 'chem', 'available', 'Science Hall', '102'),
                  ('3D Printer', 'Dual extruder', 'SN11111', 'fab', 'available', 'Engineering Bldg', '201');
                INSERT INTO Reservations (user_id, equipment_id, approved_by, start_time, end_time, status)
                VALUES
                  (2, 1, 1, '2026-04-01 10:00:00', '2026-04-01 12:00:00', 'completed'),
                  (2, 2, NULL, '2026-04-10 09:00:00', '2026-04-10 11:00:00', 'pending'),
                  (3, 3, 1, '2026-04-12 14:00:00', '2026-04-12 16:00:00', 'approved');
                INSERT INTO Usage_Log (reservation_id, actual_start, actual_end, notes)
                VALUES (1, '2026-04-01 10:00:00', '2026-04-01 12:00:00', 'Auto-logged on completion');
            """)
            db.commit()

# Main page
@app.route('/')
def index():
    return render_template('index.html')

# USERS
@app.route('/api/users', methods=['GET'])
def get_users():
    db = get_db()
    users = db.execute("SELECT * FROM Users ORDER BY user_id").fetchall()
    return jsonify([dict(u) for u in users])

@app.route('/api/users', methods=['POST'])
def add_user():
    data = request.json
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO Users (first_name, last_name, email, password_hash, role) VALUES (?,?,?,?,?)",
            (data['first_name'], data['last_name'], data['email'], data.get('password_hash','hashed_pw'), data['role'])
        )
        user_id = cur.lastrowid
        if data['role'] == 'admin':
            db.execute("INSERT INTO Admins (admin_id) VALUES (?)", (user_id,))
        db.commit()
        return jsonify({'success': True, 'user_id': user_id})
    except sqlite3.IntegrityError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/users/<int:uid>', methods=['PUT'])
def update_user(uid):
    data = request.json
    db = get_db()
    try:
        db.execute(
            "UPDATE Users SET first_name=?, last_name=?, email=?, role=? WHERE user_id=?",
            (data['first_name'], data['last_name'], data['email'], data['role'], uid)
        )
        if data['role'] == 'admin':
            db.execute("INSERT OR IGNORE INTO Admins (admin_id) VALUES (?)", (uid,))
        else:
            db.execute("DELETE FROM Admins WHERE admin_id=?", (uid,))
        db.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    db = get_db()
    db.execute("DELETE FROM Users WHERE user_id=?", (uid,))
    db.commit()
    return jsonify({'success': True})

# EQUIPMENT
@app.route('/api/equipment', methods=['GET'])
def get_equipment():
    db = get_db()
    eq = db.execute("SELECT * FROM Equipment ORDER BY equipment_id").fetchall()
    return jsonify([dict(e) for e in eq])

@app.route('/api/equipment', methods=['POST'])
def add_equipment():
    data = request.json
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO Equipment (name, description, serial_number, tags, availability, building, room_no) VALUES (?,?,?,?,?,?,?)",
            (data['name'], data.get('description',''), data.get('serial_number',''), data.get('tags',''), data.get('availability','available'), data.get('building',''), data.get('room_no',''))
        )
        db.commit()
        return jsonify({'success': True, 'equipment_id': cur.lastrowid})
    except sqlite3.IntegrityError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/equipment/<int:eid>', methods=['PUT'])
def update_equipment(eid):
    data = request.json
    db = get_db()
    try:
        db.execute(
            "UPDATE Equipment SET name=?, description=?, serial_number=?, tags=?, availability=?, building=?, room_no=? WHERE equipment_id=?",
            (data['name'], data.get('description',''), data.get('serial_number',''), data.get('tags',''), data.get('availability','available'), data.get('building',''), data.get('room_no',''), eid)
        )
        db.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/equipment/<int:eid>', methods=['DELETE'])
def delete_equipment(eid):
    db = get_db()
    db.execute("DELETE FROM Equipment WHERE equipment_id=?", (eid,))
    db.commit()
    return jsonify({'success': True})

# RESERVATIONS
@app.route('/api/reservations', methods=['GET'])
def get_reservations():
    db = get_db()
    rows = db.execute("""
        SELECT r.*, u.first_name||' '||u.last_name AS user_name,
               e.name AS equipment_name,
               au.first_name||' '||au.last_name AS admin_name
        FROM Reservations r
        JOIN Users u ON r.user_id = u.user_id
        JOIN Equipment e ON r.equipment_id = e.equipment_id
        LEFT JOIN Admins a ON r.approved_by = a.admin_id
        LEFT JOIN Users au ON a.admin_id = au.user_id
        ORDER BY r.reservation_id
    """).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/reservations', methods=['POST'])
def add_reservation():
    data = request.json
    db = get_db()
    # Business rule: check equipment availability
    eq = db.execute("SELECT availability FROM Equipment WHERE equipment_id=?", (data['equipment_id'],)).fetchone()
    if not eq:
        return jsonify({'success': False, 'error': 'Equipment not found'}), 400
    if eq['availability'] != 'available':
        return jsonify({'success': False, 'error': f"Equipment is not available for booking (status: {eq['availability']})"}), 400
    # Business rule: check for overlapping reservations
    overlap = db.execute("""
        SELECT COUNT(*) as cnt FROM Reservations
        WHERE equipment_id=? AND status IN ('pending','approved')
        AND ? < end_time AND ? > start_time
    """, (data['equipment_id'], data['start_time'], data['end_time'])).fetchone()
    if overlap['cnt'] > 0:
        return jsonify({'success': False, 'error': 'Equipment already has a conflicting reservation for this time slot'}), 400
    # Business rule: end_time must be after start_time
    if data['end_time'] <= data['start_time']:
        return jsonify({'success': False, 'error': 'End time must be after start time'}), 400
    try:
        cur = db.execute(
            "INSERT INTO Reservations (user_id, equipment_id, start_time, end_time) VALUES (?,?,?,?)",
            (data['user_id'], data['equipment_id'], data['start_time'], data['end_time'])
        )
        db.commit()
        return jsonify({'success': True, 'reservation_id': cur.lastrowid})
    except sqlite3.IntegrityError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/reservations/<int:rid>', methods=['PUT'])
def update_reservation(rid):
    data = request.json
    db = get_db()
    # Business rule: only admins can approve
    if 'approved_by' in data and data['approved_by']:
        is_admin = db.execute("SELECT 1 FROM Admins WHERE admin_id=?", (data['approved_by'],)).fetchone()
        if not is_admin:
            return jsonify({'success': False, 'error': 'Only admins can approve reservations'}), 400
    try:
        db.execute(
            "UPDATE Reservations SET status=?, approved_by=? WHERE reservation_id=?",
            (data.get('status'), data.get('approved_by'), rid)
        )
        # Business rule: auto-log on completion
        if data.get('status') == 'completed':
            res = db.execute("SELECT * FROM Reservations WHERE reservation_id=?", (rid,)).fetchone()
            existing = db.execute("SELECT 1 FROM Usage_Log WHERE reservation_id=?", (rid,)).fetchone()
            if not existing:
                db.execute(
                    "INSERT INTO Usage_Log (reservation_id, actual_start, actual_end, notes) VALUES (?,?,?,?)",
                    (rid, res['start_time'], res['end_time'], 'Auto-logged on completion')
                )
        db.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/reservations/<int:rid>', methods=['DELETE'])
def delete_reservation(rid):
    db = get_db()
    db.execute("DELETE FROM Reservations WHERE reservation_id=?", (rid,))
    db.commit()
    return jsonify({'success': True})

# USAGE LOG
@app.route('/api/usage_log', methods=['GET'])
def get_usage_log():
    db = get_db()
    rows = db.execute("""
        SELECT ul.*, e.name AS equipment_name,
               u.first_name||' '||u.last_name AS user_name
        FROM Usage_Log ul
        JOIN Reservations r ON ul.reservation_id = r.reservation_id
        JOIN Equipment e ON r.equipment_id = e.equipment_id
        JOIN Users u ON r.user_id = u.user_id
        ORDER BY ul.log_id
    """).fetchall()
    return jsonify([dict(r) for r in rows])

# ADVANCED QUERIES
@app.route('/api/reports/<report>', methods=['GET'])
def run_report(report):
    db = get_db()
    queries = {
        'all_reservations': """
            SELECT r.reservation_id, u.first_name||' '||u.last_name AS user_name,
                   e.name AS equipment_name, r.start_time, r.end_time, r.status
            FROM Reservations r
            JOIN Users u ON r.user_id = u.user_id
            JOIN Equipment e ON r.equipment_id = e.equipment_id
        """,
        'approved_with_admin': """
            SELECT r.reservation_id, u.first_name||' '||u.last_name AS user_name,
                   au.first_name||' '||au.last_name AS admin_name
            FROM Reservations r
            JOIN Users u ON r.user_id = u.user_id
            JOIN Admins a ON r.approved_by = a.admin_id
            JOIN Users au ON a.admin_id = au.user_id
            WHERE r.status = 'approved'
        """,
        'currently_reserved': """
            SELECT DISTINCT e.name, e.building, e.room_no
            FROM Equipment e
            JOIN Reservations r ON e.equipment_id = r.equipment_id
            WHERE r.status IN ('pending', 'approved')
        """,
        'usage_with_info': """
            SELECT ul.log_id, r.reservation_id, e.name AS equipment_name,
                   ul.actual_start, ul.actual_end, ul.notes
            FROM Usage_Log ul
            JOIN Reservations r ON ul.reservation_id = r.reservation_id
            JOIN Equipment e ON r.equipment_id = e.equipment_id
        """,
        'reservations_per_user': """
            SELECT u.user_id, u.first_name||' '||u.last_name AS user_name,
                   COUNT(r.reservation_id) AS total_reservations
            FROM Users u
            LEFT JOIN Reservations r ON u.user_id = r.user_id
            GROUP BY u.user_id, u.first_name, u.last_name
        """,
        'overlapping': """
            SELECT r1.reservation_id AS res1, r2.reservation_id AS res2,
                   e.name AS equipment_name
            FROM Reservations r1
            JOIN Reservations r2 ON r1.equipment_id = r2.equipment_id
              AND r1.reservation_id < r2.reservation_id
              AND r1.start_time < r2.end_time
              AND r1.end_time > r2.start_time
            JOIN Equipment e ON r1.equipment_id = e.equipment_id
        """,
        'pending_with_location': """
            SELECT r.reservation_id, e.name, e.building, e.room_no, r.start_time, r.end_time
            FROM Reservations r
            JOIN Equipment e ON r.equipment_id = e.equipment_id
            WHERE r.status = 'pending'
        """,
        'by_building': """
            SELECT r.reservation_id, e.name, e.building, r.status, r.start_time
            FROM Reservations r
            JOIN Equipment e ON r.equipment_id = e.equipment_id
            WHERE e.building = 'Science Hall'
        """,
        'completed_duration': """
            SELECT r.reservation_id, e.name AS equipment_name,
                   ROUND((JULIANDAY(ul.actual_end) - JULIANDAY(ul.actual_start)) * 1440) AS duration_minutes
            FROM Reservations r
            JOIN Usage_Log ul ON r.reservation_id = ul.reservation_id
            JOIN Equipment e ON r.equipment_id = e.equipment_id
            WHERE r.status = 'completed'
        """,
        'never_reserved': """
            SELECT u.user_id, u.first_name||' '||u.last_name AS user_name, u.role
            FROM Users u
            LEFT JOIN Reservations r ON u.user_id = r.user_id
            WHERE r.reservation_id IS NULL
        """
    }
    if report not in queries:
        return jsonify({'error': 'Unknown report'}), 404
    rows = db.execute(queries[report]).fetchall()
    return jsonify([dict(r) for r in rows])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)