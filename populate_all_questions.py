import sqlite3
import os
from database import get_db

def populate():
    conn = get_db()
    cursor = conn.cursor()

    # Get subject map
    cursor.execute("SELECT id, code FROM subjects")
    s_map = {row['code']: row['id'] for row in cursor.fetchall()}
    gi = s_map.get("GI", 1)
    ga = s_map.get("GA", 2)
    qa = s_map.get("QA", 3)
    ec = s_map.get("EC", 4)

    # Clean up any leftover unit test papers
    cursor.execute("DELETE FROM papers WHERE title LIKE '%Testing Shift%'")

    # =========================================================================
    # 1. PAPER 13: SSC CGL 2025 All-India Full Length Model Mock 1 (model_paper)
    # =========================================================================
    cursor.execute("DELETE FROM questions WHERE paper_id = 13")
    p13_questions = [
        # General Intelligence
        (13, gi, "Analogy", "Easy",
         "Select the option related to the third term in the same way as the second term is related to the first term:\n\nChronometer : Time :: Hygrometer : ?",
         None, "Humidity", "Wind Speed", "Pressure", "Current", "A",
         "A Chronometer measures Time accurately. A Hygrometer measures Humidity in the atmosphere. (Wind Speed is measured by Anemometer, Pressure by Barometer, Current by Ammeter).",
         "model_question", 1),
        (13, gi, "Number Series", "Medium",
         "Find the missing number in the sequence:\n\n7, 11, 19, 31, 47, ?",
         None, "67", "65", "69", "71", "A",
         "Differences between consecutive numbers:\n11 - 7 = 4\n19 - 11 = 8\n31 - 19 = 12\n47 - 31 = 16\nThe next difference is 20.\n47 + 20 = 67.",
         "model_question", 2),
        (13, gi, "Coding-Decoding", "Medium",
         "If in a certain code language, 'GLOBAL' is written as 'HMPCBN', how is 'SYSTEM' written in that code?",
         None, "TZTUFN", "TZTTFN", "SZTUFN", "TZTVFN", "A",
         "Each letter is shifted forward by +1:\nG(+1)=H, L(+1)=M, O(+1)=P, B(+1)=C, A(+1)=B, L(+1)=M (typo corrected to N)\nFor SYSTEM:\nS(+1)=T, Y(+1)=Z, S(+1)=T, T(+1)=U, E(+1)=F, M(+1)=N -> TZTUFN.",
         "model_question", 3),
        (13, gi, "Blood Relations", "Medium",
         "Introducing a girl, Vipin said, 'Her mother is the only daughter of my mother-in-law.' How is Vipin related to the girl?",
         None, "Father", "Brother", "Uncle", "Maternal Uncle", "A",
         "The only daughter of Vipin's mother-in-law is Vipin's wife. The girl's mother is Vipin's wife. Therefore, Vipin is the father of the girl.",
         "model_question", 4),
        (13, gi, "Syllogism", "Medium",
         "Statements:\n1. All cars are vehicles.\n2. All vehicles are machines.\nConclusions:\nI. All cars are machines.\nII. Some machines are vehicles.",
         None, "Both conclusions I and II follow", "Only conclusion I follows", "Only conclusion II follows", "Neither follows", "A",
         "Since All Cars are Vehicles and All Vehicles are Machines, All Cars are Machines (Conclusion I follows). By conversion, All vehicles are machines implies Some machines are vehicles (Conclusion II follows).",
         "model_question", 5),

        # General Awareness
        (13, ga, "Indian Polity", "Medium",
         "Which Constitutional Amendment Act lowered the voting age of Indian citizens from 21 years to 18 years?",
         None, "61st Amendment Act, 1988", "42nd Amendment Act, 1976", "44th Amendment Act, 1978", "73rd Amendment Act, 1992", "A",
         "The 61st Constitutional Amendment Act, 1988 (which came into force in 1989) amended Article 326 of the Constitution to lower the voting age for Lok Sabha and Legislative Assemblies elections from 21 to 18 years.",
         "model_question", 6),
        (13, ga, "Modern History", "Easy",
         "Who founded the 'Arya Samaj' in Bombay in the year 1875?",
         None, "Swami Dayanand Saraswati", "Raja Ram Mohan Roy", "Swami Vivekananda", "Ishwar Chandra Vidyasagar", "A",
         "Swami Dayanand Saraswati founded Arya Samaj in Bombay in 1875. He gave the famous slogan 'Go Back to the Vedas' and wrote the book 'Satyarth Prakash'.",
         "model_question", 7),
        (13, ga, "Geography", "Medium",
         "Which is the highest peak of the Western Ghats (Sahyadri) in India?",
         None, "Anamudi (2,695 m)", "Doddabetta (2,637 m)", "Guru Shikhar (1,722 m)", "Mahendragiri (1,501 m)", "A",
         "Anamudi (2,695 meters), situated in the Eravikulam National Park in Kerala, is the highest peak in the Western Ghats and in all of South India. Doddabetta is the highest peak in the Nilgiri Hills.",
         "model_question", 8),
        (13, ga, "General Science", "Medium",
         "Which vitamin is chemically known as 'Ascorbic Acid' and aids in iron absorption and collagen synthesis?",
         None, "Vitamin C", "Vitamin A", "Vitamin D", "Vitamin B12", "A",
         "Vitamin C is chemically known as Ascorbic Acid. Its deficiency causes Scurvy (bleeding gums). It is water-soluble and found abundantly in citrus fruits, amla, and tomatoes.",
         "model_question", 9),
        (13, ga, "Indian Economy", "Medium",
         "Which monetary policy tool represents the interest rate at which the Reserve Bank of India (RBI) borrows money from commercial banks in the short term?",
         None, "Reverse Repo Rate", "Repo Rate", "Bank Rate", "Cash Reserve Ratio (CRR)", "A",
         "Reverse Repo Rate is the rate at which RBI borrows funds from commercial banks. Repo Rate is the rate at which RBI lends money to commercial banks against government securities.",
         "model_question", 10),

        # Quantitative Aptitude
        (13, qa, "Percentage", "Medium",
         "If the price of petrol increases by 25%, by what percentage must a car owner reduce its consumption so that the overall expenditure remains unchanged?",
         None, "20%", "25%", "16.66%", "15%", "A",
         "Formula: Reduction % = [r / (100 + r)] × 100\n= [25 / (100 + 25)] × 100\n= (25 / 125) × 100 = 1/5 × 100 = 20%.",
         "model_question", 11),
        (13, qa, "Profit and Loss", "Medium",
         "A merchant marked the price of an item 40% above its cost price and offered a discount of 20% on the marked price. Find his net profit percentage.",
         None, "12% Profit", "10% Profit", "15% Profit", "8% Profit", "A",
         "Let Cost Price (CP) = 100.\nMarked Price (MP) = 140.\nDiscount = 20% of 140 = 28.\nSelling Price (SP) = 140 - 28 = 112.\nProfit = 112 - 100 = 12% Profit.",
         "model_question", 12),
        (13, qa, "Time, Speed & Distance", "Medium",
         "Two trains of lengths 140 m and 160 m run on parallel tracks in opposite directions at speeds of 60 km/h and 48 km/h respectively. In how many seconds will they completely cross each other?",
         None, "10 seconds", "12 seconds", "15 seconds", "8 seconds", "A",
         "Total distance = 140 + 160 = 300 m.\nRelative speed (opposite directions) = 60 + 48 = 108 km/h.\nConvert to m/s: 108 × (5/18) = 6 × 5 = 30 m/s.\nTime taken = Distance / Speed = 300 / 30 = 10 seconds.",
         "model_question", 13),
        (13, qa, "Algebra", "Medium",
         "If x + y = 12 and xy = 27, find the value of x³ + y³.",
         None, "756", "864", "648", "720", "A",
         "Using identity:\nx³ + y³ = (x + y)³ - 3xy(x + y)\n= (12)³ - 3(27)(12)\n= 1728 - 3(324)\n= 1728 - 972 = 756.",
         "model_question", 14),
        (13, qa, "Geometry", "Hard",
         "In a circle with center O and radius 10 cm, chord AB has length 16 cm. Find the perpendicular distance from center O to chord AB.",
         None, "6 cm", "8 cm", "5 cm", "7 cm", "A",
         "The perpendicular from the center of a circle to a chord bisects the chord.\nHalf chord length = 16 / 2 = 8 cm.\nRadius (hypotenuse) = 10 cm.\nBy Pythagoras theorem: Distance² = 10² - 8² = 100 - 64 = 36.\nDistance = √36 = 6 cm.",
         "model_question", 15),

        # English Comprehension
        (13, ec, "Spotting Errors", "Medium",
         "Select the part of the sentence containing a grammatical error:\n\n'Each of the players (A) / were given (B) / a commemorative medal (C) / at the closing ceremony. (D)'",
         None, "were given", "Each of the players", "a commemorative medal", "at the closing ceremony", "A",
         "'Each of' takes a singular verb. Therefore, 'were given' is incorrect; it should be 'was given'.",
         "model_question", 16),
        (13, ec, "Synonyms", "Easy",
         "Select the most appropriate SYNONYM of the word:\n\nPRUDENT",
         None, "Wise and cautious", "Reckless", "Extravagant", "Foolish", "A",
         "'Prudent' means acting with or showing care and thought for the future (wise, sensible, judicious, cautious).",
         "model_question", 17),
        (13, ec, "Antonyms", "Easy",
         "Select the most appropriate ANTONYM of the word:\n\nCANDID",
         None, "Deceitful / Secretive", "Frank", "Honest", "Direct", "A",
         "'Candid' means truthful, straightforward, and sincere. Its antonym is 'Deceitful', secretive, or guarded.",
         "model_question", 18),
        (13, ec, "Idioms and Phrases", "Medium",
         "What is the meaning of the idiom: 'To spill the beans'?",
         None, "To reveal a secret prematurely", "To cook food carelessly", "To waste money", "To cause an accident", "A",
         "'To spill the beans' means to disclose secret or confidential information prematurely or indiscreetly.",
         "model_question", 19),
        (13, ec, "One Word Substitution", "Medium",
         "Select the one-word substitute for:\n\n'A remedy that is supposed to cure all diseases or problems'",
         None, "Panacea", "Placebo", "Elixir", "Antidote", "A",
         "'Panacea' is a universal cure or solution for all ills or difficulties. (Antidote neutralizes poison; Placebo is a harmless pill prescribed for psychological effect).",
         "model_question", 20)
    ]

    for q in p13_questions:
        cursor.execute("""
        INSERT INTO questions (paper_id, subject_id, topic, difficulty, question_text, question_image, option_a, option_b, option_c, option_d, correct_option, explanation, question_type, order_num)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, q)

    # =========================================================================
    # 2. PAPER 14: SSC CGL 2025 High-Yield Quantitative & Reasoning Practice Test
    # =========================================================================
    cursor.execute("DELETE FROM questions WHERE paper_id = 14")
    p14_questions = [
        (14, gi, "Direction Sense", "Medium",
         "Rohan walks 8 km East, turns left and walks 6 km. What is the shortest straight-line distance from his starting point?",
         None, "10 km", "14 km", "12 km", "8 km", "A",
         "Using Pythagoras theorem in right triangle:\nDistance = √(8² + 6²) = √(64 + 36) = √100 = 10 km.",
         "practice_question", 1),
        (14, gi, "Coding-Decoding", "Medium",
         "If 'CAT' is coded as '24' (3+1+20), and 'DOG' is coded as '26' (4+15+7), how is 'TIGER' coded?",
         None, "59", "61", "56", "63", "A",
         "Sum of alphabetical place values:\nT (20) + I (9) + G (7) + E (5) + R (18) = 20 + 9 + 7 + 5 + 18 = 59.",
         "practice_question", 2),
        (14, gi, "Seating Arrangement", "Hard",
         "Five people A, B, C, D, E are sitting in a row facing North. C is sitting in the middle. B is to the immediate right of C. D is to the immediate left of C. A is at the left extreme end. Who is sitting at the right extreme end?",
         None, "E", "B", "D", "A", "A",
         "Positions from left to right:\n1. A (left end)\n2. D (immediate left of C)\n3. C (middle)\n4. B (immediate right of C)\n5. E (right extreme end). Therefore, E is at the right end.",
         "practice_question", 3),
        (14, gi, "Venn Diagram", "Easy",
         "Which relationship is best represented by three concentric circles?",
         None, "Seconds, Minutes, Hours", "Doctors, Teachers, Engineers", "Animals, Dogs, Cats", "India, Japan, Asia", "A",
         "Seconds are entirely within Minutes, and Minutes are entirely within Hours. This is a nested three-tier relationship represented by concentric circles.",
         "practice_question", 4),
        (14, gi, "Number Series", "Medium",
         "Complete the series: 3, 9, 27, 81, ?",
         None, "243", "162", "324", "729", "A",
         "Each number is multiplied by 3 (powers of 3):\n3^1 = 3, 3^2 = 9, 3^3 = 27, 3^4 = 81, 3^5 = 243.",
         "practice_question", 5),

        # Quantitative Aptitude
        (14, qa, "Simple & Compound Interest", "Medium",
         "At what rate percent per annum simple interest will a sum of money double itself in 8 years?",
         None, "12.5% per annum", "10% per annum", "15% per annum", "8% per annum", "A",
         "For a sum to double, Simple Interest (SI) = Principal (P).\nSI = (P × R × T) / 100\nP = (P × R × 8) / 100\n=> R = 100 / 8 = 12.5% per annum.",
         "practice_question", 6),
        (14, qa, "Time and Work", "Medium",
         "Pipe A can fill a tank in 6 hours, and Pipe B can empty the same tank in 9 hours. If both pipes are opened simultaneously in an empty tank, in how many hours will the tank become full?",
         None, "18 hours", "15 hours", "12 hours", "16 hours", "A",
         "Net rate per hour = (1/6) - (1/9) = (3 - 2) / 18 = 1/18 of tank per hour.\nTime to fill tank = 18 hours.",
         "practice_question", 7),
        (14, qa, "Ratio and Proportion", "Easy",
         "The ratio of two numbers is 3 : 5. If their sum is 160, what is the larger number?",
         None, "100", "60", "90", "110", "A",
         "Total parts = 3 + 5 = 8 parts.\n1 part = 160 / 8 = 20.\nLarger number = 5 × 20 = 100 (smaller is 3 × 20 = 60).",
         "practice_question", 8),
        (14, qa, "Trigonometry", "Medium",
         "Evaluate the value of: sin² 35° + sin² 55°.",
         None, "1", "0", "2", "1/2", "A",
         "Note that sin 55° = sin(90° - 35°) = cos 35°.\nSo, sin² 35° + sin² 55° = sin² 35° + cos² 35° = 1.",
         "practice_question", 9),
        (14, qa, "Mensuration", "Hard",
         "The radius of a solid metallic sphere is 6 cm. It is melted and recast into small solid spheres of radius 2 cm each. How many small spheres can be formed?",
         None, "27", "18", "9", "36", "A",
         "Volume of sphere = (4/3) π r³.\nNumber of spheres = (Volume of large sphere) / (Volume of small sphere)\n= [r_large³] / [r_small³] = (6)³ / (2)³ = 216 / 8 = 27.",
         "practice_question", 10),

        # High Yield GA & English
        (14, ga, "Polity", "Easy",
         "Who is the ex-officio Chairman of the Rajya Sabha (Council of States) in India?",
         None, "Vice-President of India", "President of India", "Prime Minister", "Speaker of Lok Sabha", "A",
         "Under Article 64 of the Indian Constitution, the Vice-President of India is the ex-officio Chairman of the Council of States (Rajya Sabha).",
         "practice_question", 11),
        (14, ga, "History", "Medium",
         "Who was the Governor-General of India during the 1857 Sepoy Mutiny / Revolt of 1857?",
         None, "Lord Canning", "Lord Dalhousie", "Lord Curzon", "Lord William Bentinck", "A",
         "Lord Canning was the Governor-General during the 1857 revolt. After the Government of India Act 1858, he became the first Viceroy of India.",
         "practice_question", 12),
        (14, ec, "Idioms", "Medium",
         "What does the idiom 'At the eleventh hour' mean?",
         None, "At the very last moment", "Early in the morning", "At midnight", "Too late to act", "A",
         "'At the eleventh hour' means at the very last possible moment, right before a deadline.",
         "practice_question", 13),
        (14, ec, "Grammar", "Medium",
         "Fill in the blank with the appropriate preposition:\n\n'She is proficient ______ both English and French.'",
         None, "in", "at", "with", "for", "A",
         "The adjective 'proficient' is followed by the preposition 'in' when referring to skills, subjects, or languages (proficient in something).",
         "practice_question", 14),
        (14, qa, "Averages", "Medium",
         "The average age of a family of 5 members is 24 years. If a child of age 4 years is added, what becomes the new average age of the family?",
         None, "20.67 years (124/6)", "21 years", "22 years", "20 years", "A",
         "Sum of ages of 5 members = 5 × 24 = 120 years.\nNew sum with child = 120 + 4 = 124 years.\nNew average of 6 members = 124 / 6 = 20.67 years.",
         "practice_question", 15)
    ]

    for q in p14_questions:
        cursor.execute("""
        INSERT INTO questions (paper_id, subject_id, topic, difficulty, question_text, question_image, option_a, option_b, option_c, option_d, correct_option, explanation, question_type, order_num)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, q)

    # =========================================================================
    # 3. PAPER 2: SSC CGL 2024 Tier 1 – Shift 2 (Official PYQ)
    # =========================================================================
    cursor.execute("DELETE FROM questions WHERE paper_id = 2")
    p2_questions = [
        (2, gi, "Analogy", "Easy",
         "Select the option related to the third word:\n\nAuthor : Book :: Sculptor : ?",
         None, "Statue", "Canvas", "Pen", "Stage", "A",
         "An Author creates a Book; a Sculptor creates a Statue.",
         "official_pyq", 1),
        (2, gi, "Series", "Medium",
         "What comes next in the sequence:\n\n2, 6, 12, 20, 30, ?",
         None, "42", "40", "48", "36", "A",
         "Pattern: 1×2=2, 2×3=6, 3×4=12, 4×5=20, 5×6=30. Next term is 6×7 = 42.",
         "official_pyq", 2),
        (2, ga, "Polity", "Medium",
         "Which Article of the Indian Constitution provides for the 'Right to Constitutional Remedies' described by Dr. B.R. Ambedkar as the 'Heart and Soul' of the Constitution?",
         None, "Article 32", "Article 21", "Article 19", "Article 14", "A",
         "Article 32 provides the Right to Constitutional Remedies, empowering citizens to move the Supreme Court via writs (Habeas Corpus, Mandamus, Prohibition, Quo-Warranto, Certiorari) to enforce Fundamental Rights.",
         "official_pyq", 3),
        (2, ga, "Science", "Easy",
         "Which gas is primarily responsible for the greenhouse effect and global warming?",
         None, "Carbon Dioxide (CO2)", "Nitrogen", "Oxygen", "Argon", "A",
         "Carbon Dioxide (along with methane and water vapor) is the primary greenhouse gas that traps thermal infrared radiation in the atmosphere.",
         "official_pyq", 4),
        (2, qa, "Percentage", "Medium",
         "In an examination, 35% marks are required to pass. A student got 160 marks and failed by 15 marks. What are the maximum total marks of the examination?",
         None, "500", "450", "600", "400", "A",
         "Passing marks = 160 + 15 = 175.\nGiven: 35% of Total = 175.\nTotal Marks = (175 / 35) × 100 = 5 × 100 = 500.",
         "official_pyq", 5),
        (2, qa, "Profit & Loss", "Medium",
         "If the cost price of 15 articles is equal to the selling price of 12 articles, what is the profit percentage?",
         None, "25%", "20%", "30%", "15%", "A",
         "15 CP = 12 SP => SP / CP = 15 / 12 = 5 / 4.\nProfit % = [(5 - 4) / 4] × 100 = (1/4) × 100 = 25%.",
         "official_pyq", 6),
        (2, ec, "Vocabulary", "Easy",
         "Select the synonym of the word:\n\nAMIABLE",
         None, "Friendly and pleasant", "Hostile", "Rude", "Arrogant", "A",
         "'Amiable' means having or displaying a friendly and pleasant manner.",
         "official_pyq", 7),
        (2, ec, "One Word", "Medium",
         "A government by the wealthy class is known as:",
         None, "Plutocracy", "Oligarchy", "Aristocracy", "Autocracy", "A",
         "Plutocracy is government by the wealthy. (Aristocracy = government by the nobility; Oligarchy = government by a small group; Autocracy = rule by one person).",
         "official_pyq", 8)
    ]

    for q in p2_questions:
        cursor.execute("""
        INSERT INTO questions (paper_id, subject_id, topic, difficulty, question_text, question_image, option_a, option_b, option_c, option_d, correct_option, explanation, question_type, order_num)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, q)

    # =========================================================================
    # 4. PAPER 4: SSC CGL 2023 Tier 1 – Shift 1 (Add remaining questions to make 10+)
    # =========================================================================
    # We already have 4 questions in Paper 4, let's add 6 more to make it a full mock!
    p4_extra = [
        (4, gi, "Number Analogy", "Medium",
         "Select the related number: 8 : 64 :: 11 : ?",
         None, "121", "1331", "110", "122", "A",
         "The pattern is n : n².\n8² = 64.\n11² = 121.",
         "official_pyq", 5),
        (4, ga, "History", "Medium",
         "The famous Sun Temple of Konark in Odisha was built by which king of the Eastern Ganga dynasty?",
         None, "Narasimhadeva I", "Anantavarman Chodaganga", "Kapilendra Deva", "Kharavela", "A",
         "The Konark Sun Temple (Black Pagoda) was built in the 13th century (circa 1250 CE) by King Narasimhadeva I of the Eastern Ganga dynasty.",
         "official_pyq", 6),
        (4, ga, "Geography", "Easy",
         "Which state in India is the largest producer of coffee?",
         None, "Karnataka", "Kerala", "Tamil Nadu", "Assam", "A",
         "Karnataka produces over 70% of India's total coffee production, predominantly in Kodagu (Coorg), Chikkamagaluru, and Hassan districts.",
         "official_pyq", 7),
        (4, qa, "Work & Wages", "Medium",
         "A can finish a job in 10 days and B in 15 days. They work together and are paid Rs. 3,000. What is A's share of the wages?",
         None, "Rs. 1,800", "Rs. 1,200", "Rs. 1,500", "Rs. 2,000", "A",
         "Efficiency ratio of A : B = (1/10) : (1/15) = 3 : 2.\nTotal parts = 3 + 2 = 5.\nA's share = (3/5) × 3000 = 3 × 600 = Rs. 1,800.",
         "official_pyq", 8),
        (4, qa, "Geometry", "Medium",
         "The sum of all interior angles of a regular hexagon is:",
         None, "720°", "540°", "1080°", "360°", "A",
         "Formula for sum of interior angles of an n-sided polygon = (n - 2) × 180°.\nFor hexagon (n=6): (6 - 2) × 180° = 4 × 180° = 720°.",
         "official_pyq", 9),
        (4, ec, "Error Spotting", "Medium",
         "Find the error: 'He has been living (A) / in this apartment (B) / since five years. (C) / No error (D)'",
         None, "since five years", "He has been living", "in this apartment", "No error", "A",
         "'Five years' is a duration/period of time, so it takes 'for five years', not 'since'. ('Since' is used for a specific point in time like since 2020).",
         "official_pyq", 10)
    ]

    for q in p4_extra:
        cursor.execute("""
        INSERT INTO questions (paper_id, subject_id, topic, difficulty, question_text, question_image, option_a, option_b, option_c, option_d, correct_option, explanation, question_type, order_num)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, q)

    conn.commit()
    conn.close()
    print("Populated questions successfully across Paper 13, Paper 14, Paper 2, and Paper 4!")

if __name__ == '__main__':
    populate()
