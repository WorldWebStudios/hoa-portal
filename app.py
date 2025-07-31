import os
import mimetypes
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_required, current_user
from auth import auth, login_manager
from models import db, User, Document
from models import db, User, Document, DownloadLog

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # 🔒 Replace in production

# Database config
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "hoa.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
from flask_migrate import Migrate
migrate = Migrate(app, db)

# File upload config
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'jpg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Auth setup
app.register_blueprint(auth)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Helper to validate file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Dashboard (protected)
@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

# Upload route (admin only)
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if not current_user.is_admin:
        return "Access denied. Admins only.", 403

    if request.method == 'POST':
        if 'files' not in request.files:
            flash('No files part')
            return redirect(request.url)

        uploaded_files = request.files.getlist('files')
        category = request.form.get('category', 'general')
        notes = request.form.get('notes', '')

        if not uploaded_files or uploaded_files[0].filename == '':
            flash('No selected files')
            return redirect(request.url)

        for file in uploaded_files:
            if file and allowed_file(file.filename):
                category_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
                os.makedirs(category_path, exist_ok=True)

                filepath = os.path.join(category_path, file.filename)
                file.save(filepath)

                file_size = os.path.getsize(filepath)

                new_doc = Document(
                    filename=file.filename,
                    category=category,
                    uploader=current_user,
                    notes=notes,
                    filesize=file_size
                )
                db.session.add(new_doc)

        db.session.commit()
        flash(f"{len(uploaded_files)} file(s) uploaded and saved.")
        return redirect(url_for('dashboard'))

    return render_template('upload.html', user=current_user)

# View all uploaded documents (using DB)
from flask import request
from collections import defaultdict
from sqlalchemy import or_

@app.route('/documents')
@login_required
def documents():
    search = request.args.get('search', '').strip().lower()
    selected_category = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Base query (exclude archived files)
    query = Document.query.filter_by(archived=False)


    if search:
        query = query.filter(Document.filename.ilike(f'%{search}%'))

    if selected_category:
        query = query.filter_by(category=selected_category)

    pagination = query.order_by(Document.uploaded_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    paginated_docs = pagination.items

    # Group paginated docs by category
    docs_by_category = defaultdict(list)
    for doc in paginated_docs:
        docs_by_category[doc.category].append(doc)

    # All available categories
    all_categories = db.session.query(Document.category).distinct().all()
    all_categories = [c[0] for c in all_categories]

    return render_template('documents.html',
                           docs=docs_by_category,
                           all_categories=all_categories,
                           user=current_user,
                           pagination=pagination,
                           search=search,
                           selected_category=selected_category)


# File download
@app.route('/download/<category>/<filename>')
@login_required
def download_file(category, filename):
    # Find the document object from DB
    doc = Document.query.filter_by(category=category, filename=filename).first()

    if doc:
        # Log download
        log = DownloadLog(document=doc, user=current_user)
        db.session.add(log)
        db.session.commit()

    return send_from_directory(
        directory=os.path.join(app.config['UPLOAD_FOLDER'], category),
        path=filename,
        as_attachment=True
    )

@app.route('/downloads')
@login_required
def view_downloads():
    if not current_user.is_admin:
        return "Access denied", 403

    logs = DownloadLog.query.order_by(DownloadLog.timestamp.desc()).all()
    return render_template("downloads.html", logs=logs)


# File delete (admin only)
@app.route('/delete/<category>/<filename>', methods=['POST'])
@login_required
def delete_file(category, filename):
    if not current_user.is_admin:
        return "Access denied.", 403

    # Find document in DB
    doc = Document.query.filter_by(category=category, filename=filename, archived=False).first()
    if doc:
        doc.archived = True  # ✅ Mark as archived only
        db.session.commit()
        flash(f"Archived {filename}")
    else:
        flash("Document not found.")

    return redirect(url_for('documents'))

@app.route('/archived')
@login_required
def archived_documents():
    if not current_user.is_admin:
        return "Access denied", 403

    from collections import defaultdict
    docs_by_category = defaultdict(list)

    archived_docs = Document.query.filter_by(archived=True).order_by(Document.uploaded_at.desc()).all()
    for doc in archived_docs:
        docs_by_category[doc.category].append(doc)

    return render_template("archived.html", docs=docs_by_category, user=current_user)

@app.route('/restore/<int:doc_id>', methods=['POST'])
@login_required
def restore_file(doc_id):
    if not current_user.is_admin:
        return "Access denied.", 403

    doc = Document.query.get_or_404(doc_id)
    doc.archived = False
    db.session.commit()
    flash(f"Restored {doc.filename}")
    return redirect(url_for('archived_documents'))

@app.route('/preview/<category>/<filename>')
@login_required
def preview_file(category, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], category, filename)
    mime_type, _ = mimetypes.guess_type(file_path)
    return send_from_directory(
        directory=os.path.join(app.config['UPLOAD_FOLDER'], category),
        path=filename,
        mimetype=mime_type
    )

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return "Access denied.", 403

    from sqlalchemy import func
    from datetime import datetime

    start_date = request.args.get('start')
    end_date = request.args.get('end')
    uploader = request.args.get('uploader')

    # Base query
    query = Document.query.filter_by(archived=False)

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Document.uploaded_at >= start_dt)
        except ValueError:
            flash("Invalid start date format. Use YYYY-MM-DD.")

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Document.uploaded_at <= end_dt)
        except ValueError:
            flash("Invalid end date format. Use YYYY-MM-DD.")

    if uploader:
        query = query.join(User).filter(User.username == uploader)

    total_docs = query.count()
    total_users = User.query.count()

    category_counts = (
        query.with_entities(Document.category, func.count(Document.id))
        .group_by(Document.category)
        .all()
    )

    recent_docs = (
        query.order_by(Document.uploaded_at.desc())
        .limit(5)
        .all()
    )

    all_usernames = [u.username for u in User.query.order_by(User.username).all()]

    return render_template("admin_dashboard.html",
                           total_docs=total_docs,
                           total_users=total_users,
                           category_counts=category_counts,
                           recent_docs=recent_docs,
                           all_usernames=all_usernames,
                           user=current_user,
                           selected_start=start_date,
                           selected_end=end_date,
                           selected_user=uploader)

import routes  # ✅ Registers all routes from routes.py

if __name__ == '__main__':
    app.run(debug=True)

# Run server
if __name__ == '__main__':
    app.run(debug=True)
