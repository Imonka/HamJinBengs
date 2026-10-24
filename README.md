# Gantian — Smart Leave & Shift-Cover Management System

## Team Information
* **Team Name:** HamJinBengs
* **Team Domain:** Domain 2
* **Pitch Video Link:** https://youtu.be/eitBOiF6nOQ
---

## Overall Project Structure & Overview

**Gantian** is a leave and shift-cover management system. It helps managers plan staff shifts and find replacements when an employee’s approved leave affects an upcoming shift. Staff can view their shifts, request leave, and respond to cover offers.

### Main Functions
1. **Sign-in and access control**
   Employees sign in with their work email and PIN. The system provides different screens and actions for managers and staff.

2. **Team and role management**
   Managers can manage employee and job-role information, including adding or importing staff.

3. **Shift scheduling**
   Managers configure shift patterns and scheduling rules, manage shifts, and generate weekly rosters. The system can also identify roster gaps.

4. **Leave management**
   Staff can submit leave requests through Orbyte eLeave, which managers can import onto the system. Managers can review requests, preview which shifts may need cover, then approve or reject them. When approved leave affects an upcoming shift, the system opens a cover case for it.

5. **Shift-cover offers**
   Managers can review eligible replacement candidates and send them offers. Staff can accept or decline offers. The first staff member to accept gets the shift; other outstanding offers expire.

6. **Dashboard and notifications**
   Managers can see cover cases, pending offers, leave requests, and scheduling activity. Staff receive in-app notifications and can view their inbox.

---

## How to Run the Project

You can run this project **either on Replit** or **locally on your own machine (Localhost)**.

### Option A: Run on Replit (Recommended for Quick Preview)
1. Import this repository (or upload the project zip) into **Replit**.
2. Provision a **Replit PostgreSQL** database (so `DATABASE\\\\\\\\\\\\\\\_URL` is automatically set in your environment).
3. Click the **Run** button, or open two Shell tabs:
   * **Backend Shell:**
     ```bash
     cd artifacts/api-server
     python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
     ```
   * **Frontend Shell:**
     ```bash
     cd artifacts/cover-scheduler
     pnpm exec vite --host 0.0.0.0 --port 5173
     ```

---

### Option B: Run on Localhost (Windows / macOS / Linux)

#### 1. Prerequisites
Ensure you have the following installed:
* **Python** 3.11+
* **Node.js** 20+
* **PostgreSQL** 14+ (running locally on port `5432`)

#### 2. Database Setup (One-Time Only)
Open **SQL Shell (psql)** or **pgAdmin** and run:
```sql



CREATE USER scheduler\\\\\\\\\\\\\\\_user WITH PASSWORD 'pass123456';



CREATE DATABASE cover\\\\\\\\\\\\\\\_scheduler OWNER scheduler\\\\\\\\\\\\\\\_user;



GRANT ALL PRIVILEGES ON DATABASE cover\\\\\\\\\\\\\\\_scheduler TO scheduler\\\\\\\\\\\\\\\_user;



```

#### 3. Install Dependencies (One-Time Only)
Open a terminal in the **project root folder**:

**Install Backend Dependencies:**
```bash



pip install -r artifacts/api-server/requirements.txt



```

**Install Frontend Dependencies (Windows PowerShell):**
```powershell



Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force



npm config delete optional



npm config delete omit



npx pnpm@9.15.4 install --force



```
*(For macOS/Linux, simply run: `npx pnpm@9.15.4 install --force`)*

#### 4. Start the Servers (Open 2 Terminal Windows)

**Terminal 1 — Start Backend (Port 8080):**
* **Windows (PowerShell):**
  ```powershell
  $env:DATABASE_URL="postgresql://scheduler_user:pass123456@localhost:5432/cover_scheduler"
  cd artifacts/api-server
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload --reload-dir app
  ```
* **macOS / Linux:**
  ```bash
  export DATABASE_URL="postgresql://scheduler_user:pass123456@localhost:5432/cover_scheduler"
  cd artifacts/api-server
  python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload --reload-dir app
  ```

**Terminal 2 — Start Frontend (Port 5173):**
* **Windows (PowerShell):**
  ```powershell
  cd artifacts/cover-scheduler
  $env:PORT="5173"
  $env:BASE_PATH="/"
  npx pnpm@9.15.4 exec vite --host 127.0.0.1 --port 5173
  ```
* **macOS / Linux:**
  ```bash
  cd artifacts/cover-scheduler
  export PORT="5173"
  export BASE_PATH="/"
  npx pnpm@9.15.4 exec vite --host 127.0.0.1 --port 5173
  ```

#### 5. Access the App & Demo Accounts
Open your browser and visit **[http://127.0.0.1:5173](http://127.0.0.1:5173)**
* **Manager Demo Account:** `farah@mamarich.my` / PIN: `1234`
* **Staff Demo Account:** `aisyah@mamarich.my` / PIN: `1111`

---

## How We Used Replit

We leveraged **Replit** throughout our entire development lifecycle:
1. **Rapid Prototyping & Code Generation:** We used Replit to translate our core domain ideas and scheduling rules into a structured full-stack monorepo architecture (FastAPI backend + React/Vite frontend + OpenAPI contract).
2. **Cloud Visualization & Live Testing:** By hosting and running the project on Replit, our team could immediately visualize the UI flows (Manager Desk vs. Staff Portal) and test end-to-end user journeys in real time.
3. **Interactive Debugging:** We utilized Replit's integrated environment, console logs, and database tools to debug API endpoints, refine our shift-cover constraint engine, and validate edge cases smoothly.
