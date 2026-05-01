CREATE TABLE IF NOT EXISTS Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'researcher', 'admin')),
    is_verified INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Admins (
    admin_id INTEGER PRIMARY KEY,
    FOREIGN KEY (admin_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Equipment (
    equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    serial_number TEXT UNIQUE,
    tags TEXT,
    availability TEXT DEFAULT 'available' CHECK (availability IN ('available', 'unavailable', 'maintenance')),
    building TEXT,
    room_no TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Reservations (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    equipment_id INTEGER NOT NULL,
    approved_by INTEGER,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'completed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (equipment_id) REFERENCES Equipment(equipment_id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES Admins(admin_id) ON DELETE SET NULL,
    CHECK (end_time > start_time)
);

CREATE TABLE IF NOT EXISTS Usage_Log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER UNIQUE,
    actual_start TIMESTAMP,
    actual_end TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (reservation_id) REFERENCES Reservations(reservation_id) ON DELETE SET NULL
);

CREATE TRIGGER IF NOT EXISTS auto_log_completion
AFTER UPDATE OF status ON Reservations
WHEN NEW.status = 'completed'
BEGIN
    INSERT OR IGNORE INTO Usage_Log (reservation_id, actual_start, actual_end, notes)
    VALUES (NEW.reservation_id, NEW.start_time, NEW.end_time, 'Auto-logged on completion');
END;
