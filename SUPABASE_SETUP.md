# ⚙️ Supabase Setup Instructions

## Step 1: Create Tables in Supabase

1. Go to **Supabase Dashboard** → **SQL Editor**
2. Create a **new query** 
3. Copy and paste **entire content** from `backend/setup.sql`
4. Click **Run**

Expected: All 7 tables created successfully:
- ✓ students
- ✓ jobs
- ✓ applications
- ✓ skills_graph
- ✓ learning_resources
- ✓ upskilling_plans

---

## Step 2: Create Storage Bucket

1. Go to **Supabase Dashboard** → **Storage**
2. Click **New Bucket**
3. Name: `resumes`
4. Privacy: **Private** (if you want access control)
5. Click **Create**

Expected: A new `resumes` bucket appears in the storage list

---

## Step 3: Enable RLS (Row Level Security) - Optional

1. Go to **SQL Editor**
2. Run this query to disable RLS for development (NOT for production):

```sql
ALTER TABLE students DISABLE ROW LEVEL SECURITY;
ALTER TABLE jobs DISABLE ROW LEVEL SECURITY;
ALTER TABLE applications DISABLE ROW LEVEL SECURITY;
ALTER TABLE skills_graph DISABLE ROW LEVEL SECURITY;
ALTER TABLE learning_resources DISABLE ROW LEVEL SECURITY;
ALTER TABLE upskilling_plans DISABLE ROW LEVEL SECURITY;
```

---

## Step 4: Verify Setup

Go to **Table Editor** and confirm you see all tables:
- students (empty)
- jobs (empty)
- applications (empty)
- skills_graph (empty)
- learning_resources (empty)
- upskilling_plans (empty)

---

## Step 5: Run Seed Script

Once tables are created, run from `backend/`:

```bash
python scripts/seed_db.py
```

Expected output:
```
✓ Students seeded
✓ Jobs seeded
✓ skills_graph seeded
✓ learning_resources seeded
✓ 50 dummy resumes uploaded
✅ Seeding complete!
```

---

## Troubleshooting

### "Invalid API key" error
- Double-check `backend/.env` has **correct** SUPABASE_SERVICE_KEY
- Keys should look like: `abc123def456...==` (base64, no JWT appended)
- Never use ANON_KEY for backend operations

### "Table does not exist"
- You haven't run the SQL from `setup.sql` yet
- Go to SQL Editor and run all queries

### "Storage bucket not found"
- Create `resumes` bucket in Storage section
- Make sure it's `private` for security

### Seed script runs but inserts nothing
- Check the .xlsx files have correct column names
- Open `datasets/students.xlsx` and verify headers match seed script expectations

---

✅ Once all steps complete, proceed to run backend + frontend!
