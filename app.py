from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import os
import traceback

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ugl_2025_secret'
app.config['SECRET_KEY'] = 'cle_super_secrete'
database_url = os.environ.get('DATABASE_URL')
if database_url:
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///etudiants.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy()
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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
    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)

@login_manager.user_loader
def load_user(user_id):
    return Etudiant.query.get(int(user_id))

def generer_matricule():
    try:
        annee = datetime.now().year
        dernier = Etudiant.query.filter(Etudiant.matricule.like(f"UGL-{annee}-%")).order_by(Etudiant.id.desc()).first()
        if dernier and dernier.matricule and "-" in dernier.matricule:
            num = int(dernier.matricule.split("-")[-1]) + 1
        else:
            total = Etudiant.query.count()
            num = total + 1
        return f"UGL-{annee}-{num:04d}"
    except Exception as e:
        print(f"Erreur generer_matricule: {e}")
        traceback.print_exc()
        return f"UGL-{datetime.now().year}-0001"

@app.route('/')
def index(): return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    matricule_preview = generer_matricule()
    if request.method == 'POST':
        try:
            matricule_final = generer_matricule()
            if Etudiant.query.filter_by(email=request.form.get('email')).first():
                flash('Email deja utilise', 'danger')
                return render_template('register.html', matricule_preview=matricule_preview)
            et = Etudiant(
                matricule=matricule_final,
                username=matricule_final,
                nom=request.form.get('nom'), prenom=request.form.get('prenom'),
                post_nom=request.form.get('post_nom'), date_naissance=request.form.get('date_naissance'),
                nationalite=request.form.get('nationalite'), email=request.form.get('email'),
                telephone=request.form.get('telephone'), faculte=request.form.get('faculte'),
                filiere=request.form.get('filiere')
            )
            et.set_password(request.form.get('password'))
            db.session.add(et)
            db.session.commit()
            # MODIF 1: On passe l'ID au login automatiquement
            return redirect(url_for('login', matricule=matricule_final))
        except Exception as e:
            db.session.rollback()
            print("ERREUR REGISTER POST:", e)
            traceback.print_exc()
            flash(f"Erreur interne: {e}", "danger")
            return render_template('register.html', matricule_preview=matricule_preview)
    return render_template('register.html', matricule_preview=matricule_preview)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # MODIF 2: Récupère le matricule qui vient de l'inscription
    matricule_from_register = request.args.get('matricule', '')
    if request.method == 'POST':
        u = request.form.get('username'); p = request.form.get('password')
        if u == 'admin' and p == '2005':
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
def dashboard(): return render_template('dashboard.html', etudiant=current_user)

# MODIF 3: ROUTE QUI MANQUAIT - C'est pour ça que Modifier ne marchait pas !
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if current_user.edit_count >= 1:
        flash("Vous avez déjà utilisé votre modification", "danger")
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
            flash("Profil modifié avec succès!", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur: {e}", "danger")
    return render_template('edit_profile.html', etudiant=current_user)

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('is_admin'): return redirect(url_for('login'))
    return render_template('admin_dashboard.html', etudiants=Etudiant.query.all())

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit_etudiant(id):
    if not session.get('is_admin'): return redirect(url_for('login'))
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
def delete_etudiant(id):
    if not session.get('is_admin'): return redirect(url_for('login'))
    et = Etudiant.query.get(id)
    if et: db.session.delete(et); db.session.commit()
    return redirect(url_for('admin_dashboard'))
    
@app.route('/logout')
def logout():
    session.pop('is_admin', None); logout_user()
    return redirect(url_for('index'))

@app.route('/reset-db-ugl-2026')
def reset_db():
    try:
        db.drop_all()
        db.create_all()
        return "Base effacee et recreee avec succes! Va sur /register maintenant."
    except Exception as e:
        return f"Erreur reset: {e}"

with app.app_context():
    db.create_all()
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        # ÉTAPE 2 : Il change le mot de passe
        if 'new_password' in request.form:
            email = session.get('reset_email')
            if not email:
                flash("Session expirée, recommence", "danger")
                return redirect(url_for('forgot_password'))
            
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if new_password != confirm_password:
                flash("Les mots de passe ne correspondent pas", "danger")
                return render_template('reset_password.html', email=email)
            
            etudiant = Etudiant.query.filter_by(email=email).first()
            if etudiant:
                etudiant.password_hash = generate_password_hash(new_password)
                db.session.commit()
                session.pop('reset_email', None)
                flash("Mot de passe réinitialisé avec succès !", "success")
                return redirect(url_for('login'))
            else:
                flash("Compte non trouvé", "danger")
                return redirect(url_for('forgot_password'))

        # ÉTAPE 1 : Il entre son Gmail
        elif 'email' in request.form:
            email = request.form.get('email')
            etudiant = Etudiant.query.filter_by(email=email).first()
            if etudiant:
                session['reset_email'] = email
                return render_template('reset_password.html', email=email)
            else:
                flash("Aucun compte avec ce Gmail", "danger")

    return render_template('forgot_password.html')

if __name__ == '__main__':
    app.run(debug=True)
