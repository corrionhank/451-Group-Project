# Lab Equipment Reservation System — Sprint 2 UI

## Setup

1. **Install dependencies:**
   ```
   pip install flask
   ```

2. **Run the app:**
   ```
   python app.py
   ```

3. **go to: http://127.0.0.1:5000** 

The database is created automatically on first run with sample data seeded in.

## Features

### CRUD Operations
- **Users**: Add, edit, delete users. Role is enforced.
  - Adding an admin automatically adds them to the Admins table.
- **Equipment**: Add, edit, delete equipment. Set availability status.
- **Reservations**: Create new reservations, update status/approval, cancel.

### Business Rules Enforced in UI
1. Equipment must be available to be reserved, error shown if not
2. No overlapping reservations for same equipment, conflict detected and rejected
3. End time must be after start time, validated before insert
4. Only admin IDs accepted in the 'Approved By' field, rejected otherwise
5. Completing a reservation auto-creates a Usage Log entry
6. Deleting a user cascades to their reservations
7. Duplicate emails rejected with clear error message

### Edge Cases Demonstrated
- Booking unavailable/maintenance equipment, error message
- Overlapping reservation attempt, conflict error
- Non-admin trying to approve, rejected
- Deleting a user with reservations, cascade shown in UI

### Reports (10 Advanced Queries)
All 10 JOIN queries from Part 5 are accessible under the Reports tab.
Each shows the query description, JOIN explanation, and live results.
