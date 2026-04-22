import random
from typing import List, Dict, Any

# Mock IQ test database
# Real IQ tests evaluate spatial, verbal, and math logic.
IQ_QUESTIONS = [
    {
        "id": 1,
        "type": "logic",
        "question": "If some Smurfs are Snorks, and all Snorks are swans, which statement is definitely true?",
        "options": [
            "All Smurfs are swans",
            "Some Smurfs are swans",
            "No Smurfs are swans",
            "All swans are Snorks"
        ],
        "answer": 1
    },
    {
        "id": 2,
        "type": "math",
        "question": "What number comes next in the sequence: 2, 6, 12, 20, 30, ...?",
        "options": ["38", "40", "42", "44"],
        "answer": 2
    },
    {
        "id": 3,
        "type": "pattern",
        "question": "O A T \nS T A \nT O ?",
        "options": ["O", "S", "A", "T"],
        "answer": 1
    },
    {
        "id": 4,
        "type": "logic",
        "question": "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?",
        "options": ["$0.10", "$0.05", "$0.50", "$1.00"],
        "answer": 1
    },
    {
        "id": 5,
        "type": "math",
        "question": "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?",
        "options": ["100 minutes", "50 minutes", "5 minutes", "1 minute"],
        "answer": 2
    },
    {
        "id": 6,
        "type": "pattern",
        "question": "Which word does not belong?",
        "options": ["Apple", "Banana", "Carrot", "Mango"],
        "answer": 2
    },
    {
        "id": 7,
        "type": "logic",
        "question": "In a lake, there is a patch of lily pads. Every day, the patch doubles in size. If it takes 48 days for the patch to cover the entire lake, how long would it take to cover half of it?",
        "options": ["24 days", "47 days", "12 days", "36 days"],
        "answer": 1
    },
    {
        "id": 8,
        "type": "verbal",
        "question": "What is the antonym of 'Obscure'?",
        "options": ["Hidden", "Clear", "Dark", "Complicated"],
        "answer": 1
    },
    {
        "id": 9,
        "type": "math",
        "question": "Find the missing number: 8, 27, 64, 125, ?",
        "options": ["216", "150", "256", "300"],
        "answer": 0
    },
    {
        "id": 10,
        "type": "logic",
        "question": "If you look in a mirror and touch your left ear with your right hand, what does your reflection seem to do?",
        "options": [
            "Touch its left ear with its right hand",
            "Touch its right ear with its left hand",
            "Touch its left ear with its left hand",
            "Touch its right ear with its right hand"
        ],
        "answer": 1
    }
]

def get_iq_test_questions(limit: int = 10) -> List[Dict[str, Any]]:
    # Shuffle and select questions without answers to send to the client
    questions = random.sample(IQ_QUESTIONS, min(limit, len(IQ_QUESTIONS)))
    
    # Strip answers for client safety
    safe_questions = []
    for q in questions:
        safe_q = q.copy()
        safe_q.pop("answer", None)
        safe_questions.append(safe_q)
        
    return safe_questions

def calculate_iq_score(answers: Dict[int, int]) -> int:
    """
    Given a dict of question_id -> selected_option_index, calculates an IQ score.
    Returns calculated IQ.
    """
    correct = 0
    total = len(answers)
    
    if total == 0:
        return 0
        
    for q in IQ_QUESTIONS:
        if q["id"] in answers:
            if answers[q["id"]] == q["answer"]:
                correct += 1
                
    # Basic IQ score calculation formula: 
    # Base 80 + (correct / total) * 60 (max 140)
    score = 80 + int((correct / total) * 60)
    return score
