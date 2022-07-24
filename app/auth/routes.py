from app import db
from app import login as login_manager
from app.auth import bp
from app.email import send_email
from app.forms import (LoginForm, RegistrationForm, ResetPasswordForm,
                       ResetPasswordRequestForm)
from app.models import User
from flask import (current_app, flash, redirect, render_template, request,
                   url_for)
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.urls import url_parse


@login_manager.unauthorized_handler
def unauthorized_callback():
    if request.method == 'GET':
        return redirect(url_for('auth.login', next=request.path))
    return redirect(url_for('auth.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = LoginForm()
    if form.validate_on_submit():
        user: User = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
        else:
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('main.home')
                
            return redirect(next_page)
    elif form.errors:
        for error in form.errors.values():
            flash(error[0], 'danger')
    return render_template('auth/login.html', title='Sign In', form=form)


@bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return redirect(url_for('main.home'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('A user with that email already exists.', category='danger')
        else:
            login_user(user)
            flash('Congratulations, you are now a registered user!')
            return redirect(url_for('main.home'))

    return render_template('auth/register.html', title='Sign Up',
                           form=form)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if send_password_reset_email(user):
                flash('Email successfully sent.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Error sending email... please try again')
        else:
            flash('No account with that email exists.', 'danger')
    return render_template(
        'auth/reset_password_request.html',
        title='Reset Password',
        form=form
    )


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.home'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Password successfully reset')
        return redirect(url_for('auth.login'))
    else:
        for error in form.errors.values():
            flash(error[0], 'danger')

    return render_template('auth/reset_password.html', title='Reset Password', form=form)


def send_password_reset_email(user: "User"):
    token = user.get_reset_password_token()
    text_body = render_template(
        'email/reset_password.txt', user=user, token=token)
    html_body = render_template(
        'email/reset_password.html', user=user, token=token)

    return send_email(
        'Reset Your Password',
        recipients=[user.email],
        text_body=text_body,
        html_body=html_body
    )
