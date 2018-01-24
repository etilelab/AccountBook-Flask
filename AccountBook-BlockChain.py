from flask import Flask, render_template, jsonify, request, redirect, session
import json
from textwrap import dedent
from uuid import uuid4
from blockchain import BlockChain
from datetime import datetime
from flaskext.mysql import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import sec

mysql = MySQL()
app = Flask(__name__)

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'dlxorud7202'
app.config['MYSQL_DATABASE_DB'] = 'accountBook'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

app.secret_key = '???'

# 홈화면
@app.route('/')
def home_intro():
    return validateLogin()

# 회비납부 화면
@app.route('/current')
def current():
    return render_template('current.html', name="current")

# 장부화면
# 기능
# db에서 가장 최근순으로 20개의 장부내역을 가져와야함
# 정렬 기능(오래된, 사용금액, 사용일 순), 검색기능(내역에서) 포함해야함
@app.route('/home')
def home_main():
    try:
        if session.get('user'):
            _p_count = 20 # 몇개의 데이터를 보여줄것인가

            con = mysql.connect()
            cursor = con.cursor()
            cursor.callproc('sp_GetAccountBook', (_p_count,))
            account_book = cursor.fetchall()

            account_list = []
            for account in account_book:
                account_dict = {
                    'account_id':account[0],
                    'account_use_user': account[1],
                    'account_use_description': account[2],
                    'account_use_money': account[3],
                    'account_use_date': account[4],
                    'account_write_date':account[5],
                    'account_write_user':account[6],
                }
                account_list.append(account_dict)

            return render_template('home.html', json_data=account_list, json_count=len(account_list), userName=session.get('name'))
        else:
            return render_template('error.html', error="장부를 볼 권한이 없습니다. 로그인 해주세요")
    except Exception as e:
        return render_template('error.html', error=str(e))


# 장부추가 아직 수정해야함, 예외처리 필요
@app.route('/addAccount', methods=['POST'])
def addAcount():
    try:
         if session.get('user'):

            _use_name = request.form['use_name']
            _use_description = request.form['use_d']
            _use_money = int(request.form['use_money'])
            _use_date = int(request.form['use_date'])
            _write_name = session.get('name')
            _write_date = int(datetime.today().strftime("%Y%m%d"))

            conn = mysql.connect()
            cursor = conn.cursor()

            cursor.callproc('sp_addAccount', (_use_name, _use_description, _use_money, _use_date, _write_date, _write_name))
            data = cursor.fetchall()

            if len(data) is 0:
                conn.commit()
                return redirect('/home')
            else:
                return render_template('error.html', error='An error occurred!')

    except Exception as e:
        print(str(e))
        return render_template('error.html', error=str(e))

# 로그인
@app.route('/intro', methods=['POST','GET'])
def validateLogin():
    if request.method == 'POST':
        try:
            _email = request.form['inputEmail']
            _password = request.form['inputPassword']

            # security
            if sec.check_password(_password, 1) == False or sec.check_password(_email,0) == False:
                return render_template('intro.html', loginError='특수문자를 제외해주세요.')
            if sec.check_null(_email) == False or sec.check_null(_password) == False:
                return render_template('intro.html', loginError='이메일과 비밀번호를 입력해주세요.')

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_validateLogin',(_email,))
            data = cursor.fetchall()

            if len(data) > 0:
                if(check_password_hash(str(data[0][1]), _password)): # user password compared
                    session['user'] = data[0][0] # user email
                    session['name'] = data[0][2] # user name
                    return render_template('intro.html', userName=str(data[0][2]))
                else:
                    return render_template('intro.html', loginError='잘못된 Email이거나 잘못된 Password 입니다')
            else:
                return render_template('intro.html', loginError='잘못된 Email이거나 잘못된 Password 입니다')

        except Exception as e:
            return render_template('error.html', error=str(e))

    else:
        if session.get('user'):
            return render_template('intro.html', userName=str(session['name']))
        else:
            return render_template('intro.html')

# 회원가입
@app.route('/joinIn', methods=['POST', 'GET'])
def joinIn():
        if request.method == 'POST':
            try:
                _email = request.form['inputEmail']
                _password = request.form['inputPassword'] # 특수문자 허용 x
                _name = request.form['inputName']
                _gender = int(request.form['inputGender']) # man=0, woman=1
                _grade = int(0) # default, 관리자=1

                if _email and _password and _name:
                    conn = mysql.connect()
                    cursor = conn.cursor()
                    _hashed_password = generate_password_hash(_password)
                    cursor.callproc('sp_createUser', (_email, _hashed_password, _name, _gender, _grade))
                    data = cursor.fetchall()

                    if len(data) is 0:
                        conn.commit()
                        return render_template('joinSuccess.html',join=_name + " 님의 아이디(이메일)은 '" +  _email + "' 입니다.")
                    else:
                        return render_template('error.html',error=str(data[0]))
                else:
                    return render_template('join.html',error="모든 항목을 다 채워주세요.")

            except Exception as e:
                return render_template('error.html', error=str(e))

        else:
            if session.get('user'):
                return render_template('error.html', error="로그아웃 후 가입을 시도해주세요.")
            else:
                return render_template('join.html', name="join")


# 통계 화면
@app.route('/stat')
def stat():
    return render_template('stat.html', name="stat")

# 로그아웃
@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect('/')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html',error="404 페이지를 찾을 수 없습니다")

if __name__ == '__main__':
    app.run()
