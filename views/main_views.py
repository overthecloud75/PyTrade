from flask import Blueprint, request, render_template, url_for, current_app, session, g, flash, jsonify
from werkzeug.security import generate_password_hash
from werkzeug.utils import redirect
import json

from datetime import datetime
import functools

from form import UserCreateForm, UserLoginForm
from models import post_sign_up, post_login, get_chart, get_account_list, get_account_info, get_myStock

# blueprint
bp = Blueprint('main', __name__, url_prefix='/')

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('main.login'))
        return view(**kwargs)
    return wrapped_view

@bp.route('/')
def index():
    return render_template('base.html')

@bp.route('/signup/', methods=('GET', 'POST'))
def signup():
    form = UserCreateForm()
    if request.method == 'POST' and form.validate_on_submit():
        request_data = {'name':form.name.data, 'email':form.email.data, 'password':generate_password_hash(form.password1.data)}
        error = post_sign_up(request_data)
        if error:
            flash('이미 존재하는 사용자입니다.')
        else:
            return redirect(url_for('main.index'))
    return render_template('user/signup.html', form=form)

@bp.route('/login/', methods=('GET', 'POST'))
def login():
    form = UserLoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        request_data = {'email': form.email.data, 'password': form.password.data}
        error, user_data = post_login(request_data)
        if error is None:
            del user_data['_id']
            del user_data['password']

            session.clear()
            for key in user_data:
                session[key] = user_data[key]
            return redirect(url_for('main.index'))
        flash(error)
    return render_template('user/login.html', form=form)

@bp.route('/account/')
@login_required
def account():
    page = request.args.get('page', type=int, default=1)
    account_list = get_account_list()
    account_num = account_list[0]
    paging, data_list = get_account_info(account_num, page=page, is_paging=True)
    return render_template('stock/account.html', **locals())

@bp.route('/mystock/')
@login_required
def mystock():
    page = request.args.get('page', type=int, default=1)
    account_list = get_account_list()
    account_num = account_list[0]
    paging, data_list = get_myStock(account_num, page=page, is_paging=True)
    return render_template('stock/mystock.html', **locals())

@bp.route('/logout/')
@login_required
def logout():
    session.clear()
    return redirect(url_for('main.index'))

@bp.route('/chart/')
def chart():
    codeName = request.args.get('kw', default='삼성전자')
    #chart = get_chart('005290', isJson=True)
    #chart = json.dumps(chart)
    data_list = get_chart('005290', isJson=True)
    return render_template('chart.html', **locals())

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = {}
        for key in session:
            g.user[key] = session[key]

