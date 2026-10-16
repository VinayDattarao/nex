"""
Comprehensive test script for NEXORA:
- Home Page & AI Theme Design
- Explore Plans Section
- Login & Register Authentication Flow
- Role-based Access & Guards
- Job Application Pipeline (Seeker & Employer)
- Employer Dashboard: Post, View, Edit, Manage Jobs
- 'Oops! You are not logged in!' and 'Oops! We need your details! Please register.'
"""
import unittest
from app import app
import data

class NexoraWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_01_homepage_content_and_ai_design(self):
        """Test home page renders with AI theme, Explore Plans, and role-guarded CTAs."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        
        # 1. AI Visual Image presence
        self.assertIn('ai_career_matching.jpg', html)
        self.assertIn('AI Neural Match', html)
        self.assertIn('AI Career Intelligence', html)
        
        # 2. Explore Plans section
        self.assertIn('explore-plans', html)
        self.assertIn('Employer Subscription &amp; Advertising Plans', html)
        self.assertIn('Basic', html)
        self.assertIn('Featured', html)
        self.assertIn('Urgent', html)
        self.assertIn('Premium', html)
        self.assertIn('Karthika will share the final plan details', html)
        
        # 3. Post a Job guarded link for unauthenticated visitors
        self.assertIn('msg=need_details', html)
        self.assertIn('role=employer', html)

    def test_02_login_page_and_unauthenticated_apply_alert(self):
        """Test login page and 'Oops! You are not logged in!' banner."""
        # Standard GET
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Welcome back', res.data.decode('utf-8'))
        
        # With not_logged_in query param
        res_alert = self.client.get('/login?msg=not_logged_in&redirect=/jobs/1002')
        html_alert = res_alert.data.decode('utf-8')
        self.assertIn('Oops! You are not logged in!', html_alert)
        self.assertIn('Create an account here', html_alert)

    def test_03_register_page_and_employer_details_alert(self):
        """Test register page and 'Oops! We need your details! Please register.' banner."""
        res = self.client.get('/register?role=employer&msg=need_details')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Oops! We need your details! Please register.', html)
        self.assertIn('Log in here', html)
        self.assertIn('Company Name', html)

    def test_04_seeker_login_and_user_dashboard(self):
        """Test job seeker authentication and dashboard access."""
        # Login with seed seeker account
        res = self.client.post('/login', data={
            'email': 'jordan@nexora.com',
            'password': 'password123',
            'redirect': ''
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Welcome back, Jordan', html)
        self.assertIn('Your application pipeline', html)
        self.assertIn('Browse &amp; Apply for Open Roles', html)

    def test_05_employer_login_and_employer_dashboard(self):
        """Test employer authentication and dashboard access."""
        with self.client.session_transaction() as sess:
            sess.clear()
            
        res = self.client.post('/login', data={
            'email': 'hiring@northlane.com',
            'password': 'password123',
            'redirect': ''
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Northlane Digital', html)
        self.assertIn('Job performance &amp; management', html)
        self.assertIn('Post a Job', html)

    def test_06_unauthenticated_apply_api_guard(self):
        """Test that unauthenticated apply returns 401 with 'Oops! You are not logged in!' and redirect."""
        with self.client.session_transaction() as sess:
            sess.clear()
            sess['demo_role'] = 'guest'
            
        res = self.client.post('/api/jobs/1000/apply')
        self.assertEqual(res.status_code, 401)
        data_res = res.get_json()
        self.assertFalse(data_res['ok'])
        self.assertTrue(data_res['requires_auth'])
        self.assertIn('Oops! You are not logged in!', data_res['message'])
        self.assertIn('/login?msg=not_logged_in', data_res['redirect'])

    def test_07_seeker_apply_api_flow(self):
        """Test seeker successfully applying to job and connecting to employer candidates."""
        # Login as seeker
        self.client.post('/login', data={'email': 'jordan@nexora.com', 'password': 'password123'})
        
        target_job = data.JOBS[0]
        initial_apps = target_job.get('applications_count', 0)
        
        res = self.client.post(f'/api/jobs/{target_job["id"]}/apply')
        self.assertEqual(res.status_code, 200)
        data_res = res.get_json()
        self.assertTrue(data_res['ok'])
        
        # Verify job application count incremented
        self.assertEqual(target_job['applications_count'], initial_apps + 1)
        
        # Verify candidate added to employer candidates list
        new_applicant = next((c for c in data.CANDIDATES if c['job_id'] == target_job['id'] and c['name'] == 'Jordan Reyes'), None)
        self.assertIsNotNone(new_applicant)
        self.assertEqual(new_applicant['stage'], 'New')

    def test_08_employer_post_edit_manage_delete_job(self):
        """Test complete employer job posting, viewing, editing, status change, and deletion."""
        # Login as employer
        self.client.post('/login', data={'email': 'hiring@northlane.com', 'password': 'password123'})
        
        # 1. Post job
        post_res = self.client.post('/api/post-job', json={
            'title': 'Lead AI Systems Engineer',
            'location': 'Sydney, NSW',
            'type': 'Full-time',
            'mode': 'Hybrid',
            'experience': '5+ years',
            'industry': 'Technology',
            'salary_min': 140000,
            'salary_max': 180000,
            'skills': 'PyTorch, Python, LLMs',
            'description': 'Lead our next-generation AI hiring agents project.'
        })
        self.assertEqual(post_res.status_code, 200)
        created_job_id = post_res.get_json()['job_id']
        self.assertIsNotNone(created_job_id)
        
        # Verify job is in data and belongs to employer
        job = data.get_job(created_job_id)
        self.assertIsNotNone(job)
        self.assertEqual(job['title'], 'Lead AI Systems Engineer')
        self.assertEqual(job['company'], 'Northlane Digital')
        
        # 2. Edit job
        edit_res = self.client.post(f'/api/employer/jobs/{created_job_id}/edit', json={
            'title': 'Principal AI Systems Architect',
            'salary_min': 160000,
            'salary_max': 210000,
            'mode': 'Remote'
        })
        self.assertEqual(edit_res.status_code, 200)
        self.assertEqual(job['title'], 'Principal AI Systems Architect')
        self.assertEqual(job['salary_min'], 160000)
        self.assertEqual(job['mode'], 'Remote')
        
        # 3. Change status (manage job)
        status_res = self.client.post(f'/api/employer/jobs/{created_job_id}/status', json={'status': 'Closed'})
        self.assertEqual(status_res.status_code, 200)
        self.assertEqual(job['status'], 'Closed')
        
        # 4. Delete job
        del_res = self.client.post(f'/api/employer/jobs/{created_job_id}/delete')
        self.assertEqual(del_res.status_code, 200)
        self.assertIsNone(data.get_job(created_job_id))

    def test_09_registration_new_user_flow(self):
        """Test registration of a new job seeker and employer with automatic redirection."""
        import random
        rnd = random.randint(1000, 9999)
        
        # Register new seeker
        seeker_email = f"newseeker{rnd}@example.com"
        res_seeker = self.client.post('/register', data={
            'name': 'Priya Sharma',
            'email': seeker_email,
            'password': 'secretpassword',
            'role': 'seeker',
            'location': 'Sydney, NSW'
        }, follow_redirects=False)
        self.assertEqual(res_seeker.status_code, 302)
        self.assertIn('/dashboard/seeker', res_seeker.headers['Location'])
        
        # Register new employer
        emp_email = f"emp{rnd}@techventures.com"
        res_emp = self.client.post('/register', data={
            'name': 'Rohan Gupta',
            'email': emp_email,
            'password': 'secretpassword',
            'role': 'employer',
            'company': 'TechVentures Labs',
            'location': 'Melbourne, VIC'
        }, follow_redirects=False)
        self.assertEqual(res_emp.status_code, 302)
        self.assertIn('/dashboard/employer', res_emp.headers['Location'])

    def test_10_google_auth_flow(self):
        """Test Google authentication flow: initiation, callback handling, session establishment."""
        # 1. /auth/google redirects to Supabase Google OAuth authorize URL
        res_init = self.client.get('/auth/google?role=seeker&redirect=/dashboard/seeker')
        self.assertEqual(res_init.status_code, 302)
        self.assertIn('provider=google', res_init.headers['Location'])
        self.assertIn('supabase.co/auth/v1/authorize', res_init.headers['Location'])

        # 2. /auth/callback renders handler page
        res_cb = self.client.get('/auth/callback')
        self.assertEqual(res_cb.status_code, 200)
        self.assertIn('Authenticating with Google', res_cb.data.decode('utf-8'))

        # 3. /api/auth/google-callback creates/finds Google user and establishes session
        res_api = self.client.post('/api/auth/google-callback', json={
            'email': 'maya.lin.google@example.com',
            'name': 'Maya Lin',
            'avatar': 'https://example.com/avatar.jpg'
        })
        self.assertEqual(res_api.status_code, 200)
        res_json = res_api.get_json()
        self.assertTrue(res_json['ok'])
        self.assertIn('/dashboard/seeker', res_json['redirect'])

        # Verify authenticated session in Flask
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('demo_role'), 'seeker')
            self.assertEqual(sess.get('user_name'), 'Maya Lin')

    def test_11_sms_forgot_password_and_reset_flow(self):
        """Test complete SMS OTP Forgot Password flow: request, OTP verification, password update, and login."""
        # Target user: Jordan Reyes
        target_email = 'jordan@nexora.com'
        new_password = 'newpassword2026'

        # 1. Request SMS OTP for Jordan
        res_req = self.client.post('/forgot-password', data={'identifier': target_email}, follow_redirects=False)
        self.assertEqual(res_req.status_code, 302)
        self.assertIn('/verify-otp', res_req.headers['Location'])

        # 2. View OTP verification page with SMS preview banner
        res_vpage = self.client.get('/verify-otp')
        self.assertEqual(res_vpage.status_code, 200)
        html_vpage = res_vpage.data.decode('utf-8')
        self.assertIn('Enter Verification Code', html_vpage)
        self.assertIn('Incoming SMS Message', html_vpage)

        # Retrieve the OTP that was dispatched
        with self.client.session_transaction() as sess:
            sent_otp = sess.get('last_otp_code')
        self.assertIsNotNone(sent_otp)
        self.assertEqual(len(sent_otp), 6)

        # 3. Test invalid OTP rejection
        res_bad = self.client.post('/verify-otp', data={'otp': '000000'})
        self.assertEqual(res_bad.status_code, 400)
        self.assertIn('Invalid verification code', res_bad.data.decode('utf-8'))

        # 4. Test valid OTP submission
        res_good = self.client.post('/verify-otp', data={'otp': sent_otp}, follow_redirects=False)
        self.assertEqual(res_good.status_code, 302)
        self.assertIn('/reset-password', res_good.headers['Location'])

        # 5. View Reset Password page
        res_reset_page = self.client.get('/reset-password')
        self.assertEqual(res_reset_page.status_code, 200)
        self.assertIn('Create New Password', res_reset_page.data.decode('utf-8'))

        # 6. Submit new password
        res_set = self.client.post('/reset-password', data={
            'password': new_password,
            'confirm_password': new_password
        }, follow_redirects=False)
        self.assertEqual(res_set.status_code, 302)
        self.assertIn('/login?msg=password_reset_success', res_set.headers['Location'])

        # 7. Sign in with the newly reset password!
        res_login = self.client.post('/login', data={
            'email': target_email,
            'password': new_password
        }, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn('Welcome back, Jordan', res_login.data.decode('utf-8'))

    def test_12_same_email_different_role_rejection(self):
        """Test that an email registered as a job seeker CANNOT be re-registered as an employer."""
        test_email = "unique.seeker@domain.com"
        # 1. Register as seeker
        res_reg = self.client.post('/register', data={
            'name': 'Candidate One',
            'email': test_email,
            'password': 'password123',
            'role': 'seeker'
        }, follow_redirects=False)
        self.assertEqual(res_reg.status_code, 302)

        # 2. Attempt to register the exact same email as employer
        res_conflict = self.client.post('/register', data={
            'name': 'Employer Person',
            'email': test_email,
            'password': 'password123',
            'role': 'employer',
            'company': 'Conflict Corp'
        }, follow_redirects=False)
        self.assertEqual(res_conflict.status_code, 400)
        html_conflict = res_conflict.data.decode('utf-8')
        self.assertIn('already registered as a Seeker', html_conflict)
        self.assertIn('cannot be shared across both Job Seeker and Employer accounts', html_conflict)


if __name__ == '__main__':
    unittest.main()
