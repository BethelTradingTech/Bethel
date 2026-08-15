from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return (ROOT/p).read_text(encoding='utf-8')
backend=read('api/public_reviews.py')
for needle in ['VisitorReview','/public/reviews','/admin/reviews','require_admin','REVIEW_HASH_SALT','approved.is_(True)','Only one review may be submitted per visitor every 24 hours']:
    assert needle in backend, needle
render=read('render_app.py')
for needle in ['public_reviews_router','VisitorReview.__table__.create','Bethel moderated visitor reviews loaded']:
    assert needle in render, needle
front=read('frontend/js/visitor-reviews.js')+read('frontend/js/chat-assistant.js')
for needle in ['api.betheltradingtechnologies.com/public/reviews','Reviews are moderated before publication','visitor-reviews.js']:
    assert needle in front, needle
assert 'Trustpilot' not in read('frontend/js/visitor-reviews.js')
assert 'REVIEW_HASH_SALT' in read('render.yaml')
print('PASS: moderated visitor reviews and ratings safeguards')
