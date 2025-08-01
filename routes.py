from werkzeug.security import generate_password_hash
from forms import RegistrationForm
from app import app
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(
            username=form.username.data,
            password_hash=generate_password_hash(form.password.data),
            email=form.email.data,
            name=form.name.data,
            unit_number=form.unit_number.data or None,
            phone_number=form.phone_number.data or None,
            role='Pending',
            is_admin=False
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registration submitted for approval.', 'success')
        return redirect(url_for('login'))  # or home/dashboard/etc.
    return render_template('register.html', form=form)

@app.route('/admin/approvals')
@login_required
def admin_approvals():
    if not current_user.is_admin and not current_user.is_board:
        flash("Access denied.", "danger")
        return redirect(url_for('index'))

    pending_users = User.query.filter_by(role='Pending').all()
    return render_template('approve_users.html', users=pending_users)

@app.route('/admin/approve_user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if not (current_user.is_admin or current_user.role == 'Board'):
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')

    valid_roles = ['Admin', 'Board', 'Owner', 'Renter', 'Maintenance']
    if new_role not in valid_roles:
        flash("Invalid role selected.", "danger")
        return redirect(url_for('admin_approvals'))

    user.role = new_role
    user.is_admin = (new_role == 'Admin')
    db.session.commit()
    flash(f"{user.name} approved as {new_role}.", "success")
    return redirect(url_for('admin_approvals'))


