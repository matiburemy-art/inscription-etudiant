from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_cle_secrete_super_securisee'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///etudiants.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class Etudiant(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return Etudiant.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        if Etudiant.query.filter_by(username=username).first():
            flash('Cet ID est deja utilise.', 'danger')
            return redirect(url_for('register'))
        nouvel_etudiant = Etudiant(
            username=username,
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
        nouvel_etudiant.set_password(request.form.get('password'))
        db.session.add(nouvel_etudiant)
        db.session.commit()
        flash('Compte cree avec succes !', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == '2005':
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        etudiant = Etudiant.query.filter_by(username=username).first()
        if etudiant and etudiant.check_password(password):
            login_user(etudiant)
            return redirect(url_for('dashboard'))
        else:
            flash('Nom ou mot de passe incorrect', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', etudiant=current_user)

# --- PARTIE ADMIN SEULEMENT ---
@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    etudiants = Etudiant.query.all()
    return render_template('admin_dashboard.html', etudiants=etudiants)

@app.route('/admin/delete/<int:id>')
def delete_etudiant(id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    etudiant = Etudiant.query.get(id)
    if etudiant:
        db.session.delete(etudiant)
        db.session.commit()
        flash('Etudiant supprime', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def edit_etudiant(id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    etudiant = Etudiant.query.get(id)
    if request.method == 'POST':
        etudiant.nom = request.form.get('nom')
        etudiant.prenom = request.form.get('prenom')
        etudiant.post_nom = request.form.get('post_nom')
        etudiant.faculte = request.form.get('faculte')
        etudiant.filiere = request.form.get('filiere')
        etudiant.telephone = request.form.get('telephone')
        etudiant.email = request.form.get('email')
        db.session.commit()
        flash('Modifie avec succes', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit.html', etudiant=etudiant)

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    logout_user()
    return redirect(url_for('index'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
