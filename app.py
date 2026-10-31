import os, random, subprocess, sys, sqlite3, hashlib, secrets
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, g

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylearn.db')

# ---------------------------------------------------
# Database helpers
# ---------------------------------------------------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    db.commit()
    db.close()

init_db()

def hash_password(pw):
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + pw).encode()).hexdigest()
    return salt + ':' + h

def check_password(stored, pw):
    salt, h = stored.split(':')
    return hashlib.sha256((salt + pw).encode()).hexdigest() == h

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ---------------------------------------------------
# Quiz question banks
# ---------------------------------------------------
EASY = [
    {"question":"What keyword defines a function?","choices":["def","function","func","define"],"answer":"def"},
    {"question":"Output of print(2+3)?","choices":["5","23","6","Error"],"answer":"5"},
    {"question":"Comment symbol in Python?","choices":["//","#","/*","--"],"answer":"#"},
    {"question":"Type of 3.14?","choices":["int","str","float","bool"],"answer":"float"},
    {"question":"Create variable x=10?","choices":["x = 10","int x = 10","var x = 10","x := 10"],"answer":"x = 10"},
    {"question":"len('hello')?","choices":["4","5","6","Error"],"answer":"5"},
    {"question":"Which is a string?","choices":["42","True","'hello'","[1,2]"],"answer":"'hello'"},
    {"question":"print('Hello'+' World')?","choices":["Hello World","HelloWorld","Error","Hello+World"],"answer":"Hello World"},
    {"question":"Correct if syntax?","choices":["if x==5:","if(x==5)","if x=5:","if x==5 then"],"answer":"if x==5:"},
    {"question":"What does input() do?","choices":["Prints","Reads input","Creates file","Loops"],"answer":"Reads input"},
    {"question":"True + True?","choices":["True","2","TrueTrue","Error"],"answer":"2"},
    {"question":"Not equal operator?","choices":["<>","!=","=/=","not="],"answer":"!="},
    {"question":"Type of True?","choices":["int","str","bool","float"],"answer":"bool"},
    {"question":"Fixed-count loop?","choices":["for","while","do-while","repeat"],"answer":"for"},
    {"question":"range(5) produces?","choices":["[1,2,3,4,5]","[0,1,2,3,4]","[0,1,2,3,4,5]","[1,2,3,4]"],"answer":"[0,1,2,3,4]"},
]
MEDIUM = [
    {"question":"[1,2,3][1:]?","choices":["[1,2]","[2,3]","[1]","[3]"],"answer":"[2,3]"},
    {"question":"'hello'.upper()?","choices":["Hello","HELLO","hello","hELLO"],"answer":"HELLO"},
    {"question":"Add item to list?","choices":["add()","append()","push()","insert()"],"answer":"append()"},
    {"question":"Dict key:value separator?","choices":["=",":","->","=>"],"answer":":"},
    {"question":"'break' in loop?","choices":["Skips","Exits loop","Restarts","Pauses"],"answer":"Exits loop"},
    {"question":"10 // 3?","choices":["3.33","3","4","1"],"answer":"3"},
    {"question":"Handle exceptions?","choices":["try/except","try/catch","handle/error","if/error"],"answer":"try/except"},
    {"question":"'in' keyword checks?","choices":["Membership","Identity","Equality","Type"],"answer":"Membership"},
    {"question":"What is a tuple?","choices":["Mutable seq","Immutable seq","Dictionary","Set"],"answer":"Immutable seq"},
    {"question":"list(range(3))?","choices":["[1,2,3]","[0,1,2]","(0,1,2)","range(3)"],"answer":"[0,1,2]"},
    {"question":"2 ** 4?","choices":["8","16","6","24"],"answer":"16"},
    {"question":"Open file for reading?","choices":["open('f','r')","open('f','w')","read('f')","file('f')"],"answer":"open('f','r')"},
    {"question":"continue in loop?","choices":["Exits","Skips to next","Restarts","Nothing"],"answer":"Skips to next"},
    {"question":"Valid set?","choices":["{1,2,3}","[1,2,3]","(1,2,3)","set[1,2,3]"],"answer":"{1,2,3}"},
    {"question":"Lambda function?","choices":["Named func","Anonymous func","Class method","Module"],"answer":"Anonymous func"},
]
HARD = [
    {"question":"@staticmethod does?","choices":["Static method","Private method","Decorator","Logging"],"answer":"Static method"},
    {"question":"set([1,2,2,3])?","choices":["[1,2,3]","{1,2,3}","(1,2,3)","{1,2,2,3}"],"answer":"{1,2,3}"},
    {"question":"*args does?","choices":["Keyword args","Variable positional","Default args","No args"],"answer":"Variable positional"},
    {"question":"Generator in Python?","choices":["A class","Yields lazily","A module","A decorator"],"answer":"Yields lazily"},
    {"question":"GIL stands for?","choices":["Global Interpreter Lock","General Input Loop","Global Index List","General Interpreter Layer"],"answer":"Global Interpreter Lock"},
    {"question":"__init__ is?","choices":["Destructor","Constructor","Iterator","Decorator"],"answer":"Constructor"},
    {"question":"bool('')?","choices":["True","False","None","Error"],"answer":"False"},
    {"question":"zip() does?","choices":["Compresses","Pairs iterables","Sorts","Filters"],"answer":"Pairs iterables"},
    {"question":"List comprehension?","choices":["A loop","Concise list creation","A class","Error handling"],"answer":"Concise list creation"},
    {"question":"__name__=='__main__'?","choices":["Imported","Runs directly","Func exists","Class defined"],"answer":"Runs directly"},
    {"question":"Decorator is?","choices":["A class","Wraps a function","A variable","A module"],"answer":"Wraps a function"},
    {"question":"map() returns in Py3?","choices":["list","map object","tuple","dict"],"answer":"map object"},
    {"question":"MRO stands for?","choices":["Method Resolution Order","Module Run Order","Main Return Object","Meta Resource Object"],"answer":"Method Resolution Order"},
    {"question":"__slots__ does?","choices":["Limits attrs","Creates UI","Adds methods","Enables GIL"],"answer":"Limits attrs"},
    {"question":"Walrus operator?","choices":[":=","==","=>","::"],"answer":":="},
]

def get_quiz(level, qnum):
    pool = EASY if level <= 10 else MEDIUM if level <= 20 else HARD
    return pool[(level * 7 + qnum * 3) % len(pool)]

def run_user_code(code):
    try:
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=5)
        return {"out": r.stdout, "err": r.stderr}
    except subprocess.TimeoutExpired:
        return {"out": "", "err": "Error: Took too long (5s limit)."}
    except Exception as e:
        return {"out": "", "err": str(e)}

# ---------------------------------------------------
# Auth routes
# ---------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm  = request.form.get('confirm', '').strip()
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('register.html')
        if len(username) < 3:
            flash('Username must be at least 3 characters.', 'error')
            return render_template('register.html')
        if len(password) < 4:
            flash('Password must be at least 4 characters.', 'error')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        db = get_db()
        if db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
            flash('Username already taken.', 'error')
            return render_template('register.html')
        db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hash_password(password)))
        db.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if user and check_password(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('home'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ---------------------------------------------------
# Page routes
# ---------------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/training')
def training():
    return render_template('training.html')

@app.route('/play')
def play():
    return render_template('play.html')

@app.route('/editor')
def editor():
    return render_template('editor.html')

@app.route('/script')
def script():
    return render_template('script.html')

@app.route('/games')
def games():
    return render_template('games.html')

# ---------------------------------------------------
# API
# ---------------------------------------------------
@app.route('/api/quiz/<int:level>/<int:qnum>')
def api_quiz(level, qnum):
    if not (1 <= level <= 30):
        return jsonify({"error": "Level 1-30"}), 400
    return jsonify(get_quiz(level, qnum))

@app.route('/execute', methods=['POST'])
def execute():
    data = request.get_json()
    return jsonify(run_user_code(data.get('code', '')))

@app.route('/check_answer', methods=['POST'])
def check_answer():
    data = request.get_json()
    return jsonify({"correct": data.get('answer') == data.get('correct')})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
