from tkinter import *
from tkinter import ttk, messagebox
import sqlite3
import uuid
import hashlib
import secrets
from datetime import datetime


BG = "#f4f6fa"
CARD = "#ffffff"
BORDER = "#d9dee8"
PRIMARY = "#2457d6"
DANGER = "#c0392b"
MUTED = "#667085"
TEXT = "#1c2333"

MAX_CONTENT_WIDTH = 560


class PayrollSystem:

    def __init__(self):
        self.root = Tk()
        self.root.title("Payroll System")
        self.root.configure(bg=BG)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        self.mobile = screen_w <= 800 or screen_h > screen_w

        if self.mobile:
            self.root.geometry(f"{screen_w}x{screen_h}+0+0")
        else:
            self.root.geometry("900x650")
            self.root.minsize(340, 480)

        self.root.resizable(True, True)

        self.font_size = 10 if self.mobile else 11

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

        msc = int((monthly_pay + 250) // 500) * 500
        msc = max(5000, min(35000, msc))

        return round(msc * 0.05, 2)

    def compute_pagibig(self, monthly_pay):

        fund_salary = min(monthly_pay, 10000)

        return round(fund_salary * 0.02, 2)


    def font(self, delta=0, bold=False):

        return (
            "Arial",
            self.font_size + delta,
            "bold" if bold else "normal"
        )

    def clear_window(self):

        for sequence in (
            "<MouseWheel>", "<Button-4>", "<Button-5>",
            "<ButtonPress-1>", "<B1-Motion>"
        ):
            self.root.unbind_all(sequence)

        for widget in self.root.winfo_children():
            widget.destroy()

    def new_page(self, title):

        self.clear_window()

        container = Frame(self.root, bg=BG)
        container.pack(fill=BOTH, expand=True)

        canvas = Canvas(container, highlightthickness=0, bg=BG)

        scrollbar = ttk.Scrollbar(
            container,
            orient=VERTICAL,
            command=canvas.yview
        )

        content = Frame(canvas, bg=BG)

        window_id = canvas.create_window(
            (0, 0),
            window=content,
            anchor="n"
        )

        def fit_content(event=None):

            width = canvas.winfo_width()

            canvas.itemconfigure(
                window_id,
                width=min(width, MAX_CONTENT_WIDTH)
            )

            canvas.coords(window_id, width // 2, 0)

            canvas.configure(
                scrollregion=(
                    0,
                    0,
                    width,
                    max(
                        content.winfo_reqheight(),
                        canvas.winfo_height()
                    )
                )
            )

        canvas.bind("<Configure>", fit_content)
        content.bind("<Configure>", fit_content)

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=LEFT, fill=BOTH, expand=True)

        if not self.mobile:
            scrollbar.pack(side=RIGHT, fill=Y)

        def scrollable():
            return content.winfo_reqheight() > canvas.winfo_height()

        def on_wheel(event):

            if not scrollable():
                return

            if event.num == 4:
                canvas.yview_scroll(-3, "units")

            elif event.num == 5:
                canvas.yview_scroll(3, "units")

            elif event.delta:
                step = event.delta / 120 if abs(event.delta) >= 120 \
                    else event.delta
                canvas.yview_scroll(int(-step), "units")

        drag = {"y": 0, "top": 0.0, "ok": False}

        def on_press(event):

            drag["y"] = event.y_root
            drag["top"] = canvas.yview()[0]

            drag["ok"] = event.widget.winfo_class() not in (
                "Entry", "TEntry", "Scrollbar", "TScrollbar"
            )

        def on_drag(event):

            if not drag["ok"] or not scrollable():
                return

            total = max(content.winfo_reqheight(), 1)

            moved = (event.y_root - drag["y"]) / total

            canvas.yview_moveto(max(0.0, drag["top"] - moved))

        self.root.bind_all("<MouseWheel>", on_wheel)
        self.root.bind_all("<Button-4>", on_wheel)
        self.root.bind_all("<Button-5>", on_wheel)
        self.root.bind_all("<ButtonPress-1>", on_press, add="+")
        self.root.bind_all("<B1-Motion>", on_drag, add="+")

        Label(
            content,
            text=title,
            font=self.font(4, True),
            bg=BG,
            fg=TEXT,
            wraplength=self.wrap(),
            justify=CENTER
        ).pack(pady=(24, 14), padx=12)

        return content

    def wrap(self):

        width = self.root.winfo_screenwidth() if self.mobile \
            else MAX_CONTENT_WIDTH

        return max(220, min(width, MAX_CONTENT_WIDTH) - 70)

    def button(self, parent, text, command, kind="primary"):

        colors = {
            "primary": (PRIMARY, "white"),
            "secondary": ("#e6ebf5", PRIMARY),
            "danger": (DANGER, "white")
        }

        bg, fg = colors[kind]

        Button(
            parent,
            text=text,
            command=command,
            font=self.font(0, True),
            bg=bg,
            fg=fg,
            activebackground=bg,
            activeforeground=fg,
            relief=FLAT,
            bd=0,
            cursor="hand2"
        ).pack(
            fill=X,
            padx=16,
            pady=6,
            ipady=8 if self.mobile else 8
        )

    def card(self, parent, heading=None):

        frame = Frame(
            parent,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        frame.pack(fill=X, padx=12, pady=6)

        if heading:

            Label(
                frame,
                text=heading,
                font=self.font(0, True),
                bg=CARD,
                fg=TEXT,
                anchor="w",
                wraplength=self.wrap(),
                justify=LEFT
            ).pack(fill=X, padx=12, pady=(10, 4))

        return frame

    def row(self, parent, label, value, bold=False):

        line = Frame(parent, bg=CARD)
        line.pack(fill=X, padx=12, pady=3)

        Label(
            line,
            text=label,
            font=self.font(-1),
            bg=CARD,
            fg=MUTED,
            anchor="w"
        ).pack(side=LEFT)

        Label(
            line,
            text=str(value),
            font=self.font(0, bold),
            bg=CARD,
            fg=TEXT,
            anchor="e",
            justify=RIGHT,
            wraplength=int(self.wrap() * 0.6)
        ).pack(side=RIGHT)

    def end_card(self, card):

        Frame(card, bg=CARD, height=8).pack()

    def field(self, parent, label, show="", default=""):

        Label(
            parent,
            text=label,
            font=self.font(-1, True),
            bg=BG,
            fg=TEXT,
            anchor="w"
        ).pack(fill=X, padx=16, pady=(10, 2))

        entry = Entry(
            parent,
            font=self.font(0),
            show=show,
            relief=SOLID,
            bd=1,
            highlightthickness=1,
            highlightcolor=PRIMARY,
            highlightbackground=BORDER
        )

        entry.pack(
            fill=X,
            padx=16,
            ipady=6 if self.mobile else 5
        )

        if default:
            entry.insert(0, default)

        return entry

    def note(self, parent, text):

        Label(
            parent,
            text=text,
            font=self.font(-1),
            bg=BG,
            fg=MUTED,
            wraplength=self.wrap(),
            justify=CENTER
        ).pack(pady=6, padx=12)


    def main_page(self):

        content = self.new_page("PAYROLL SYSTEM")

        self.button(content, "Employee Login", self.employee_login_page)
        self.button(
            content, "Admin Login", self.admin_login_page, "secondary"
        )

    def admin_login_page(self):

        content = self.new_page("ADMIN LOGIN")

        username = self.field(content, "Username")
        password = self.field(content, "Password", show="*")

        self.note(content, "Demo credentials: admin / admin123")

        def login():

            if username.get() == "admin" and password.get() == "admin123":
                self.admin_page()

            else:
                messagebox.showerror(
                    "Login Failed",
                    "Incorrect username or password."
                )

        self.button(content, "Login", login)
        self.button(content, "Back", self.main_page, "secondary")


    def admin_page(self):

        content = self.new_page("ADMIN DASHBOARD")

        self.button(content, "Add Employee", self.add_employee_page)
        self.button(
            content, "Employee Information", self.employee_info_page
        )
        self.button(
            content, "Calculate Payroll", self.calculate_payroll_page
        )
        self.button(
            content, "Payroll Records", self.payroll_records_page
        )
        self.button(content, "Logout", self.main_page, "secondary")

    def add_employee_page(self):

        content = self.new_page("ADD EMPLOYEE")

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

        for field in fields:

            entries[field] = self.field(
                content,
                field if field != "Date Hired"
                else "Date Hired (YYYY-MM-DD)",
                show="*" if field == "Password" else "",
                default=datetime.now().strftime("%Y-%m-%d")
                if field == "Date Hired" else ""
            )

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

        Frame(content, bg=BG, height=10).pack()

        self.button(content, "Submit", submit)
        self.button(content, "Back", self.admin_page, "secondary")

    def employee_info_page(self):

        content = self.new_page("EMPLOYEE INFORMATION")

        conn = self.connect_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, name, position, department,
                   dailyrate, email, phone
            FROM employees
            ORDER BY name
        """)

        employees = cur.fetchall()

        conn.close()

        if not employees:
            self.note(content, "No employees yet.")

        for emp in employees:

            card = self.card(content, emp[1])

            self.row(card, "Position", emp[2])
            self.row(card, "Department", emp[3])
            self.row(card, "Daily Rate", f"₱{emp[4]:,.2f}")
            self.row(card, "Email", emp[5] or "")
            self.row(card, "Phone", emp[6] or "")
            self.row(card, "ID", emp[0][:8] + "...")

            Button(
                card,
                text="Edit",
                command=lambda i=emp[0]: self.edit_employee_page(i),
                font=self.font(0, True),
                bg=PRIMARY,
                fg="white",
                activebackground=PRIMARY,
                activeforeground="white",
                relief=FLAT,
                bd=0
            ).pack(
                fill=X,
                padx=12,
                pady=(8, 12),
                ipady=7 if self.mobile else 6
            )

        self.button(content, "Back", self.admin_page, "secondary")

    def edit_employee_page(self, employee_id):

        conn = self.connect_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT name, position, department, dailyrate,
                   email, phone, address, date_hired, username
            FROM employees
            WHERE id = ?
        """, (employee_id,))

        employee = cur.fetchone()

        conn.close()

        if employee is None:
            messagebox.showerror("Error", "Employee not found.")
            self.employee_info_page()
            return

        content = self.new_page("EDIT EMPLOYEE")

        labels = [
            ("name", "Employee Name"),
            ("position", "Position"),
            ("department", "Department"),
            ("dailyrate", "Daily Rate"),
            ("email", "Email"),
            ("phone", "Phone Number"),
            ("address", "Address"),
            ("date_hired", "Date Hired (YYYY-MM-DD)"),
            ("username", "Username"),
        ]

        entries = {}

        for index, (key, label) in enumerate(labels):

            value = employee[index]

            entries[key] = self.field(
                content,
                label,
                default="" if value is None else str(value)
            )

        new_password = self.field(
            content,
            "New Password (leave blank to keep current)",
            show="*"
        )

        self.note(
            content,
            "A changed daily rate applies to payroll calculated "
            "from now on. Saved payrolls are not changed."
        )

        def save():

            values = {
                key: entry.get().strip()
                for key, entry in entries.items()
            }

            if not all(values.values()):

                messagebox.showerror(
                    "Error",
                    "Please complete all fields."
                )
                return

            try:

                daily_rate = float(values["dailyrate"])

                if daily_rate <= 0:
                    raise ValueError

                datetime.strptime(
                    values["date_hired"],
                    "%Y-%m-%d"
                )

            except ValueError:

                messagebox.showerror(
                    "Error",
                    "Enter a valid daily rate and date (YYYY-MM-DD)."
                )
                return

            password = new_password.get()

            if not messagebox.askyesno(
                "Save Changes",
                f"Save changes for {values['name']}?"
            ):
                return

            conn = self.connect_database()
            cur = conn.cursor()

            try:

                cur.execute("""
                    UPDATE employees
                    SET name = ?, position = ?, department = ?,
                        dailyrate = ?, email = ?, phone = ?,
                        address = ?, date_hired = ?, username = ?
                    WHERE id = ?
                """, (
                    values["name"],
                    values["position"],
                    values["department"],
                    daily_rate,
                    values["email"],
                    values["phone"],
                    values["address"],
                    values["date_hired"],
                    values["username"],
                    employee_id
                ))

                if password:

                    cur.execute(
                        "UPDATE employees SET password_hash = ? "
                        "WHERE id = ?",
                        (self.hash_password(password), employee_id)
                    )

                conn.commit()

            except sqlite3.IntegrityError:

                conn.rollback()
                conn.close()

                messagebox.showerror(
                    "Error",
                    "Username already exists."
                )
                return

            conn.close()

            messagebox.showinfo(
                "Success",
                "Employee updated successfully!"
            )

            self.employee_info_page()

        Frame(content, bg=BG, height=10).pack()

        self.button(content, "Save Changes", save)
        self.button(
            content, "Cancel", self.employee_info_page, "secondary"
        )

    def calculate_payroll_page(self):

        content = self.new_page("CALCULATE PAYROLL")

        self.note(
            content,
            "Days worked come from unpaid attendance records "
            "(with a time out)."
        )

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

        employees = cur.fetchall()

        conn.close()

        if not employees:
            self.note(content, "No employees yet.")

        for employee_id, name, daily_rate, unpaid in employees:

            card = self.card(content, name)

            self.row(card, "Daily Rate", f"₱{daily_rate:,.2f}")
            self.row(card, "Unpaid Days", unpaid, bold=True)

            Button(
                card,
                text="Calculate & Save",
                command=lambda i=employee_id, n=name, r=daily_rate:
                    self.calculate_payroll(i, n, r),
                font=self.font(0, True),
                bg=PRIMARY if unpaid else BORDER,
                fg="white" if unpaid else MUTED,
                relief=FLAT,
                bd=0,
                state=NORMAL if unpaid else DISABLED
            ).pack(
                fill=X,
                padx=12,
                pady=(8, 12),
                ipady=7 if self.mobile else 6
            )

        self.button(content, "Back", self.admin_page, "secondary")

    def calculate_payroll(self, employee_id, name, daily_rate):

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

        taxable_income = gross - sss - pagibig
        tax = self.compute_tax(taxable_income)

        net = round(gross - sss - pagibig - tax, 2)

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

    def payroll_records_page(self):

        content = self.new_page("PAYROLL RECORDS")

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

        if not records:
            self.note(content, "No payroll records yet.")

        for r in records:

            card = self.card(content, f"{r[0]}  •  {r[7]}")

            self.row(card, "Days Worked", r[1])
            self.row(card, "Gross Pay", f"₱{r[2]:,.2f}")
            self.row(card, "SSS", f"₱{r[3]:,.2f}")
            self.row(card, "Pag-IBIG", f"₱{r[4]:,.2f}")
            self.row(card, "Tax", f"₱{r[5]:,.2f}")
            self.row(card, "Net Pay", f"₱{r[6]:,.2f}", bold=True)

            self.end_card(card)

        self.button(content, "Back", self.admin_page, "secondary")


    def employee_login_page(self):

        content = self.new_page("EMPLOYEE LOGIN")

        username = self.field(content, "Username")
        password = self.field(content, "Password", show="*")

        Frame(content, bg=BG, height=10).pack()

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

        self.button(content, "Login", login)
        self.button(content, "Back", self.main_page, "secondary")

    def employee_dashboard(self, employee_id):

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

        content = self.new_page(f"WELCOME, {name.upper()}")

        card = self.card(content)

        Frame(card, bg=CARD, height=6).pack()

        self.row(card, "Position", position)
        self.row(card, "Department", department)
        self.row(card, "Email", email or "")
        self.row(card, "Phone", phone or "")
        self.row(card, "Address", address or "")
        self.row(card, "Date Hired", date_hired or "")
        self.row(card, "Daily Rate", f"₱{daily_rate:,.2f}")

        self.end_card(card)

        self.button(
            content,
            "My Attendance",
            lambda: self.employee_attendance_page(employee_id)
        )

        self.button(
            content,
            "My Payslips",
            lambda: self.employee_payslip_page(employee_id)
        )

        self.button(
            content,
            "My Payroll History",
            lambda: self.employee_payroll_page(employee_id)
        )

        self.button(content, "Logout", self.main_page, "secondary")

    def employee_attendance_page(self, employee_id):

        content = self.new_page("MY ATTENDANCE")

        today = datetime.now().strftime("%Y-%m-%d")

        conn = self.connect_database()
        cur = conn.cursor()

        cur.execute("""
            SELECT time_in, time_out, hours_worked
            FROM attendance
            WHERE employee_id = ? AND date = ?
        """, (employee_id, today))

        attendance = cur.fetchone()

        cur.execute("""
            SELECT date, time_in, time_out, hours_worked
            FROM attendance
            WHERE employee_id = ?
            ORDER BY date DESC
        """, (employee_id,))

        records = cur.fetchall()

        conn.close()

        card = self.card(content, f"Today: {today}")

        if attendance:

            self.row(card, "Time In", attendance[0] or "Not recorded")
            self.row(card, "Time Out", attendance[1] or "Not recorded")
            self.row(
                card, "Working Hours", f"{(attendance[2] or 0):.2f}"
            )

        else:

            self.row(card, "Status", "You have not timed in today.")

        self.end_card(card)

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

        self.button(content, "TIME IN", time_in)
        self.button(content, "TIME OUT", time_out, "danger")

        Label(
            content,
            text="ATTENDANCE HISTORY",
            font=self.font(1, True),
            bg=BG,
            fg=TEXT
        ).pack(pady=(18, 6))

        if not records:
            self.note(content, "No attendance yet.")

        for record in records:

            card = self.card(content, record[0])

            self.row(card, "Time In", record[1] or "")
            self.row(card, "Time Out", record[2] or "")
            self.row(card, "Working Hours", f"{(record[3] or 0):.2f}")

            self.end_card(card)

        self.button(
            content,
            "Back",
            lambda: self.employee_dashboard(employee_id),
            "secondary"
        )

    def employee_payslip_page(self, employee_id):

        content = self.new_page("MY PAYSLIPS")

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

        if not records:
            self.note(content, "No payslips yet.")

        for r in records:

            card = self.card(content, r[1])

            self.row(card, "Days Worked", r[2])
            self.row(card, "Gross Pay", f"₱{r[3]:,.2f}")
            self.row(card, "Net Pay", f"₱{r[7]:,.2f}", bold=True)

            Button(
                card,
                text="View Payslip",
                command=lambda pid=r[0]:
                    self.payslip_view_page(employee_id, pid),
                font=self.font(0, True),
                bg=PRIMARY,
                fg="white",
                relief=FLAT,
                bd=0
            ).pack(
                fill=X,
                padx=12,
                pady=(8, 12),
                ipady=7 if self.mobile else 6
            )

        self.button(
            content,
            "Back",
            lambda: self.employee_dashboard(employee_id),
            "secondary"
        )

    def payslip_view_page(self, employee_id, payroll_id):

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
            self.employee_payslip_page(employee_id)
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

        content = self.new_page("EMPLOYEE PAYSLIP")

        card = self.card(content)

        Frame(card, bg=CARD, height=6).pack()

        self.row(card, "Employee Name", name)
        self.row(card, "Position", position)
        self.row(card, "Department", department)
        self.row(card, "Payroll Date", date)
        self.row(card, "Daily Rate", f"₱{rate:,.2f}")
        self.row(card, "Days Worked", days)
        self.row(card, "Gross Pay", f"₱{gross:,.2f}")
        self.row(card, "SSS Contribution", f"₱{sss:,.2f}")
        self.row(card, "Pag-IBIG Contribution", f"₱{pagibig:,.2f}")
        self.row(card, "Withholding Tax", f"₱{tax:,.2f}")

        Frame(card, bg=BORDER, height=1).pack(fill=X, padx=12, pady=6)

        self.row(card, "NET PAY", f"₱{net:,.2f}", bold=True)

        self.end_card(card)

        self.button(
            content,
            "Back",
            lambda: self.employee_payslip_page(employee_id),
            "secondary"
        )

    def employee_payroll_page(self, employee_id):

        content = self.new_page("MY PAYROLL HISTORY")

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

        if not records:
            self.note(content, "No payroll history yet.")

        for r in records:

            card = self.card(content, r[0])

            self.row(card, "Days Worked", r[1])
            self.row(card, "Gross Pay", f"₱{r[2]:,.2f}")
            self.row(card, "SSS", f"₱{r[3]:,.2f}")
            self.row(card, "Pag-IBIG", f"₱{r[4]:,.2f}")
            self.row(card, "Tax", f"₱{r[5]:,.2f}")
            self.row(card, "Net Pay", f"₱{r[6]:,.2f}", bold=True)

            self.end_card(card)

        self.button(
            content,
            "Back",
            lambda: self.employee_dashboard(employee_id),
            "secondary"
        )

    def run(self):

        self.main_page()
        self.root.mainloop()


if __name__ == "__main__":

    app = PayrollSystem()
    app.run()
