from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import traceback

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ugl_2025_secret_pro_max'

database_url = os.environ.get('DATABASE_URL')
if database_url:
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///etudiants.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ===================== MODELS =====================
class Etudiant(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    matricule = db.Column(db.String(20), unique=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=False)
    post_nom = db.Column(db.String(50), nullable=False)
    date_naissance = db.Column(db.String(20), nullable=False)
    nationalite = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    faculte = db.Column(db.String(50), nullable=False)
    filiere = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    edit_count = db.Column(db.Integer, default=0)

    def set_password(self, p):
        self.password_hash = generate_password_hash(p)
    def check_password(self, p):
        return check_password_hash(self.password_hash, p)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(20), db.ForeignKey('etudiant.matricule'), nullable=False)
    cours = db.Column(db.String(100), nullable=False)
    note = db.Column(db.Float, nullable=False)
    date_ajout = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return Etudiant.query.get(int(user_id))

def admin_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            flash("Accès admin requis", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def generer_matricule():
    try:
        annee = datetime.now().year
        pattern = f"UGL-{annee}-%"
        dernier = Etudiant.query.filter(Etudiant.matricule.like(pattern)).order_by(Etudiant.id.desc()).first()
        if dernier and dernier.matricule and "-" in dernier.matricule:
            num = int(dernier.matricule.split("-")[-1]) + 1
        else:
            num = Etudiant.query.count() + 1
        return f"UGL-{annee}-{num:04d}"
    except Exception as e:
        print(f"Erreur generer_matricule: {e}")
        return f"UGL-{datetime.now().year}-0001"

# ===================== ROUTES PUBLIQUES =====================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    matricule_preview = generer_matricule()
    if request.method == 'POST':
        try:
            if Etudiant.query.filter_by(email=request.form.get('email')).first():
                flash('Email deja utilisé', 'danger')
                return render_template('register.html', matricule_preview=matricule_preview)
            
            matricule_final = generer_matricule()
            et = Etudiant(
                matricule=matricule_final,
                username=matricule_final,
                nom=request.form.get('nom'),
                prenom=request.form.get('prenom'),
                post_nom=request.form.get('post_nom'),
                date_naissance=request.form.get('date_naissance'),
                nationalite=request.form.get('nationalite'),
                email=request.form.get('email'),
                telephone=request.form.get('telephone'),
                faculte=request.form.get('faculte'),
                filiere=request.form.get('filiere')
            )
            et.set_password(request.form.get('password'))
            db.session.add(et)
            db.session.commit()
            return redirect(url_for('login', matricule=matricule_final))
        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            flash(f"Erreur: {e}", "danger")
    return render_template('register.html', matricule_preview=matricule_preview)

@app.route('/login', methods=['GET', 'POST'])
def login():
    matricule_from_register = request.args.get('matricule', '')
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        if u == 'admin' and p == 'Matibu@2005':
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        et = Etudiant.query.filter_by(username=u).first()
        if et and et.check_password(p):
            login_user(et)
            return redirect(url_for('dashboard'))
        flash('Identifiants incorrects', 'danger')
    return render_template('login.html', matricule_prefill=matricule_from_register)

@app.route('/dashboard')
@login_required
def dashboard():
    notes = Note.query.filter_by(matricule=current_user.matricule).all()
    return render_template('dashboard.html', etudiant=current_user, notes=notes)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if current_user.edit_count >= 1:
        flash("Vous avez deja utilisé votre modification", "danger")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        try:
            current_user.nom = request.form.get('nom')
            current_user.prenom = request.form.get('prenom')
            current_user.post_nom = request.form.get('post_nom')
            current_user.telephone = request.form.get('telephone')
            current_user.email = request.form.get('email')
            current_user.faculte = request.form.get('faculte')
            current_user.filiere = request.form.get('filiere')
            current_user.nationalite = request.form.get('nationalite')
            current_user.edit_count = 1
            db.session.commit()
            flash("Profil modifié!", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur: {e}", "danger")
    return render_template('edit_profile.html', etudiant=current_user)

# ===================== ADMIN =====================
@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    etudiants = Etudiant.query.all()
    return render_template('admin_dashboard.html', etudiants=etudiants)

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_etudiant(id):
    et = Etudiant.query.get_or_404(id)
    if request.method == 'POST':
        et.nom = request.form.get('nom')
        et.prenom = request.form.get('prenom')
        et.post_nom = request.form.get('post_nom')
        et.telephone = request.form.get('telephone')
        et.email = request.form.get('email')
        et.faculte = request.form.get('faculte')
        et.filiere = request.form.get('filiere')
        et.nationalite = request.form.get('nationalite')
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_edit.html', etudiant=et)

@app.route('/admin/delete/<int:id>')
@admin_required
def delete_etudiant(id):
    et = Etudiant.query.get(id)
    if et:
        db.session.delete(et)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

# ===================== NOUVEAU: NOTES ETUDIANTS (SEUL ADMIN) =====================
@app.route('/notes-etudiants')
@admin_required
def notes_etudiants():
    return render_template('notes_etudiants.html')

@app.route('/api/chercher-etudiant/<matricule>')
@admin_required
def chercher_etudiant_api(matricule):
    etu = Etudiant.query.filter_by(matricule=matricule).first()
    if not etu:
        return jsonify({"found": False})
    notes = Note.query.filter_by(matricule=matricule).all()
    return jsonify({
        "found": True,
        "etudiant": {
            "matricule": etu.matricule, "nom": etu.nom, "prenom": etu.prenom,
            "post_nom": etu.post_nom, "email": etu.email, "telephone": etu.telephone,
            "faculte": etu.faculte, "filiere": etu.filiere, "nationalite": etu.nationalite,
            "date_naissance": etu.date_naissance
        },
        "notes": [{"id": n.id, "cours": n.cours, "note": n.note} for n in notes]
    })

@app.route('/api/ajouter-note', methods=['POST'])
@admin_required
def ajouter_note_api():
    data = request.json
    nouvelle = Note(matricule=data['matricule'], cours=data['cours'], note=float(data['note']))
    db.session.add(nouvelle)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/modifier-note/<int:id>', methods=['PUT'])
@admin_required
def modifier_note_api(id):
    n = Note.query.get_or_404(id)
    data = request.json
    n.cours = data.get('cours', n.cours)
    n.note = float(data.get('note', n.note))
    db.session.commit()
    return jsonify({"success": True})   

@app.route('/api/supprimer-note/<int:id>', methods=['DELETE'])
@admin_required
def supprimer_note_api(id):
    n = Note.query.get(id)
    if n:
        db.session.delete(n)
        db.session.commit()
    return jsonify({"success": True})

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    logout_user()
    return redirect(url_for('index'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        if 'new_password' in request.form:
            email = session.get('reset_email')
            if not email:
                flash("Session expirée", "danger")
                return redirect(url_for('forgot_password'))
            if request.form.get('new_password') != request.form.get('confirm_password'):
                flash("Mots de passe différents", "danger")
                return render_template('reset_password.html', email=email)
            etu = Etudiant.query.filter_by(email=email).first()
            if etu:
                etu.set_password(request.form.get('new_password'))
                db.session.commit()
                session.pop('reset_email', None)
                flash("Mot de passe réinitialisé!", "success")
                return redirect(url_for('login'))
        elif 'email' in request.form:
            etu = Etudiant.query.filter_by(email=request.form.get('email')).first()
            if etu:
                session['reset_email'] = etu.email
                return render_template('reset_password.html', email=etu.email)
            else:
                flash("Aucun compte avec ce Gmail", "danger")
    return render_template('forgot_password.html')

@app.route('/reset-db-ugl-2026')
def reset_db():
    try:
        db.drop_all()
        db.create_all()
        return "Base effacée et recréée! Va sur /register"
    except Exception as e:
        return f"Erreur reset: {e}"

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
