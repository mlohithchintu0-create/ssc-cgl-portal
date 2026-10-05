import unittest
import json
import io
from app import app
from database import get_db, init_db
from seed_data import seed

class SscCglPortalTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        # Seed fresh data
        seed()

    def test_01_homepage_and_navigation(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'SSC CGL', response.data)
        self.assertIn(b'Previous Year Papers', response.data)

    def test_02_authentication_and_security(self):
        # 1. Login with bad credentials
        bad_login = self.client.post('/login', data={'login_id': 'aspirant', 'password': 'wrongpassword'}, follow_redirects=True)
        self.assertIn(b'Invalid username/email or password', bad_login.data)

        # 2. Login with valid credentials
        login = self.client.post('/login', data={'login_id': 'aspirant', 'password': 'aspirant123'}, follow_redirects=True)
        self.assertIn(b'Welcome back, Rahul Sharma', login.data)

        # 3. Check dashboard access
        dash = self.client.get('/dashboard')
        self.assertEqual(dash.status_code, 200)
        self.assertIn(b'Aspirant Dashboard', dash.data)
        self.assertIn(b'Overall Net Score', dash.data)

        # 4. Logout
        logout = self.client.get('/logout', follow_redirects=True)
        self.assertIn(b'You have been logged out', logout.data)

    def test_03_year_wise_papers_and_provenance(self):
        # Login
        self.client.post('/login', data={'login_id': 'aspirant', 'password': 'aspirant123'})
        
        # Access /papers
        resp = self.client.get('/papers')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'SSC CGL 2024 Tier 1', resp.data)
        self.assertIn(b'Official PYQ', resp.data)
        self.assertIn(b'Model Paper', resp.data)

        # Paper details before test
        detail_resp = self.client.get('/papers/1')
        self.assertEqual(detail_resp.status_code, 200)
        self.assertIn(b'Examination Instructions', detail_resp.data)
        self.assertIn(b'Start Mock Test Now', detail_resp.data)

    def test_04_mock_test_engine_instant_feedback_and_scoring(self):
        # Login as aspirant
        self.client.post('/login', data={'login_id': 'aspirant', 'password': 'aspirant123'})

        # Start paper 1 (SSC CGL 2024 Tier 1 Shift 1)
        test_page = self.client.get('/test/1')
        self.assertEqual(test_page.status_code, 200)
        self.assertIn(b'mock test', test_page.data.lower())
        self.assertIn(b'question palette', test_page.data.lower())

        # Find attempt ID
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM test_attempts WHERE user_id = 2 AND paper_id = 1 AND status = 'in_progress' ORDER BY id DESC LIMIT 1")
        att = cursor.fetchone()
        self.assertIsNotNone(att)
        attempt_id = att['id']

        # API fetch state
        state_resp = self.client.get(f'/api/attempt/{attempt_id}/state')
        self.assertEqual(state_resp.status_code, 200)
        state_data = json.loads(state_resp.data)
        self.assertGreater(len(state_data['questions']), 0)
        first_q = state_data['questions'][0]

        # Submit answer (Immediate Feedback checking - Section 8)
        ans_resp = self.client.post(
            f'/api/attempt/{attempt_id}/submit_answer',
            data=json.dumps({
                'question_id': first_q['id'],
                'selected_option': 'A', # Thermometer : Temperature :: Barometer : Atmospheric Pressure (A)
                'time_spent_seconds': 10
            }),
            content_type='application/json'
        )
        self.assertEqual(ans_resp.status_code, 200)
        ans_data = json.loads(ans_resp.data)
        self.assertTrue(ans_data['success'])
        self.assertTrue(ans_data['is_correct'])
        self.assertEqual(ans_data['correct_option'], 'A')
        self.assertIn('Atmospheric Pressure', ans_data['explanation'])

        # Submit answer for Question 2 with wrong option to test negative marking
        second_q = state_data['questions'][1]
        ans2_resp = self.client.post(
            f'/api/attempt/{attempt_id}/submit_answer',
            data=json.dumps({
                'question_id': second_q['id'],
                'selected_option': 'D', # Correct is A (119)
                'time_spent_seconds': 15
            }),
            content_type='application/json'
        )
        self.assertEqual(ans2_resp.status_code, 200)
        ans2_data = json.loads(ans2_resp.data)
        self.assertFalse(ans2_data['is_correct'])
        self.assertEqual(ans2_data['selected_option'], 'D')
        self.assertEqual(ans2_data['correct_option'], 'A')

        # Finish test
        finish_resp = self.client.post(f'/api/attempt/{attempt_id}/finish')
        self.assertEqual(finish_resp.status_code, 200)
        finish_data = json.loads(finish_resp.data)
        self.assertIn('/result/', finish_data['redirect'])

        # Verify Result Page
        res_page = self.client.get(f'/result/{attempt_id}')
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b'Official Mock Test Result', res_page.data)
        self.assertIn(b'Section-Wise Performance Card', res_page.data)

        # Verify Review Page with status filters
        rev_all = self.client.get(f'/review/{attempt_id}?filter=all')
        self.assertEqual(rev_all.status_code, 200)
        self.assertIn(b'Detailed Answer Review', rev_all.data)

        rev_correct = self.client.get(f'/review/{attempt_id}?filter=correct')
        self.assertEqual(rev_correct.status_code, 200)

        conn.close()

    def test_05_admin_panel_crud_and_bulk_import(self):
        # 1. Non-admin blocked
        self.client.post('/login', data={'login_id': 'aspirant', 'password': 'aspirant123'})
        admin_blocked = self.client.get('/admin', follow_redirects=True)
        self.assertIn(b'Access denied', admin_blocked.data)

        # 2. Login as admin
        self.client.get('/logout')
        admin_login = self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertIn(b'Welcome back, SSC Portal Administrator', admin_login.data)
        admin_dash = self.client.get('/admin')
        self.assertIn(b'Administration & Question Bank', admin_dash.data)

        # 3. Add Paper via Admin
        add_paper = self.client.post('/admin/papers', data={
            'action': 'add',
            'title': 'SSC CGL 2025 Tier 1 – Shift 4 (Testing Shift)',
            'year': 2025,
            'tier': 'Tier 1',
            'shift': 'Shift 4',
            'duration_minutes': 60,
            'marks_per_question': 2.0,
            'negative_marks': 0.50,
            'paper_type': 'model_paper',
            'source_attribution': 'Admin Portal Unit Test',
            'instructions': 'Automated Test Guidelines'
        }, follow_redirects=True)
        self.assertIn(b'created successfully', add_paper.data)

        # Find new paper ID
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM papers WHERE title LIKE '%Shift 4 (Testing Shift)%'")
        new_paper = cursor.fetchone()
        self.assertIsNotNone(new_paper)
        new_paper_id = new_paper['id']
        conn.close()

        # 4. Add Question via Admin
        add_q = self.client.post('/admin/questions', data={
            'action': 'add',
            'paper_id': new_paper_id,
            'subject_id': 1,
            'topic': 'Analogy',
            'difficulty': 'Easy',
            'question_text': 'Odometer is to Mileage as Compass is to what?',
            'question_image': '',
            'option_a': 'Direction',
            'option_b': 'Speed',
            'option_c': 'Altitude',
            'option_d': 'Weight',
            'correct_option': 'A',
            'explanation': 'An odometer measures mileage; a compass determines geographic direction.',
            'question_type': 'model_question',
            'order_num': 1
        }, follow_redirects=True)
        self.assertIn(b'Question added successfully', add_q.data)

        # 5. Bulk Import via JSON
        sample_json = json.dumps([
            {
                "subject_code": "GA",
                "topic": "Polity",
                "difficulty": "Medium",
                "question_text": "Which Part of the Indian Constitution deals with Fundamental Rights?",
                "option_a": "Part III",
                "option_b": "Part IV",
                "option_c": "Part II",
                "option_d": "Part IV-A",
                "correct_option": "A",
                "explanation": "Part III (Articles 12-35) enshrines the Fundamental Rights of Indian citizens.",
                "question_type": "official_pyq",
                "order_num": 2
            }
        ])
        import_resp = self.client.post(
            '/admin/questions/import',
            data={
                'target_paper_id': new_paper_id,
                'file': (io.BytesIO(sample_json.encode('utf-8')), 'test_questions.json')
            },
            content_type='multipart/form-data',
            follow_redirects=True
        )
        self.assertIn(b'Successfully imported 1 questions', import_resp.data)

        # 6. Export JSON
        export_resp = self.client.get(f'/admin/questions/export?paper_id={new_paper_id}&format=json')
        self.assertEqual(export_resp.status_code, 200)
        export_data = json.loads(export_resp.data)
        self.assertGreaterEqual(len(export_data), 2)

        # 7. Check Users Directory
        users_resp = self.client.get('/admin/users')
        self.assertEqual(users_resp.status_code, 200)
        self.assertIn(b'Aspirant Directory', users_resp.data)
        self.assertIn(b'admin', users_resp.data)
        self.assertIn(b'aspirant', users_resp.data)

        conn.close()

if __name__ == '__main__':
    unittest.main()
