"""Bank pytań do zejściówek: kompletność, odnośniki do materiałów i wyświetlanie w panelu."""
from collections import Counter

from app import app
from calculations.lecture_quiz import LECTURES, QUESTIONS, lectures_with_questions

# Liczba stron materiałów okBIPOL_1_handout_*.pdf (wydruk po trzy slajdy na stronę).
PAGES = {'okBIPOL_1_handout_1.pdf': 8, 'okBIPOL_1_handout_2.pdf': 20, 'okBIPOL_1_handout_3.pdf': 22,
         'okBIPOL_1_handout_4.pdf': 17, 'okBIPOL_1_handout_5.pdf': 36, 'okBIPOL_1_handout_6.pdf': 13,
         'okBIPOL_1_handout_7.pdf': 20, 'okBIPOL_1_handout_8.pdf': 21, 'okBIPOL_1_handout_9.pdf': 10,
         'okBIPOL_1_handout_10.pdf': 22, 'okBIPOL_1_handout_11_1.pdf': 7, 'okBIPOL_1_handout_11_2.pdf': 6,
         'okBIPOL_1_handout_12.pdf': 14, 'okBIPOL_1_handout_13.pdf': 8, 'okBIPOL_1_handout_14.pdf': 12,
         'okBIPOL_1_handout_15.pdf': 9}


def test_every_lecture_has_questions_with_valid_references():
    counts = Counter(q['lecture'] for q in QUESTIONS)
    assert [key for key, *_ in LECTURES] == sorted(counts) and min(counts.values()) >= 4
    assert len({q['id'] for q in QUESTIONS}) == len(QUESTIONS)
    assert len({q['question'] for q in QUESTIONS}) == len(QUESTIONS)
    for q in QUESTIONS:
        assert q['source'] in PAGES, q
        assert 1 <= q['slide'] <= PAGES[q['source']], q
        assert q['question'].endswith(('?', '.')) and len(q['answer']) > 40, q['id']


def test_lectures_group_questions_in_order():
    lectures = lectures_with_questions()
    assert [lecture['number'] for lecture in lectures] == list(range(1, 16))
    assert sum(len(lecture['questions']) for lecture in lectures) == len(QUESTIONS)


def test_quiz_panel_renders_all_questions():
    html = app.test_client().get('/').get_data(as_text=True)
    assert 'id="tab-quiz"' in html and 'data-studio-nav="tab-quiz"' in html and '/static/js/quiz.js' in html
    assert html.count('class="quiz-question"') == len(QUESTIONS)
    assert html.count('data-quiz-progress=') == len(LECTURES)
