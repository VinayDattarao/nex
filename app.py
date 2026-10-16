from datetime import date, timedelta
from flask import Flask, render_template, session, jsonify, request, redirect, url_for, flash
import re
import os
import random
import time
from dotenv import load_dotenv

import data

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
APP_EMAIL = os.getenv("APP_EMAIL", "solonerd4@gmail.com")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

RESET_OTPS = {}

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "nexora-secure-session-secret-key-2026")


def current_user():
    user_id = session.get("user_id")
    if user_id:
        return data.get_user_by_id(user_id)
    return None


def current_role():
    user = current_user()
    if user:
        return user.get("role", "guest")
    return "guest"


@app.context_processor
def inject_globals():
    user = current_user()
    role = current_role()
    if user and user.get("role") == "seeker":
        saved_count = len(user.get("saved_job_ids", set()))
    else:
        saved_count = len(data.SEEKER_SAVED_JOB_IDS)
    return {
        "current_user": user,
        "demo_role": role,
        "saved_count": saved_count,
    }


# ---------------------------------------------------------------- AUTH --
@app.route("/login", methods=["GET", "POST"])
def login():
    redirect_url = request.args.get("redirect") or request.form.get("redirect") or ""
    msg = request.args.get("msg") or ""

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""

        if not email or not password:
            return render_template("login.html", error="Please provide both email and password.",
                                   email=email, redirect_url=redirect_url, msg=msg), 400

        user = data.authenticate_user(email, password)
        if not user:
            return render_template("login.html", error="Invalid email or password. Please try again.",
                                   email=email, redirect_url=redirect_url, msg=msg), 401

        # Establish session
        session["user_id"] = user["id"]
        session["demo_role"] = user["role"]
        session["user_name"] = user["name"]

        # Sync demo data structures for legacy views
        if user["role"] == "employer":
            data.EMPLOYER["company"] = user["company"]
            data.EMPLOYER["initials"] = user["initials"]
            data.EMPLOYER["color"] = user["color"]
            data.EMPLOYER["jobs_posted_ids"] = user["jobs_posted_ids"]
        elif user["role"] == "seeker":
            data.SEEKER["name"] = user["name"]
            data.SEEKER["title"] = user.get("title", "Job Seeker")
            data.SEEKER["location"] = user.get("location", "Melbourne, VIC")
            data.SEEKER["skills"] = user.get("skills", ["JavaScript", "React", "CSS", "Figma"])

        if redirect_url and redirect_url.startswith("/") and not redirect_url.startswith("//"):
            return redirect(redirect_url)

        if user["role"] == "employer":
            return redirect(url_for("employer_dashboard"))
        elif user["role"] == "seeker":
            return redirect(url_for("seeker_dashboard"))
        return redirect(url_for("index"))

    return render_template("login.html", redirect_url=redirect_url, msg=msg)


@app.route("/register", methods=["GET", "POST"])
def register():
    redirect_url = request.args.get("redirect") or request.form.get("redirect") or ""
    msg = request.args.get("msg") or ""
    role = request.args.get("role") or "seeker"

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        role = (request.form.get("role") or "seeker").strip()
        company = (request.form.get("company") or "").strip()
        location = (request.form.get("location") or data.LOCATIONS[0]).strip()

        # Validation
        if not name or not email or not password:
            return render_template("register.html", error="Please complete all required fields.",
                                   name=name, email=email, role=role, company=company,
                                   location=location, redirect_url=redirect_url, msg=msg), 400

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return render_template("register.html", error="Please enter a valid email address.",
                                   name=name, email=email, role=role, company=company,
                                   location=location, redirect_url=redirect_url, msg=msg), 400

        if len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters long.",
                                   name=name, email=email, role=role, company=company,
                                   location=location, redirect_url=redirect_url, msg=msg), 400

        if role == "employer" and not company:
            return render_template("register.html", error="Company name is required for employer registration.",
                                   name=name, email=email, role=role, company=company,
                                   location=location, redirect_url=redirect_url, msg=msg), 400

        user, err = data.create_user(name=name, email=email, password=password,
                                     role=role, company=company, location=location)
        if err:
            return render_template("register.html", error=err,
                                   name=name, email=email, role=role, company=company,
                                   location=location, redirect_url=redirect_url, msg=msg), 400

        # Log user in directly
        session["user_id"] = user["id"]
        session["demo_role"] = user["role"]
        session["user_name"] = user["name"]

        if user["role"] == "employer":
            data.EMPLOYER["company"] = user["company"]
            data.EMPLOYER["initials"] = user["initials"]
            data.EMPLOYER["color"] = user["color"]
            data.EMPLOYER["jobs_posted_ids"] = user["jobs_posted_ids"]
        elif user["role"] == "seeker":
            data.SEEKER["name"] = user["name"]
            data.SEEKER["title"] = user.get("title", "Job Seeker")
            data.SEEKER["location"] = user.get("location", location)

        if redirect_url and redirect_url.startswith("/") and not redirect_url.startswith("//"):
            return redirect(redirect_url)

        if role == "employer":
            return redirect(url_for("employer_dashboard"))
        return redirect(url_for("seeker_dashboard"))

    return render_template("register.html", redirect_url=redirect_url, msg=msg, role=role,
                           locations=data.LOCATIONS)


@app.route("/logout")
def logout():
    session.clear()
    session["demo_role"] = "guest"
    return redirect(url_for("index"))


# -------------------------------------------------------- GOOGLE OAUTH --
@app.route("/auth/google")
def auth_google():
    role = request.args.get("role") or "seeker"
    redirect_url = request.args.get("redirect") or ""
    session["oauth_role"] = role
    session["oauth_redirect"] = redirect_url

    if SUPABASE_URL:
        callback_url = request.host_url.rstrip("/") + url_for("auth_callback")
        auth_url = f"{SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to={callback_url}"
        return redirect(auth_url)

    # Local fallback for tests/offline
    return redirect(url_for("auth_callback", demo_email="alex.chen.nexora@gmail.com", demo_name="Alex Chen"))


@app.route("/auth/callback")
def auth_callback():
    return render_template("auth_callback.html",
                           supabase_url=SUPABASE_URL,
                           supabase_anon_key=SUPABASE_ANON_KEY)


@app.post("/api/auth/google-callback")
def api_auth_google_callback():
    payload = request.json or {}
    email = payload.get("email")
    name = payload.get("name")
    avatar = payload.get("avatar")

    if not email:
        return jsonify({"ok": False, "message": "Email is required"}), 400

    role = session.get("oauth_role") or "seeker"
    redirect_url = session.get("oauth_redirect") or ""

    user = data.find_or_create_google_user(email=email, name=name, avatar=avatar, role=role)
    if not user:
        return jsonify({"ok": False, "message": "Failed to create or find user account."}), 500

    session["user_id"] = user["id"]
    session["demo_role"] = user["role"]
    session["user_name"] = user["name"]

    if user["role"] == "employer":
        data.EMPLOYER["company"] = user["company"]
        data.EMPLOYER["initials"] = user["initials"]
        data.EMPLOYER["color"] = user["color"]
        data.EMPLOYER["jobs_posted_ids"] = user["jobs_posted_ids"]
        target = redirect_url if (redirect_url and redirect_url.startswith("/") and not redirect_url.startswith("//")) else url_for("employer_dashboard")
    else:
        data.SEEKER["name"] = user["name"]
        data.SEEKER["title"] = user.get("title", "Job Seeker")
        target = redirect_url if (redirect_url and redirect_url.startswith("/") and not redirect_url.startswith("//")) else url_for("seeker_dashboard")

    return jsonify({"ok": True, "redirect": target, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}})



# ----------------------------------------------- SMS FORGOT PASSWORD --
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        identifier = (request.form.get("identifier") or "").strip()
        if not identifier:
            return render_template("forgot_password.html", error="Please enter your mobile phone number or email address."), 400

        otp_code = str(random.randint(100000, 999999))
        ident_key = identifier.lower().replace(" ", "").replace("-", "")

        RESET_OTPS[ident_key] = {
            "code": otp_code,
            "expires": time.time() + 600,
            "identifier": identifier,
        }

        session["reset_identifier"] = identifier
        session["last_otp_code"] = otp_code
        session["otp_verified"] = False

        print(f"[NEXORA SMS GATEWAY] Dispatched verification code '{otp_code}' to {identifier}")
        return redirect(url_for("verify_otp"))

    return render_template("forgot_password.html")


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    identifier = session.get("reset_identifier")
    if not identifier:
        return redirect(url_for("forgot_password"))

    ident_key = identifier.lower().replace(" ", "").replace("-", "")
    stored_entry = RESET_OTPS.get(ident_key)
    demo_otp = stored_entry["code"] if stored_entry else session.get("last_otp_code", "123456")

    if request.method == "POST":
        submitted_otp = (request.form.get("otp") or "").strip()
        if not submitted_otp:
            return render_template("verify_otp.html", identifier=identifier, demo_otp=demo_otp,
                                   error="Please enter the 6-digit code received via SMS."), 400

        is_valid = False
        if stored_entry and stored_entry["code"] == submitted_otp:
            if time.time() <= stored_entry["expires"]:
                is_valid = True
            else:
                return render_template("verify_otp.html", identifier=identifier, demo_otp=demo_otp,
                                       error="This verification code has expired. Please request a new one."), 400
        elif session.get("last_otp_code") == submitted_otp:
            is_valid = True

        if not is_valid:
            return render_template("verify_otp.html", identifier=identifier, demo_otp=demo_otp,
                                   error="Invalid verification code. Please check the SMS and try again."), 400

        session["otp_verified"] = True
        return redirect(url_for("reset_password"))

    resent = request.args.get("resent") == "true"
    return render_template("verify_otp.html", identifier=identifier, demo_otp=demo_otp, resent=resent)


@app.post("/resend-otp")
def resend_otp():
    identifier = session.get("reset_identifier")
    if not identifier:
        return redirect(url_for("forgot_password"))

    otp_code = str(random.randint(100000, 999999))
    ident_key = identifier.lower().replace(" ", "").replace("-", "")
    RESET_OTPS[ident_key] = {
        "code": otp_code,
        "expires": time.time() + 600,
        "identifier": identifier,
    }
    session["last_otp_code"] = otp_code
    print(f"[NEXORA SMS GATEWAY] Resent SMS code '{otp_code}' to {identifier}")
    return redirect(url_for("verify_otp", resent="true"))


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if not session.get("otp_verified") or not session.get("reset_identifier"):
        return redirect(url_for("forgot_password"))

    identifier = session.get("reset_identifier")

    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        if not password or len(password) < 6:
            return render_template("reset_password.html", identifier=identifier,
                                   error="Password must be at least 6 characters long."), 400

        if password != confirm:
            return render_template("reset_password.html", identifier=identifier,
                                   error="Passwords do not match. Please ensure both fields are identical."), 400

        data.reset_user_password(identifier, password)

        session.pop("otp_verified", None)
        session.pop("reset_identifier", None)
        session.pop("last_otp_code", None)

        return redirect(url_for("login", msg="password_reset_success"))

    return render_template("reset_password.html", identifier=identifier)


# ---------------------------------------------------------------- pages --
@app.route("/")
def index():
    featured_jobs = [j for j in data.JOBS if j["status"] == "Approved" and j["featured"]][:6]
    categories = {}
    for j in data.JOBS:
        categories.setdefault(j["industry"], 0)
        categories[j["industry"]] += 1
    return render_template("index.html", featured_jobs=featured_jobs, categories=categories,
                            salary_label=data.salary_label, packages=data.PACKAGES)


@app.route("/jobs")
def jobs():
    live_jobs = [j for j in data.JOBS if j["status"] == "Approved"]
    user = current_user()
    saved_ids = list(user.get("saved_job_ids", set())) if (user and "saved_job_ids" in user) else list(data.SEEKER_SAVED_JOB_IDS)
    return render_template(
        "jobs.html",
        jobs_json=live_jobs,
        saved_ids=saved_ids,
        locations=data.LOCATIONS,
        industries=data.INDUSTRIES,
        job_types=data.JOB_TYPES,
        work_modes=data.WORK_MODES,
        experience_levels=data.EXPERIENCE_LEVELS,
        salary_label=data.salary_label,
    )


TOP_COMPANIES = [
    {"slug": "northlane-digital", "name": "Northlane Digital", "initials": "ND", "color": "#5D4FE0",
     "industry": "Technology", "location": "Melbourne, VIC", "employees": "250-500",
     "about": "A product engineering studio building web and mobile platforms for Australian brands."},
    {"slug": "harbourfield-health", "name": "Harbourfield Health", "initials": "HH", "color": "#2DD9B8",
     "industry": "Healthcare", "location": "Brisbane, QLD", "employees": "1,000+",
     "about": "A leading healthcare network delivering compassionate, community-focused patient care."},
    {"slug": "ferro-cole-construction", "name": "Ferro & Cole Construction", "initials": "FC", "color": "#0B1230",
     "industry": "Construction", "location": "Perth, WA", "employees": "500-1,000",
     "about": "Commercial and civil construction specialists delivering landmark projects nationwide."},
    {"slug": "bright-retail-co", "name": "Bright Retail Co.", "initials": "BR", "color": "#E0975D",
     "industry": "Retail", "location": "Adelaide, SA", "employees": "100-250",
     "about": "A fast-growing retail group with stores and online experiences across Australia."},
]


@app.route("/companies")
def companies():
    items = []
    for c in TOP_COMPANIES:
        count = sum(1 for j in data.JOBS if j["status"] == "Approved" and j["company"] == c["name"])
        items.append({**c, "open_roles": count})
    return render_template("companies.html", companies=items)


@app.route("/companies/<slug>")
def company_jobs(slug):
    company = next((c for c in TOP_COMPANIES if c["slug"] == slug), None)
    if not company:
        return render_template("404.html"), 404
    posted = [j for j in data.JOBS if j["status"] == "Approved" and j["company"] == company["name"]]
    return render_template("company_jobs.html", company=company, jobs=posted, salary_label=data.salary_label)


@app.route("/jobs/<int:job_id>")
def job_details(job_id):
    job = data.get_job(job_id)
    if not job:
        return render_template("404.html"), 404

    user = current_user()
    if user and user.get("role") == "seeker":
        is_saved = job_id in user.get("saved_job_ids", set())
        has_applied = any(a["job_id"] == job_id for a in user.get("applications", []))
        seeker_profile = user
    else:
        is_saved = job_id in data.SEEKER_SAVED_JOB_IDS
        has_applied = any(a["job_id"] == job_id for a in data.SEEKER_APPLICATIONS)
        seeker_profile = data.SEEKER

    similar = [j for j in data.JOBS if j["industry"] == job["industry"] and j["id"] != job_id][:3]
    return render_template("job_details.html", job=job, is_saved=is_saved, has_applied=has_applied,
                            similar=similar, seeker=seeker_profile, salary_label=data.salary_label)


@app.route("/dashboard/seeker")
def seeker_dashboard():
    # Role protection: redirect guests to login with specific oops message
    role = current_role()
    if role != "seeker":
        return redirect(url_for("login", msg="not_logged_in", redirect="/dashboard/seeker"))

    user = current_user()
    if user and "applications" in user:
        raw_apps = user["applications"]
        saved_ids = user.get("saved_job_ids", set())
        seeker_profile = user
    else:
        raw_apps = data.SEEKER_APPLICATIONS
        saved_ids = data.SEEKER_SAVED_JOB_IDS
        seeker_profile = data.SEEKER

    apps = []
    applied_job_ids = set()
    for a in raw_apps:
        job = data.get_job(a["job_id"])
        if job:
            apps.append({**a, "job": job})
            applied_job_ids.add(a["job_id"])

    saved = [data.get_job(jid) for jid in saved_ids if data.get_job(jid)]
    recommended = [j for j in data.JOBS
                   if j["status"] == "Approved"
                   and any(t in seeker_profile.get("skills", []) for t in j["tags"])
                   and j["id"] not in applied_job_ids][:3]
    for i, j in enumerate(recommended):
        j["_match"] = 92 - i * 6

    pipeline_counts = {s: sum(1 for a in apps if a["stage"] == s) for s in data.APPLICATION_STAGES}

    # Available jobs for instant browsing & direct application from User Dashboard
    all_live_jobs = [j for j in data.JOBS if j["status"] == "Approved"]

    return render_template("seeker_dashboard.html", seeker=seeker_profile, applications=apps,
                            saved=saved, recommended=recommended, stages=data.APPLICATION_STAGES,
                            pipeline_counts=pipeline_counts, salary_label=data.salary_label,
                            all_jobs=all_live_jobs, applied_job_ids=list(applied_job_ids))


@app.route("/dashboard/employer")
def employer_dashboard():
    # Role protection: redirect guests to register with employer details notice
    role = current_role()
    if role != "employer":
        return redirect(url_for("register", role="employer", msg="need_details", redirect="/dashboard/employer"))

    user = current_user()
    employer_obj = user if (user and user.get("role") == "employer") else data.EMPLOYER
    company_name = employer_obj.get("company", "Northlane Digital")
    jobs_posted_ids = employer_obj.get("jobs_posted_ids", [])

    # Retrieve all jobs belonging to this employer
    my_jobs = [j for j in data.JOBS if j["company"] == company_name or j["id"] in jobs_posted_ids]
    total_views = sum(j["views"] for j in my_jobs)
    total_apps = sum(j["applications_count"] for j in my_jobs)

    # Filter applicants for this employer's jobs
    my_job_ids = set(j["id"] for j in my_jobs)
    employer_candidates = [c for c in data.CANDIDATES if c.get("job_id") in my_job_ids]
    if not employer_candidates and company_name == "Northlane Digital":
        employer_candidates = data.CANDIDATES

    shortlisted = sum(1 for c in employer_candidates if c["stage"] in ("Shortlisted", "Interview", "Hired"))
    recent_applicants = sorted(employer_candidates, key=lambda c: c["applied_date"], reverse=True)[:5]

    return render_template("employer_dashboard.html", employer=employer_obj, my_jobs=my_jobs,
                            total_views=total_views, total_apps=total_apps, shortlisted=shortlisted,
                            recent_applicants=recent_applicants, salary_label=data.salary_label,
                            locations=data.LOCATIONS, industries=data.INDUSTRIES,
                            job_types=data.JOB_TYPES, work_modes=data.WORK_MODES,
                            experience_levels=data.EXPERIENCE_LEVELS)


@app.route("/post-job")
def post_job():
    # Require employer role; redirect if not registered/logged in as employer
    role = current_role()
    if role != "employer":
        return redirect(url_for("register", role="employer", msg="need_details", redirect="/post-job"))

    return render_template("post_job.html", industries=data.INDUSTRIES, job_types=data.JOB_TYPES,
                            work_modes=data.WORK_MODES, experience_levels=data.EXPERIENCE_LEVELS,
                            locations=data.LOCATIONS)


@app.route("/pricing")
def pricing():
    return render_template("pricing.html", packages=data.PACKAGES)


@app.route("/checkout")
def checkout():
    role = current_role()
    if role != "employer":
        return redirect(url_for("register", role="employer", msg="need_details", redirect=request.full_path))

    package_id = request.args.get("package", "featured")
    package = next((p for p in data.PACKAGES if p["id"] == package_id), data.PACKAGES[1])
    return render_template("checkout.html", package=package, draft=data.DRAFT_JOB)


@app.route("/applicants")
def applicants():
    role = current_role()
    if role != "employer":
        return redirect(url_for("register", role="employer", msg="need_details", redirect="/applicants"))

    user = current_user()
    employer_obj = user if (user and user.get("role") == "employer") else data.EMPLOYER
    company_name = employer_obj.get("company", "Northlane Digital")
    my_jobs = [j for j in data.JOBS if j["company"] == company_name or j["id"] in employer_obj.get("jobs_posted_ids", [])]
    my_job_ids = set(j["id"] for j in my_jobs)

    employer_candidates = [c for c in data.CANDIDATES if c.get("job_id") in my_job_ids]
    if not employer_candidates and company_name == "Northlane Digital":
        employer_candidates = data.CANDIDATES

    grouped = {s: [c for c in employer_candidates if c["stage"] == s] for s in data.STAGES}
    return render_template("applicants.html", grouped=grouped, stages=data.STAGES)


@app.route("/admin")
def admin():
    live_jobs = [j for j in data.JOBS if j["status"] == "Approved"]
    pending_jobs = [j for j in data.JOBS if j["status"] == "Pending"]
    rejected_jobs = [j for j in data.JOBS if j["status"] == "Rejected"]
    revenue = data.PLATFORM_STATS["revenue_month"]
    return render_template("admin.html", stats=data.PLATFORM_STATS, live_jobs=live_jobs,
                            pending_jobs=pending_jobs, rejected_jobs=rejected_jobs,
                            all_jobs=data.JOBS, reports=data.ADMIN_REPORTS, revenue=revenue)


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# --------------------------------------------------------------- API ----
@app.post("/api/demo-role")
def api_demo_role():
    role = request.json.get("role", "guest")
    session["demo_role"] = role
    if role == "seeker":
        session["user_id"] = 1
    elif role == "employer":
        session["user_id"] = 2
    elif role == "guest":
        session.pop("user_id", None)
    return jsonify({"ok": True, "role": role})


@app.post("/api/jobs/<int:job_id>/save")
def api_toggle_save(job_id):
    user = current_user()
    if user and user.get("role") == "seeker":
        saved_set = user.setdefault("saved_job_ids", set())
        if job_id in saved_set:
            saved_set.discard(job_id)
            saved = False
        else:
            saved_set.add(job_id)
            saved = True
        return jsonify({"ok": True, "saved": saved, "saved_count": len(saved_set)})

    if job_id in data.SEEKER_SAVED_JOB_IDS:
        data.SEEKER_SAVED_JOB_IDS.discard(job_id)
        saved = False
    else:
        data.SEEKER_SAVED_JOB_IDS.add(job_id)
        saved = True
    return jsonify({"ok": True, "saved": saved, "saved_count": len(data.SEEKER_SAVED_JOB_IDS)})


@app.post("/api/jobs/<int:job_id>/apply")
def api_apply(job_id):
    role = current_role()
    if role != "seeker":
        # Unauthenticated: return oops response and redirect destination
        return jsonify({
            "ok": False,
            "requires_auth": True,
            "message": "Oops! You are not logged in!",
            "redirect": url_for("login", msg="not_logged_in", redirect=f"/jobs/{job_id}"),
        }), 401

    user = current_user()
    applied_date = date.today().isoformat()
    seeker_name = user["name"] if user else data.SEEKER["name"]

    job = data.get_job(job_id)
    if not job:
        return jsonify({"ok": False, "message": "Job not found"}), 404

    # Record in user applications
    if user and "applications" in user:
        if not any(a["job_id"] == job_id for a in user["applications"]):
            user["applications"].append({
                "job_id": job_id, "stage": "Applied", "applied_date": applied_date,
            })
    if not any(a["job_id"] == job_id for a in data.SEEKER_APPLICATIONS):
        data.SEEKER_APPLICATIONS.append({
            "job_id": job_id, "stage": "Applied", "applied_date": applied_date,
        })

    job["applications_count"] = job.get("applications_count", 0) + 1

    # Connect to employer pipeline
    candidate_id = data.next_id()
    data.CANDIDATES.insert(0, {
        "id": candidate_id,
        "job_id": job["id"],
        "job_title": job["title"],
        "name": seeker_name,
        "title": f"Applicant for {job['title']}",
        "experience": job.get("experience", "1-3 years"),
        "skills": job.get("tags", []),
        "applied_date": applied_date,
        "stage": "New",
        "avatar_initials": "".join(p[0].upper() for p in seeker_name.split()[:2]) or "CD",
    })

    return jsonify({"ok": True, "message": "Application submitted successfully!"})


@app.post("/api/post-job")
def api_post_job():
    role = current_role()
    if role != "employer":
        return jsonify({
            "ok": False,
            "requires_auth": True,
            "message": "Oops! We need your details! Please register.",
            "redirect": url_for("register", role="employer", msg="need_details", redirect="/post-job")
        }), 401

    user = current_user()
    employer_obj = user if (user and user.get("role") == "employer") else data.EMPLOYER
    company_name = employer_obj.get("company", "Northlane Digital")
    company_initials = employer_obj.get("initials", "ND")
    company_color = employer_obj.get("color", "#5D4FE0")

    payload = request.json or {}
    job_id = data.next_id()
    job = {
        "id": job_id,
        "title": payload.get("title", "Untitled role"),
        "company": company_name,
        "company_initials": company_initials,
        "company_color": company_color,
        "location": payload.get("location", data.LOCATIONS[0]),
        "type": payload.get("type", data.JOB_TYPES[0]),
        "mode": payload.get("mode", data.WORK_MODES[0]),
        "experience": payload.get("experience", data.EXPERIENCE_LEVELS[0]),
        "industry": payload.get("industry", data.INDUSTRIES[0]),
        "salary_min": int(payload.get("salary_min") or 60000),
        "salary_max": int(payload.get("salary_max") or 90000),
        "tags": [t.strip() for t in payload.get("skills", "").split(",") if t.strip()][:6] or ["General"],
        "posted_days_ago": 0,
        "closing_date": payload.get("closing_date", (date.today() + timedelta(days=30)).isoformat()),
        "featured": False,
        "urgent": False,
        "status": "Approved",
        "views": 1,
        "applications_count": 0,
        "about_role": payload.get("description", "Description coming soon."),
        "responsibilities": ["Deliver against role objectives", "Work closely with the team"],
        "requirements": [f"Experience level: {payload.get('experience', 'Not specified')}"],
        "benefits": ["Flexible working arrangements", "Competitive compensation"],
        "about_company": f"{company_name} is hiring through NEXORA.",
    }
    data.JOBS.insert(0, job)

    if user and "jobs_posted_ids" in user:
        if job_id not in user["jobs_posted_ids"]:
            user["jobs_posted_ids"].append(job_id)
    if job_id not in data.EMPLOYER["jobs_posted_ids"]:
        data.EMPLOYER["jobs_posted_ids"].append(job_id)

    data.DRAFT_JOB.clear()
    data.DRAFT_JOB.update({"job_id": job["id"], "title": job["title"]})
    return jsonify({"ok": True, "job_id": job["id"]})


@app.post("/api/employer/jobs/<int:job_id>/edit")
def api_edit_job(job_id):
    role = current_role()
    if role != "employer":
        return jsonify({"ok": False, "message": "Unauthorized"}), 403

    payload = request.json or {}
    job = data.get_job(job_id)
    if not job:
        return jsonify({"ok": False, "message": "Job not found"}), 404

    # Update job fields
    job["title"] = payload.get("title", job["title"])
    job["location"] = payload.get("location", job["location"])
    job["type"] = payload.get("type", job["type"])
    job["mode"] = payload.get("mode", job["mode"])
    job["experience"] = payload.get("experience", job["experience"])
    job["industry"] = payload.get("industry", job["industry"])
    if "salary_min" in payload:
        try:
            job["salary_min"] = int(payload["salary_min"])
        except (ValueError, TypeError):
            pass
    if "salary_max" in payload:
        try:
            job["salary_max"] = int(payload["salary_max"])
        except (ValueError, TypeError):
            pass
    if "status" in payload:
        job["status"] = payload["status"]
    if "description" in payload:
        job["about_role"] = payload["description"]

    return jsonify({"ok": True, "job": job, "message": "Job updated successfully!"})


@app.post("/api/employer/jobs/<int:job_id>/status")
def api_toggle_job_status(job_id):
    role = current_role()
    if role != "employer":
        return jsonify({"ok": False, "message": "Unauthorized"}), 403

    payload = request.json or {}
    status = payload.get("status")
    job = data.get_job(job_id)
    if not job:
        return jsonify({"ok": False, "message": "Job not found"}), 404

    if status in ("Approved", "Draft", "Closed", "Pending"):
        job["status"] = status
        return jsonify({"ok": True, "status": status})
    return jsonify({"ok": False, "message": "Invalid status"}), 400


@app.post("/api/employer/jobs/<int:job_id>/delete")
def api_delete_job(job_id):
    role = current_role()
    if role != "employer":
        return jsonify({"ok": False, "message": "Unauthorized"}), 403

    success = data.delete_job(job_id)
    if success:
        return jsonify({"ok": True, "message": "Job deleted successfully."})
    return jsonify({"ok": False, "message": "Job not found"}), 404


@app.post("/api/checkout")
def api_checkout():
    payload = request.json or {}
    job_id = data.DRAFT_JOB.get("job_id")
    job = data.get_job(job_id) if job_id else None
    package_id = payload.get("package", "featured")
    if job:
        job["status"] = "Approved"
        job["featured"] = package_id in ("featured", "premium")
        job["urgent"] = package_id == "urgent"
        user = current_user()
        if user and "jobs_posted_ids" in user and job_id not in user["jobs_posted_ids"]:
            user["jobs_posted_ids"].append(job_id)
        if job_id not in data.EMPLOYER["jobs_posted_ids"]:
            data.EMPLOYER["jobs_posted_ids"].append(job_id)
    return jsonify({"ok": True, "job_id": job_id})


@app.post("/api/applicants/<int:candidate_id>/stage")
def api_move_stage(candidate_id):
    new_stage = (request.json or {}).get("stage")
    for c in data.CANDIDATES:
        if c["id"] == candidate_id and new_stage in data.STAGES:
            c["stage"] = new_stage
            return jsonify({"ok": True, "stage": new_stage})
    return jsonify({"ok": False}), 404


@app.post("/api/admin/jobs/<int:job_id>/moderate")
def api_moderate(job_id):
    action = (request.json or {}).get("action")
    job = data.get_job(job_id)
    if not job:
        return jsonify({"ok": False}), 404
    mapping = {"approve": "Approved", "reject": "Rejected", "review": "Review", "suspend": "Suspended"}
    if action in mapping:
        job["status"] = mapping[action]
        return jsonify({"ok": True, "status": job["status"]})
    return jsonify({"ok": False}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
