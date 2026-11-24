from tkinter import *
from tkinter import ttk, messagebox
import sqlite3
import uuid
import hashlib
import secrets
from datetime import datetime


class PayrollSystem:

    def __init__(self):
        self.root = Tk()
        self.root.title("Payroll System")
        self.root.geometry("900x600")
        self.root.resizable(False, False)

        self.create_database()

    def connect_database(self):
        conn = sqlite3.connect("payroll.db")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_database(self):

        conn = self.connect_database()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                position TEXT NOT NULL,
                department TEXT NOT NULL,
                dailyrate REAL NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS payroll (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                days_worked INTEGER NOT NULL,
                gross_pay REAL NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (employee_id)
                REFERENCES employees(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                date TEXT NOT NULL,
                time_in TEXT,
                time_out TEXT,
                hours_worked REAL DEFAULT 0,
                UNIQUE(employee_id, date),
                FOREIGN KEY (employee_id)
                REFERENCES employees(id)
            )
        """)

        # Add any columns missing from older databases
        migrations = {
            "employees": [
                ("email", "TEXT"),
                ("phone", "TEXT"),
                ("address", "TEXT"),
                ("date_hired", "TEXT"),
                ("username", "TEXT"),
                ("password_hash", "TEXT")
            ],
            "payroll": [
                ("sss", "REAL DEFAULT 0"),
                ("pagibig", "REAL DEFAULT 0"),
                ("tax", "REAL DEFAULT 0"),
                ("net_pay", "REAL")
            ],
            "attendance": [
                ("payroll_id", "TEXT")
            ]
        }

        for table_name, new_columns in migrations.items():

            cur.execute(f"PRAGMA table_info({table_name})")

            existing = [col[1] for col in cur.fetchall()]

            for column_name, data_type in new_columns:

                if column_name not in existing:
                    cur.execute(
                        f"ALTER TABLE {table_name} "
                        f"ADD COLUMN {column_name} {data_type}"
                    )

        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            unique_employee_username
            ON employees(username)
        """)

        conn.commit()
        conn.close()

    def hash_password(self, password):

        salt = secrets.token_hex(16)

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            600000
        )

        return salt + "$" + password_hash.hex()

    def verify_password(self, password, stored_hash):

        try:

            salt, original_hash = stored_hash.split("$")

            password_hash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(),
                salt.encode(),
                600000
            )

            return secrets.compare_digest(
                password_hash.hex(),
                original_hash
            )

        except (ValueError, AttributeError):
            return False

    def compute_tax(self, gross):
        """
        Philippine TRAIN withholding tax (monthly brackets).
        Gross pay is treated as monthly taxable income.
        """

        # (lower bound, base tax, rate on excess over lower bound)
        brackets = [
            (666667, 183541.80, 0.35),
            (166667, 33541.80, 0.30),
            (66667, 8541.80, 0.25),
            (33333, 1875.00, 0.20),
            (20833, 0.00, 0.15),
        ]

        for lower, base, rate in brackets:

            if gross > lower:
                return round(base + (gross - lower) * rate, 2)

        return 0.0

    def compute_sss(self, monthly_pay):
        """
        SSS employee share (2025-2026 schedule): 5% of the Monthly Salary
        Credit (MSC). MSC moves in PHP 500 steps, min 5,000, max 35,000.
        (Employer share of 10% + EC is paid by the company, not deducted.)
        """

        msc = int((monthly_pay + 250) // 500) * 500
        msc = max(5000, min(35000, msc))

        return round(msc * 0.05, 2)

    def compute_pagibig(self, monthly_pay):
        """
        Pag-IBIG (HDMF) employee share: 2% of monthly compensation,
        with the Monthly Fund Salary capped at PHP 10,000 (max PHP 200).
        """

        fund_salary = min(monthly_pay, 10000)

        return round(fund_salary * 0.02, 2)

    def clear_window(self):

        # Remove mouse wheel binding left by scrollable pages
        self.root.unbind_all("<MouseWheel>")

        for widget in self.root.winfo_children():
            widget.destroy()

    def create_title(self, text):

        Label(
            self.root,
            text=text,
            font=("Arial", 20, "bold")
        ).pack(pady=20)

    def create_scrollable_frame(self):

        container = Frame(self.root)
        container.pack(fill=BOTH, expand=True)

        canvas = Canvas(container, highlightthickness=0)

        scrollbar = ttk.Scrollbar(
            container,
            orient=VERTICAL,
            command=canvas.yview
        )

        content = Frame(canvas)

        content.bind(
            "<Configure>",
            lambda event: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        window_id = canvas.create_window(
            (0, 0),
            window=content,
            anchor="nw"
        )

        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(
                window_id,
                width=event.width
            )
        )

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        def scroll_with_mouse(event):
            canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )

        canvas.bind_all("<MouseWheel>", scroll_with_mouse)

        return content

    # ------------------------------------------------------------------
    # MAIN / LOGIN
    # ------------------------------------------------------------------

    def main_page(self):

        self.clear_window()

        self.create_title("PAYROLL SYSTEM")

        Button(
            self.root,
            text="Employee Login",
            width=30,
            command=self.employee_login_page
        ).pack(pady=10)

        Button(
            self.root,
            text="Admin Login",
            width=30,
            command=self.admin_login_page
        ).pack(pady=10)

    def admin_login_page(self):

        self.clear_window()

        self.create_title("ADMIN LOGIN")

        Label(self.root, text="Username").pack()

        username = Entry(self.root, width=35)
        username.pack(pady=5)

        Label(self.root, text="Password").pack()

        password = Entry(
            self.root,
            width=35,
            show="*"
        )
        password.pack(pady=5)

        Label(
            self.root,
            text="Demo credentials: admin / admin123",
            font=("Arial", 9)
        ).pack(pady=5)

        def login():

            if username.get() == "admin" and password.get() == "admin123":
                self.admin_page()

            else:
                messagebox.showerror(
                    "Login Failed",
                    "Incorrect username or password."
                )

        Button(
            self.root,
            text="Login",
            width=20,
            command=login
        ).pack(pady=15)

        Button(
            self.root,
            text="Back",
            command=self.main_page
        ).pack()

    # ------------------------------------------------------------------
    # ADMIN
    # ------------------------------------------------------------------

    def admin_page(self):

        self.clear_window()

        self.create_title("ADMIN DASHBOARD")

        Button(
            self.root,
            text="Add Employee",
            width=30,
            command=self.add_employee_page
        ).pack(pady=8)

        Button(
            self.root,
            text="Employee Information",
            width=30,
            command=self.employee_info_page
        ).pack(pady=8)

        Button(
            self.root,
            text="Calculate Payroll",
            width=30,
            command=self.calculate_payroll_page
        ).pack(pady=8)

        Button(
            self.root,
            text="Payroll Records",
            width=30,
            command=self.payroll_records_page
        ).pack(pady=8)

        Button(
            self.root,
            text="Logout",
            width=30,
            command=self.main_page
        ).pack(pady=8)

    def add_employee_page(self):

        self.clear_window()

        content = self.create_scrollable_frame()

        Label(
            content,
            text="ADD EMPLOYEE",
            font=("Arial", 20, "bold")
        ).pack(pady=20)

        fields = [
            "Employee Name",
            "Position",
            "Department",
            "Daily Rate",
            "Email",
            "Phone Number",
            "Address",
            "Date Hired",
            "Username",
            "Password"
        ]

        entries = {}

        form = Frame(content)
        form.pack(pady=5)

        for row, field in enumerate(fields):

            Label(
                form,
                text=field,
                anchor="w"
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=10,
                pady=6
            )

            entry = Entry(
                form,
                width=45,
                show="*" if field == "Password" else ""
            )

            entry.grid(
                row=row,
                column=1,
                padx=10,
                pady=6
            )

            if field == "Date Hired":
                entry.insert(
                    0,
                    datetime.now().strftime("%Y-%m-%d")
                )

            entries[field] = entry

        def submit():

            values = {
                field: entry.get().strip()
                for field, entry in entries.items()
            }

            if not all(values.values()):

                messagebox.showerror(
                    "Error",
                    "Please complete all fields."
                )
                return

            try:

                daily_rate = float(values["Daily Rate"])

                if daily_rate <= 0:
                    raise ValueError

                datetime.strptime(
                    values["Date Hired"],
                    "%Y-%m-%d"
                )

            except ValueError:

                messagebox.showerror(
                    "Error",
                    "Enter a valid daily rate and date (YYYY-MM-DD)."
                )
                return

            employee_id = str(uuid.uuid4())

            password_hash = self.hash_password(
                values["Password"]
            )

            conn = self.connect_database()
            cur = conn.cursor()

            try:

                cur.execute("""
                    INSERT INTO employees (
                        id, name, position, department,
                        dailyrate, email, phone, address,
                        date_hired, username, password_hash
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    employee_id,
                    values["Employee Name"],
                    values["Position"],
                    values["Department"],
                    daily_rate,
                    values["Email"],
                    values["Phone Number"],
                    values["Address"],
                    values["Date Hired"],
                    values["Username"],
                    password_hash
                ))

                conn.commit()

                messagebox.showinfo(
                    "Success",
                    "Employee registered successfully!"
                )

                for entry in entries.values():
                    entry.delete(0, END)

                entries["Date Hired"].insert(
                    0,
                    datetime.now().strftime("%Y-%m-%d")
                )

            except sqlite3.IntegrityError:

                messagebox.showerror(
                    "Error",
                    "Username already exists."
                )

            finally:
                conn.close()

        Button(
            content,
            text="Submit",
            width=20,
            command=submit
        ).pack(pady=12)

        Button(
            content,
            text="Back",
            width=20,
            command=self.admin_page
        ).pack(pady=10)

    def employee_info_page(self):

        self.clear_window()

        self.create_title("EMPLOYEE INFORMATION")

        table_frame = Frame(self.root)
        table_frame.pack(
            fill=BOTH,
            expand=True,
            padx=10,
            pady=10
        )

        columns = (
            "id",
            "name",
            "position",
            "department",
            "dailyrate",
            "email",
            "phone"
        )

        table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings"
        )

        headings = {
            "id": "Employee ID",
            "name": "Name",
            "position": "Position",
            "department": "Department",
            "dailyrate": "Daily Rate",
            "email": "Email",
            "phone": "Phone"
        }

        for column, heading in headings.items():

            table.heading(column, text=heading)
            table.column(column, width=120)

        table.column("id", width=180)

        vertical_scrollbar = ttk.Scrollbar(
            table_frame,
            orient=VERTICAL,
            command=table.yview
        )

        horizontal_scrollbar = ttk.Scrollbar(
            table_frame,
            orient=HORIZONTAL,
            command=table.xview
        )

        table.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set
        )

        table.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        conn = self.connect_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, name, position, department,
                   dailyrate, email, phone
            FROM employees
        """)

        employees = cur.fetchall()

        conn.close()

        for employee in employees:

            table.insert(
                "",
                END,
                values=employee
            )

        Button(
            self.root,
            text="Back",
            command=self.admin_page
        ).pack(pady=10)

    def calculate_payroll_page(self):

        self.clear_window()

        self.create_title("CALCULATE PAYROLL")

        columns = ("id", "name", "dailyrate", "unpaid_days")

        table = ttk.Treeview(
            self.root,
            columns=columns,
            show="headings",
            height=8
        )

        table.heading("id", text="Employee ID")
        table.heading("name", text="Employee Name")
        table.heading("dailyrate", text="Daily Rate")
        table.heading("unpaid_days", text="Unpaid Days (Attendance)")

        table.column("id", width=280)
        table.column("name", width=200)
        table.column("dailyrate", width=120)
        table.column("unpaid_days", width=180)

        table.pack(fill=X, padx=10, pady=10)

        conn = self.connect_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT e.id, e.name, e.dailyrate,
                   (SELECT COUNT(*) FROM attendance a
                    WHERE a.employee_id = e.id
                    AND a.payroll_id IS NULL
                    AND a.time_out IS NOT NULL)
            FROM employees e
            ORDER BY e.name
        """)

        for employee in cur.fetchall():
            table.insert("", END, values=employee)

        conn.close()

        Label(
            self.root,
            text="Select an employee. Days worked are taken from "
                 "unpaid attendance records.",
            font=("Arial", 10)
        ).pack(pady=5)

        result_label = Label(
            self.root,
            text="Gross: ₱0.00   |   SSS: ₱0.00   |   Pag-IBIG: ₱0.00\n"
                 "Tax: ₱0.00   |   Net: ₱0.00",
            font=("Arial", 12, "bold")
        )
        result_label.pack(pady=10)

        def calculate():

            selected = table.selection()

            if not selected:
                messagebox.showerror(
                    "Error",
                    "Please select an employee."
                )
                return

            values = table.item(selected[0], "values")

            employee_id = values[0]
            name = values[1]
            daily_rate = float(values[2])

            conn = self.connect_database()
            cur = conn.cursor()

            cur.execute("""
                SELECT id FROM attendance
                WHERE employee_id = ?
                AND payroll_id IS NULL
                AND time_out IS NOT NULL
            """, (employee_id,))

            attendance_ids = [row[0] for row in cur.fetchall()]
            days = len(attendance_ids)

            if days == 0:
                conn.close()
                messagebox.showerror(
                    "Error",
                    "No unpaid attendance records for this employee."
                )
                return

            gross = round(daily_rate * days, 2)
            sss = self.compute_sss(gross)
            pagibig = self.compute_pagibig(gross)

            # SSS and Pag-IBIG contributions are tax-exempt,
            # so withholding tax is computed on what remains
            taxable_income = gross - sss - pagibig
            tax = self.compute_tax(taxable_income)

            net = round(gross - sss - pagibig - tax, 2)

            result_label.config(
                text=f"Gross: ₱{gross:,.2f}   |   "
                     f"SSS: ₱{sss:,.2f}   |   "
                     f"Pag-IBIG: ₱{pagibig:,.2f}\n"
                     f"Tax: ₱{tax:,.2f}   |   Net: ₱{net:,.2f}"
            )

            confirm = messagebox.askyesno(
                "Confirm Payroll",
                f"Employee: {name}\n"
                f"Days Worked: {days}\n"
                f"Gross Pay: ₱{gross:,.2f}\n"
                f"SSS: ₱{sss:,.2f}\n"
                f"Pag-IBIG: ₱{pagibig:,.2f}\n"
                f"Withholding Tax: ₱{tax:,.2f}\n"
                f"Net Pay: ₱{net:,.2f}\n\n"
                f"Save this payroll?"
            )

            if not confirm:
                conn.close()
                return

            payroll_id = str(uuid.uuid4())

            try:

                cur.execute("""
                    INSERT INTO payroll (
                        id, employee_id, days_worked,
                        gross_pay, sss, pagibig, tax, net_pay, date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    payroll_id,
                    employee_id,
                    days,
                    gross,
                    sss,
                    pagibig,
                    tax,
                    net,
                    datetime.now().strftime("%Y-%m-%d")
                ))

                cur.executemany(
                    "UPDATE attendance SET payroll_id = ? WHERE id = ?",
                    [(payroll_id, att_id) for att_id in attendance_ids]
                )

                conn.commit()

                messagebox.showinfo(
                    "Success",
                    "Payroll saved successfully!"
                )

            except sqlite3.Error as error:

                conn.rollback()
                messagebox.showerror("Database Error", str(error))

            finally:
                conn.close()

            self.calculate_payroll_page()

        Button(
            self.root,
            text="Calculate & Save",
            width=20,
            command=calculate
        ).pack(pady=5)

        Button(
            self.root,
            text="Back",
            command=self.admin_page
        ).pack(pady=10)

    def payroll_records_page(self):

        self.clear_window()

        self.create_title("PAYROLL RECORDS")

        columns = (
            "name", "days", "gross", "sss",
            "pagibig", "tax", "net", "date"
        )

        table = ttk.Treeview(
            self.root,
            columns=columns,
            show="headings"
        )

        table.heading("name", text="Employee")
        table.heading("days", text="Days Worked")
        table.heading("gross", text="Gross Pay")
        table.heading("sss", text="SSS")
        table.heading("pagibig", text="Pag-IBIG")
        table.heading("tax", text="Tax")
        table.heading("net", text="Net Pay")
        table.heading("date", text="Date")

        for col in columns:
            table.column(col, width=100, anchor="center")

        table.pack(
            fill=BOTH,
            expand=True,
            padx=10,
            pady=10
        )

        conn = self.connect_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT employees.name,
                   payroll.days_worked,
                   payroll.gross_pay,
                   COALESCE(payroll.sss, 0),
                   COALESCE(payroll.pagibig, 0),
                   COALESCE(payroll.tax, 0),
                   COALESCE(payroll.net_pay, payroll.gross_pay),
                   payroll.date
            FROM payroll
            JOIN employees
            ON payroll.employee_id = employees.id
            ORDER BY payroll.date DESC
        """)

        records = cur.fetchall()

        conn.close()

        for r in records:

            table.insert(
                "",
                END,
                values=(
                    r[0],
                    r[1],
                    f"₱{r[2]:,.2f}",
                    f"₱{r[3]:,.2f}",
                    f"₱{r[4]:,.2f}",
                    f"₱{r[5]:,.2f}",
                    f"₱{r[6]:,.2f}",
                    r[7]
                )
            )

        Button(
            self.root,
            text="Back",
            command=self.admin_page
        ).pack(pady=10)

    # ------------------------------------------------------------------
    # EMPLOYEE
    # ------------------------------------------------------------------

    def employee_login_page(self):

        self.clear_window()

        self.create_title("EMPLOYEE LOGIN")

        Label(self.root, text="Username").pack()

        username = Entry(self.root, width=35)
        username.pack(pady=5)

        Label(self.root, text="Password").pack()

        password = Entry(
            self.root,
            width=35,
            show="*"
        )

        password.pack(pady=5)

        def login():

            conn = self.connect_database()
            cur = conn.cursor()

            cur.execute("""
                SELECT id, name, password_hash
                FROM employees
                WHERE username = ?
            """, (username.get().strip(),))

            employee = cur.fetchone()

            conn.close()

            if employee is None:

                messagebox.showerror(
                    "Login Failed",
                    "Username does not exist."
                )
                return

            employee_id, name, password_hash = employee

            if self.verify_password(
                password.get(),
                password_hash
            ):

                self.employee_dashboard(employee_id)

            else:

                messagebox.showerror(
                    "Login Failed",
                    "Incorrect password."
                )

        Button(
            self.root,
            text="Login",
            width=20,
            command=login
        ).pack(pady=15)

        Button(
            self.root,
            text="Back",
            command=self.main_page
        ).pack()

    def employee_dashboard(self, employee_id):

        self.clear_window()

        conn = self.connect_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT name, position, department,
                   email, phone, address,
                   date_hired, dailyrate
            FROM employees
            WHERE id = ?
        """, (employee_id,))

        employee = cur.fetchone()

        conn.close()

        if employee is None:
            self.main_page()
            return

        (
            name,
            position,
            department,
            email,
            phone,
            address,
            date_hired,
            daily_rate
        ) = employee

        self.create_title(
            f"WELCOME, {name.upper()}"
        )

        Label(
            self.root,
            text=f"Position: {position}"
        ).pack(pady=3)

        Label(
            self.root,
            text=f"Department: {department}"
        ).pack(pady=3)

        Label(
            self.root,
            text=f"Email: {email}"
        ).pack(pady=3)

        Label(
            self.root,
            text=f"Phone: {phone}"
        ).pack(pady=3)

        Label(
            self.root,
            text=f"Address: {address}"
        ).pack(pady=3)

        Label(
            self.root,
            text=f"Date Hired: {date_hired}"
        ).pack(pady=3)

        Label(
            self.root,
            text=f"Daily Rate: ₱{daily_rate:,.2f}"
        ).pack(pady=3)

        Button(
            self.root,
            text="My Attendance",
            width=25,
            command=lambda: self.employee_attendance_page(employee_id)
        ).pack(pady=6)

        Button(
            self.root,
            text="My Payslips",
            width=25,
            command=lambda: self.employee_payslip_page(employee_id)
        ).pack(pady=6)

        Button(
            self.root,
            text="My Payroll History",
            width=25,
            command=lambda: self.employee_payroll_page(employee_id)
        ).pack(pady=6)

        Button(
            self.root,
            text="Logout",
            width=25,
            command=self.main_page
        ).pack(pady=5)

    def employee_attendance_page(self, employee_id):

        self.clear_window()

        self.create_title("MY ATTENDANCE")

        today = datetime.now().strftime("%Y-%m-%d")

        conn = self.connect_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT time_in, time_out, hours_worked
            FROM attendance
            WHERE employee_id = ? AND date = ?
        """, (employee_id, today))

        attendance = cur.fetchone()

        conn.close()

        if attendance:

            Label(
                self.root,
                text=f"Date: {today}",
                font=("Arial", 12, "bold")
            ).pack(pady=5)

            Label(
                self.root,
                text=f"Time In: {attendance[0] or 'Not recorded'}"
            ).pack(pady=5)

            Label(
                self.root,
                text=f"Time Out: {attendance[1] or 'Not recorded'}"
            ).pack(pady=5)

            Label(
                self.root,
                text=f"Working Hours: {attendance[2]:.2f}"
            ).pack(pady=5)

        else:

            Label(
                self.root,
                text="You have not timed in today."
            ).pack(pady=10)

        def time_in():

            current_time = datetime.now()

            conn = self.connect_database()
            cur = conn.cursor()

            try:

                cur.execute("""
                    INSERT INTO attendance (
                        id, employee_id, date, time_in
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    employee_id,
                    today,
                    current_time.strftime("%H:%M:%S")
                ))

                conn.commit()

                messagebox.showinfo(
                    "Success",
                    "Time in recorded successfully!"
                )

            except sqlite3.IntegrityError:

                messagebox.showerror(
                    "Error",
                    "You have already timed in today."
                )

            finally:
                conn.close()

            self.employee_attendance_page(employee_id)

        def time_out():

            current_time = datetime.now()

            conn = self.connect_database()
            cur = conn.cursor()

            cur.execute("""
                SELECT id, time_in, time_out
                FROM attendance
                WHERE employee_id = ? AND date = ?
            """, (employee_id, today))

            record = cur.fetchone()

            if record is None:

                conn.close()

                messagebox.showerror(
                    "Error",
                    "Please time in first."
                )
                return

            if record[2] is not None:

                conn.close()

                messagebox.showerror(
                    "Error",
                    "You have already timed out."
                )
                return

            time_in_datetime = datetime.strptime(
                today + " " + record[1],
                "%Y-%m-%d %H:%M:%S"
            )

            hours = (
                current_time - time_in_datetime
            ).total_seconds() / 3600

            if hours <= 0:

                conn.close()

                messagebox.showerror(
                    "Error",
                    "Invalid time out."
                )
                return

            cur.execute("""
                UPDATE attendance
                SET time_out = ?, hours_worked = ?
                WHERE id = ?
            """, (
                current_time.strftime("%H:%M:%S"),
                round(hours, 2),
                record[0]
            ))

            conn.commit()
            conn.close()

            messagebox.showinfo(
                "Success",
                "Time out recorded successfully!"
            )

            self.employee_attendance_page(employee_id)

        Button(
            self.root,
            text="TIME IN",
            width=25,
            command=time_in
        ).pack(pady=8)

        Button(
            self.root,
            text="TIME OUT",
            width=25,
            command=time_out
        ).pack(pady=8)

        Label(
            self.root,
            text="ATTENDANCE HISTORY",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        columns = (
            "date",
            "time_in",
            "time_out",
            "hours"
        )

        table = ttk.Treeview(
            self.root,
            columns=columns,
            show="headings",
            height=7
        )

        table.heading("date", text="Date")
        table.heading("time_in", text="Time In")
        table.heading("time_out", text="Time Out")
        table.heading("hours", text="Working Hours")

        table.pack(
            fill=BOTH,
            expand=True,
            padx=10,
            pady=5
        )

        conn = self.connect_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT date, time_in, time_out, hours_worked
            FROM attendance
            WHERE employee_id = ?
            ORDER BY date DESC
        """, (employee_id,))

        records = cur.fetchall()

        conn.close()

        for record in records:

            table.insert(
                "",
                END,
                values=record
            )

        Button(
            self.root,
            text="Back",
            command=lambda: self.employee_dashboard(employee_id)
        ).pack(pady=8)

    def employee_payslip_page(self, employee_id):

        self.clear_window()

        self.create_title("MY PAYSLIPS")

        columns = (
            "date",
            "days",
            "gross",
            "sss",
            "pagibig",
            "tax",
            "net"
        )

        table = ttk.Treeview(
            self.root,
            columns=columns,
            show="headings",
            height=12
        )

        table.heading("date", text="Payroll Date")
        table.heading("days", text="Days Worked")
        table.heading("gross", text="Gross Pay")
        table.heading("sss", text="SSS")
        table.heading("pagibig", text="Pag-IBIG")
        table.heading("tax", text="Tax")
        table.heading("net", text="Net Pay")

        for col in columns:
            table.column(col, width=115, anchor="center")

        table.pack(
            fill=BOTH,
            expand=True,
            padx=10,
            pady=10
        )

        conn = self.connect_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, date, days_worked, gross_pay,
                   COALESCE(sss, 0),
                   COALESCE(pagibig, 0),
                   COALESCE(tax, 0),
                   COALESCE(net_pay, gross_pay)
            FROM payroll
            WHERE employee_id = ?
            ORDER BY date DESC
        """, (employee_id,))

        records = cur.fetchall()

        conn.close()

        for r in records:

            table.insert(
                "",
                END,
                iid=r[0],
                values=(
                    r[1],
                    r[2],
                    f"₱{r[3]:,.2f}",
                    f"₱{r[4]:,.2f}",
                    f"₱{r[5]:,.2f}",
                    f"₱{r[6]:,.2f}",
                    f"₱{r[7]:,.2f}"
                )
            )

        def view_payslip():

            selected = table.selection()

            if not selected:

                messagebox.showerror(
                    "Error",
                    "Please select a payslip."
                )
                return

            payroll_id = selected[0]

            conn = self.connect_database()
            cur = conn.cursor()

            cur.execute("""
                SELECT employees.name,
                       employees.position,
                       employees.department,
                       employees.dailyrate,
                       payroll.days_worked,
                       payroll.gross_pay,
                       COALESCE(payroll.sss, 0),
                       COALESCE(payroll.pagibig, 0),
                       COALESCE(payroll.tax, 0),
                       COALESCE(payroll.net_pay, payroll.gross_pay),
                       payroll.date
                FROM payroll
                JOIN employees
                ON payroll.employee_id = employees.id
                WHERE payroll.id = ?
                AND payroll.employee_id = ?
            """, (payroll_id, employee_id))

            record = cur.fetchone()

            conn.close()

            if record is None:
                return

            (
                name,
                position,
                department,
                rate,
                days,
                gross,
                sss,
                pagibig,
                tax,
                net,
                date
            ) = record

            payslip = Toplevel(self.root)
            payslip.title("Employee Payslip")
            payslip.geometry("400x620")
            payslip.resizable(False, False)

            Label(
                payslip,
                text="EMPLOYEE PAYSLIP",
                font=("Arial", 18, "bold")
            ).pack(pady=20)

            details = [
                ("Employee Name", name),
                ("Position", position),
                ("Department", department),
                ("Payroll Date", date),
                ("Daily Rate", f"₱{rate:,.2f}"),
                ("Days Worked", str(days)),
                ("Gross Pay", f"₱{gross:,.2f}"),
                ("SSS Contribution", f"₱{sss:,.2f}"),
                ("Pag-IBIG Contribution", f"₱{pagibig:,.2f}"),
                ("Withholding Tax", f"₱{tax:,.2f}")
            ]

            for label, value in details:

                Label(
                    payslip,
                    text=f"{label}: {value}",
                    font=("Arial", 11)
                ).pack(
                    anchor="w",
                    padx=30,
                    pady=5
                )

            Label(
                payslip,
                text=f"NET PAY: ₱{net:,.2f}",
                font=("Arial", 16, "bold")
            ).pack(pady=20)

            Button(
                payslip,
                text="Close",
                command=payslip.destroy
            ).pack(pady=10)

        Button(
            self.root,
            text="View Payslip",
            width=20,
            command=view_payslip
        ).pack(pady=10)

        Button(
            self.root,
            text="Back",
            command=lambda: self.employee_dashboard(employee_id)
        ).pack(pady=10)

    def employee_payroll_page(self, employee_id):

        self.clear_window()

        self.create_title("MY PAYROLL HISTORY")

        columns = (
            "date",
            "days",
            "gross",
            "sss",
            "pagibig",
            "tax",
            "net"
        )

        table = ttk.Treeview(
            self.root,
            columns=columns,
            show="headings"
        )

        table.heading("date", text="Date")
        table.heading("days", text="Days Worked")
        table.heading("gross", text="Gross Pay")
        table.heading("sss", text="SSS")
        table.heading("pagibig", text="Pag-IBIG")
        table.heading("tax", text="Tax")
        table.heading("net", text="Net Pay")

        for col in columns:
            table.column(col, width=115, anchor="center")

        table.pack(
            fill=BOTH,
            expand=True,
            padx=10,
            pady=10
        )

        conn = self.connect_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT date, days_worked, gross_pay,
                   COALESCE(sss, 0),
                   COALESCE(pagibig, 0),
                   COALESCE(tax, 0),
                   COALESCE(net_pay, gross_pay)
            FROM payroll
            WHERE employee_id = ?
            ORDER BY date DESC
        """, (employee_id,))

        records = cur.fetchall()

        conn.close()

        for r in records:

            table.insert(
                "",
                END,
                values=(
                    r[0],
                    r[1],
                    f"₱{r[2]:,.2f}",
                    f"₱{r[3]:,.2f}",
                    f"₱{r[4]:,.2f}",
                    f"₱{r[5]:,.2f}",
                    f"₱{r[6]:,.2f}"
                )
            )

        Button(
            self.root,
            text="Back",
            command=lambda: self.employee_dashboard(employee_id)
        ).pack(pady=10)

    def run(self):

        self.main_page()
        self.root.mainloop()


if __name__ == "__main__":

    app = PayrollSystem()
    app.run()