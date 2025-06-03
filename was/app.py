from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
import os
import uuid
import threading
import time
from PIL import Image
import logging
import json
import traceback

# Flask-WTF 추가 import
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_wtf.csrf import CSRFProtect, CSRFError
from wtforms import StringField, TextAreaField, SelectField, DateField, IntegerField, BooleanField, URLField
from wtforms.validators import DataRequired, Length, Optional, URL, ValidationError

app = Flask(__name__)

# Logging 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:1234@mysql:3306/portfolio')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# CSRF 보호 활성화
csrf = CSRFProtect(app)

# 데이터베이스 초기화 상태를 추적하는 전역 변수
_db_initialized = False
_db_lock = threading.Lock()

# 기존 모델들 (그대로 유지)
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    detailed_description = db.Column(db.Text)
    
    project_type = db.Column(db.String(50), index=True)
    category = db.Column(db.String(100), index=True)
    
    tech_stack = db.Column(db.Text)
    github_url = db.Column(db.String(500))
    demo_url = db.Column(db.String(500))
    
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    team_size = db.Column(db.Integer)
    my_role = db.Column(db.String(200))
    
    achievements = db.Column(db.Text)
    metrics = db.Column(db.Text)
    
    image_path = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    document_path = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_featured = db.Column(db.Boolean, default=False, index=True)
    is_public = db.Column(db.Boolean, default=True, index=True)
    sort_order = db.Column(db.Integer, default=0, index=True)
    
    view_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)

class TechStack(db.Model):
    __tablename__ = 'tech_stacks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    category = db.Column(db.String(50), index=True)
    icon_class = db.Column(db.String(100))
    color = db.Column(db.String(7))
    proficiency = db.Column(db.Integer, default=0)
    years_experience = db.Column(db.Float, default=0)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Experience(db.Model):
    __tablename__ = 'experiences'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    company = db.Column(db.String(200))
    location = db.Column(db.String(200))
    description = db.Column(db.Text)
    
    experience_type = db.Column(db.String(50), index=True)
    
    start_date = db.Column(db.Date, index=True)
    end_date = db.Column(db.Date)
    is_current = db.Column(db.Boolean, default=False)
    
    skills_used = db.Column(db.Text)
    achievements = db.Column(db.Text)
    image_path = db.Column(db.String(500))
    link_url = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class Certification(db.Model):
    __tablename__ = 'certifications'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    issuer = db.Column(db.String(200), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    expire_date = db.Column(db.Date)
    credential_id = db.Column(db.String(200))
    credential_url = db.Column(db.String(500))
    
    category = db.Column(db.String(100), index=True)
    
    image_path = db.Column(db.String(500))
    document_path = db.Column(db.String(500))
    
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DatabaseLock(db.Model):
    __tablename__ = 'database_locks'
    
    id = db.Column(db.Integer, primary_key=True)
    lock_name = db.Column(db.String(100), unique=True, nullable=False)
    locked_by = db.Column(db.String(100), nullable=False)
    locked_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

# Flask-WTF 폼 클래스 추가
class ProjectForm(FlaskForm):
    title = StringField('프로젝트명', 
                       validators=[DataRequired(message='프로젝트명을 입력해주세요.'), 
                                 Length(min=5, max=200, message='프로젝트명은 5-200자 사이여야 합니다.')])
    
    description = TextAreaField('간단한 설명', 
                              validators=[DataRequired(message='프로젝트 설명을 입력해주세요.'), 
                                        Length(min=20, max=1000, message='설명은 20-1000자 사이여야 합니다.')])
    
    detailed_description = TextAreaField('상세 설명', 
                                       validators=[Optional(), 
                                                 Length(max=5000, message='상세 설명은 5000자를 초과할 수 없습니다.')])
    
    project_type = SelectField('프로젝트 유형', 
                              choices=[('', '선택하세요'),
                                     ('tech', '웹/앱 개발'),
                                     ('infra', '인프라/DevOps'),
                                     ('data', '데이터 분석'),
                                     ('ai', 'AI/ML'),
                                     ('art', '아트워크')],
                              validators=[DataRequired(message='프로젝트 유형을 선택해주세요.')])
    
    category = StringField('세부 카테고리', 
                          validators=[Optional(), 
                                    Length(max=100, message='카테고리는 100자를 초과할 수 없습니다.')])
    
    my_role = StringField('내 역할', 
                         validators=[Optional(), 
                                   Length(max=200, message='역할은 200자를 초과할 수 없습니다.')])
    
    tech_stack = StringField('기술 스택', 
                           validators=[Optional(), 
                                     Length(max=500, message='기술 스택은 500자를 초과할 수 없습니다.')])
    
    github_url = URLField('GitHub URL', 
                         validators=[Optional(), 
                                   URL(message='올바른 GitHub URL을 입력해주세요.')])
    
    demo_url = URLField('데모 URL', 
                       validators=[Optional(), 
                                 URL(message='올바른 데모 URL을 입력해주세요.')])
    
    video_url = URLField('비디오 URL', 
                        validators=[Optional(), 
                                  URL(message='올바른 비디오 URL을 입력해주세요.')])
    
    start_date = DateField('시작일', validators=[Optional()])
    end_date = DateField('종료일', validators=[Optional()])
    
    team_size = IntegerField('팀 규모', 
                           validators=[Optional()], 
                           render_kw={"min": 1, "max": 100})
    
    achievements = TextAreaField('주요 성과', 
                               validators=[Optional(), 
                                         Length(max=2000, message='성과는 2000자를 초과할 수 없습니다.')])
    
    metrics = TextAreaField('정량적 지표', 
                          validators=[Optional(), 
                                    Length(max=1000, message='지표는 1000자를 초과할 수 없습니다.')])
    
    image = FileField('프로젝트 이미지', 
                     validators=[Optional(), 
                               FileAllowed(['jpg', 'png', 'gif', 'jpeg'], 
                                         '이미지 파일만 업로드 가능합니다! (jpg, png, gif, jpeg)')])
    
    is_featured = BooleanField('주요 프로젝트로 설정', default=False)
    is_public = BooleanField('공개 프로젝트', default=True)
    sort_order = IntegerField('정렬 순서', 
                            validators=[Optional()], 
                            default=0,
                            render_kw={"min": 0})

    def validate_end_date(self, field):
        """종료일 유효성 검사"""
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('종료일은 시작일보다 늦어야 합니다.')

    def validate_team_size(self, field):
        """팀 규모 유효성 검사"""
        if field.data is not None and (field.data < 1 or field.data > 100):
            raise ValidationError('팀 규모는 1-100명 사이여야 합니다.')

# 기존 함수들 (그대로 유지)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_instance_id():
    return f"{os.getpid()}_{int(time.time() * 1000)}"

def acquire_db_lock(lock_name, timeout=300):
    instance_id = get_instance_id()
    expires_at = datetime.utcnow() + timedelta(seconds=timeout)
    
    try:
        db.session.query(DatabaseLock).filter(
            DatabaseLock.expires_at < datetime.utcnow()
        ).delete()
        
        lock = DatabaseLock(
            lock_name=lock_name,
            locked_by=instance_id,
            expires_at=expires_at
        )
        db.session.add(lock)
        db.session.commit()
        logger.info(f"Lock '{lock_name}' acquired by {instance_id}")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.info(f"Failed to acquire lock '{lock_name}': {e}")
        return False

def release_db_lock(lock_name):
    instance_id = get_instance_id()
    try:
        db.session.query(DatabaseLock).filter(
            DatabaseLock.lock_name == lock_name,
            DatabaseLock.locked_by == instance_id
        ).delete()
        db.session.commit()
        logger.info(f"Lock '{lock_name}' released by {instance_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to release lock '{lock_name}': {e}")

def safe_init_db():
    global _db_initialized
    
    if _db_initialized:
        return True
        
    with _db_lock:
        if _db_initialized:
            return True
            
        logger.info("Attempting to initialize database...")
        
        max_retries = 10
        for attempt in range(max_retries):
            try:
                db.session.execute(db.text('SELECT 1'))
                db.session.commit()
                logger.info("Database connection successful")
                break
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error("Failed to connect to database after all retries")
                    return False
                time.sleep(2)
        
        try:
            DatabaseLock.__table__.create(db.engine, checkfirst=True)
            logger.info("DatabaseLock table created/verified")
        except Exception as e:
            logger.error(f"Failed to create DatabaseLock table: {e}")
            return False
        
        if not acquire_db_lock('db_init', timeout=180):
            logger.info("Another instance is initializing the database, waiting...")
            for _ in range(60):
                time.sleep(1)
                try:
                    db.session.execute(db.text("SELECT 1 FROM users LIMIT 1"))
                    logger.info("Database initialization completed by another instance")
                    _db_initialized = True
                    return True
                except:
                    continue
            
            logger.warning("Timeout waiting for database initialization")
            return False
        
        try:
            db.create_all()
            logger.info("Database tables created")
            
            init_default_data()
            
            _db_initialized = True
            logger.info("Database initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            db.session.rollback()
            return False
        finally:
            release_db_lock('db_init')

def init_default_data():
    try:
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            logger.info("Admin user created")
        
        default_tech_stacks = [
            {'name': 'Python', 'category': 'language', 'icon_class': 'fab fa-python', 'color': '#3776ab', 'proficiency': 90, 'is_primary': True},
            {'name': 'JavaScript', 'category': 'language', 'icon_class': 'fab fa-js-square', 'color': '#f7df1e', 'proficiency': 85, 'is_primary': True},
            {'name': 'Java', 'category': 'language', 'icon_class': 'fab fa-java', 'color': '#ed8b00', 'proficiency': 80},
            {'name': 'Go', 'category': 'language', 'icon_class': 'fas fa-code', 'color': '#00add8', 'proficiency': 75},
            {'name': 'Django', 'category': 'framework', 'icon_class': 'fas fa-server', 'color': '#092e20', 'proficiency': 85},
            {'name': 'Flask', 'category': 'framework', 'icon_class': 'fas fa-flask', 'color': '#000000', 'proficiency': 90},
            {'name': 'React', 'category': 'framework', 'icon_class': 'fab fa-react', 'color': '#61dafb', 'proficiency': 80, 'is_primary': True},
            {'name': 'Vue.js', 'category': 'framework', 'icon_class': 'fab fa-vuejs', 'color': '#4fc08d', 'proficiency': 75},
            {'name': 'PostgreSQL', 'category': 'database', 'icon_class': 'fas fa-database', 'color': '#336791', 'proficiency': 85},
            {'name': 'MySQL', 'category': 'database', 'icon_class': 'fas fa-database', 'color': '#4479a1', 'proficiency': 90},
            {'name': 'MongoDB', 'category': 'database', 'icon_class': 'fas fa-leaf', 'color': '#47a248', 'proficiency': 80},
            {'name': 'Redis', 'category': 'database', 'icon_class': 'fas fa-memory', 'color': '#dc382d', 'proficiency': 85},
            {'name': 'AWS', 'category': 'cloud', 'icon_class': 'fab fa-aws', 'color': '#ff9900', 'proficiency': 85, 'is_primary': True},
            {'name': 'Google Cloud', 'category': 'cloud', 'icon_class': 'fab fa-google', 'color': '#4285f4', 'proficiency': 80},
            {'name': 'Azure', 'category': 'cloud', 'icon_class': 'fab fa-microsoft', 'color': '#0078d4', 'proficiency': 75},
            {'name': 'Docker', 'category': 'devops', 'icon_class': 'fab fa-docker', 'color': '#2496ed', 'proficiency': 90, 'is_primary': True},
            {'name': 'Kubernetes', 'category': 'devops', 'icon_class': 'fas fa-dharmachakra', 'color': '#326ce5', 'proficiency': 85, 'is_primary': True},
            {'name': 'Jenkins', 'category': 'devops', 'icon_class': 'fas fa-tools', 'color': '#d33833', 'proficiency': 80},
            {'name': 'Terraform', 'category': 'devops', 'icon_class': 'fas fa-layer-group', 'color': '#623ce4', 'proficiency': 85},
            {'name': 'Pandas', 'category': 'data', 'icon_class': 'fas fa-chart-bar', 'color': '#150458', 'proficiency': 90},
            {'name': 'NumPy', 'category': 'data', 'icon_class': 'fas fa-calculator', 'color': '#013243', 'proficiency': 85},
            {'name': 'TensorFlow', 'category': 'ai', 'icon_class': 'fas fa-brain', 'color': '#ff6f00', 'proficiency': 80},
            {'name': 'PyTorch', 'category': 'ai', 'icon_class': 'fas fa-fire', 'color': '#ee4c2c', 'proficiency': 75},
        ]
        
        for tech_data in default_tech_stacks:
            existing = TechStack.query.filter_by(name=tech_data['name']).first()
            if not existing:
                tech = TechStack(**tech_data)
                db.session.add(tech)
        
        default_certifications = [
            {
                'name': 'AWS Certified Solutions Architect',
                'issuer': 'Amazon Web Services',
                'issue_date': date(2023, 6, 15),
                'category': 'cloud',
                'is_featured': True
            },
            {
                'name': 'Certified Kubernetes Administrator (CKA)',
                'issuer': 'Cloud Native Computing Foundation',
                'issue_date': date(2023, 8, 20),
                'category': 'devops',
                'is_featured': True
            },
            {
                'name': '정보처리기사',
                'issuer': '한국산업인력공단',
                'issue_date': date(2022, 11, 25),
                'category': 'general',
                'is_featured': True
            }
        ]
        
        for cert_data in default_certifications:
            existing = Certification.query.filter_by(name=cert_data['name']).first()
            if not existing:
                cert = Certification(**cert_data)
                db.session.add(cert)
        
        db.session.commit()
        logger.info("Default data initialized")
    except Exception as e:
        logger.error(f"Failed to initialize default data: {e}")
        db.session.rollback()

# 유틸리티 함수들 추가
def handle_image_upload(file):
    """이미지 파일 업로드 처리"""
    try:
        if not file or not file.filename:
            return None
        
        filename = secure_filename(file.filename)
        if not filename:
            logger.error("잘못된 파일명")
            return None
        
        if not allowed_file(filename):
            logger.error(f"허용되지 않는 파일 형식: {filename}")
            return None
        
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}{ext}"
        
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        optimize_image(file_path)
        
        logger.info(f"이미지 업로드 성공: {unique_filename}")
        return unique_filename
        
    except Exception as e:
        logger.error(f"이미지 업로드 실패: {str(e)}", exc_info=True)
        return None

def optimize_image(file_path):
    """이미지 최적화"""
    try:
        with Image.open(file_path) as img:
            if img.width > 1200:
                ratio = 1200 / img.width
                new_height = int(img.height * ratio)
                img = img.resize((1200, new_height), Image.Resampling.LANCZOS)
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            img.save(file_path, format='JPEG', optimize=True, quality=85)
            
    except Exception as e:
        logger.warning(f"이미지 최적화 실패: {str(e)}")

def allowed_file(filename):
    """허용되는 파일 확장자 검사"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_recent_works():
    """최근 추가된 프로젝트 가져오기"""
    try:
        return Project.query.order_by(Project.created_at.desc()).limit(3).all()
    except Exception as e:
        logger.error(f"최근 프로젝트 조회 실패: {str(e)}")
        return []

# 기존 라우트들 (그대로 유지)
@app.route('/')
def index():
    featured_projects = Project.query.filter_by(is_featured=True, is_public=True)\
                                   .order_by(Project.sort_order, Project.created_at.desc())\
                                   .limit(6).all()
    
    recent_projects = Project.query.filter_by(is_public=True)\
                                 .order_by(Project.created_at.desc())\
                                 .limit(8).all()
    
    primary_techs = TechStack.query.filter_by(is_primary=True)\
                                 .order_by(TechStack.proficiency.desc())\
                                 .limit(8).all()
    
    recent_experiences = Experience.query.filter(Experience.experience_type.in_(['work', 'education']))\
                                       .order_by(Experience.start_date.desc())\
                                       .limit(3).all()
    
    return render_template('index.html', 
                         featured_projects=featured_projects,
                         recent_projects=recent_projects,
                         primary_techs=primary_techs,
                         recent_experiences=recent_experiences)

@app.route('/portfolio')
def portfolio():
    project_type = request.args.get('type', 'all')
    category = request.args.get('category', 'all')
    
    query = Project.query.filter_by(is_public=True)
    
    if project_type != 'all':
        query = query.filter_by(project_type=project_type)
    
    if category != 'all':
        query = query.filter_by(category=category)
    
    projects = query.order_by(Project.sort_order, Project.created_at.desc()).all()
    
    project_types = db.session.query(Project.project_type, db.func.count(Project.id))\
                             .filter_by(is_public=True)\
                             .group_by(Project.project_type)\
                             .all()
    
    categories = db.session.query(Project.category, db.func.count(Project.id))\
                          .filter_by(is_public=True)\
                          .group_by(Project.category)\
                          .all()
    
    return render_template('portfolio.html', 
                         projects=projects,
                         project_types=dict(project_types),
                         categories=dict(categories),
                         current_type=project_type,
                         current_category=category)

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    
    if not project.is_public and (not current_user.is_authenticated or not current_user.is_admin):
        flash('접근 권한이 없습니다.', 'error')
        return redirect(url_for('portfolio'))
    
    project.view_count += 1
    db.session.commit()
    
    related_projects = Project.query.filter(
        Project.id != project_id,
        Project.category == project.category,
        Project.is_public == True
    ).order_by(Project.created_at.desc()).limit(3).all()
    
    return render_template('project_detail.html', 
                         project=project,
                         related_projects=related_projects)

@app.route('/about')
def about():
    work_experiences = Experience.query.filter_by(experience_type='work')\
                                     .order_by(Experience.start_date.desc()).all()
    
    education_experiences = Experience.query.filter_by(experience_type='education')\
                                          .order_by(Experience.start_date.desc()).all()
    
    certifications = Certification.query.order_by(Certification.issue_date.desc()).all()
    
    tech_categories = ['language', 'framework', 'database', 'cloud', 'devops', 'data', 'ai', 'tool']
    tech_stacks = {}
    for category in tech_categories:
        tech_stacks[category] = TechStack.query.filter_by(category=category)\
                                             .order_by(TechStack.proficiency.desc()).all()
    
    return render_template('about.html',
                         work_experiences=work_experiences,
                         education_experiences=education_experiences,
                         certifications=certifications,
                         tech_stacks=tech_stacks)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('index'))
    
    projects = Project.query.order_by(Project.created_at.desc()).all()
    tech_stacks = TechStack.query.order_by(TechStack.proficiency.desc()).all()
    certifications = Certification.query.order_by(Certification.issue_date.desc()).all()
    experiences = Experience.query.order_by(Experience.created_at.desc()).all()
    
    return render_template('admin.html', 
                         works=projects,  # 기존 템플릿 호환성을 위해 works로도 전달
                         projects=projects,
                         tech_stacks=tech_stacks,
                         certifications=certifications,
                         experiences=experiences)

# 개선된 add_work 함수 (기존 함수 완전 교체)
@app.route('/admin/add_work', methods=['GET', 'POST'])
@login_required
def add_work():
    """새 프로젝트 추가"""
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('index'))
    
    form = ProjectForm()
    
    if request.method == 'POST':
        logger.info(f"프로젝트 추가 요청 - 사용자: {current_user.username}")
        
        # 폼 유효성 검사
        if form.validate_on_submit():
            try:
                # 이미지 파일 처리
                image_path = None
                if form.image.data:
                    image_path = handle_image_upload(form.image.data)
                    if not image_path:
                        flash('이미지 업로드에 실패했습니다.', 'error')
                        return render_template('add_work.html', form=form, recent_works=get_recent_works())
                
                # 프로젝트 데이터 생성
                project_data = {
                    'title': form.title.data.strip(),
                    'description': form.description.data.strip(),
                    'detailed_description': form.detailed_description.data.strip() if form.detailed_description.data else None,
                    'project_type': form.project_type.data,
                    'category': form.category.data.strip() if form.category.data else None,
                    'tech_stack': form.tech_stack.data.strip() if form.tech_stack.data else None,
                    'github_url': form.github_url.data if form.github_url.data else None,
                    'demo_url': form.demo_url.data if form.demo_url.data else None,
                    'video_url': form.video_url.data if form.video_url.data else None,
                    'start_date': form.start_date.data,
                    'end_date': form.end_date.data,
                    'team_size': form.team_size.data,
                    'my_role': form.my_role.data.strip() if form.my_role.data else None,
                    'achievements': form.achievements.data.strip() if form.achievements.data else None,
                    'metrics': form.metrics.data.strip() if form.metrics.data else None,
                    'image_path': image_path,
                    'is_featured': form.is_featured.data,
                    'is_public': form.is_public.data,
                    'sort_order': form.sort_order.data or 0
                }
                
                # 프로젝트 생성
                project = Project(**project_data)
                
                # 데이터베이스에 저장
                db.session.add(project)
                db.session.commit()
                
                logger.info(f"새 프로젝트 추가됨: {project.title} (ID: {project.id})")
                
                # AJAX 요청인 경우 JSON 응답
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True, 
                        'message': '프로젝트가 성공적으로 추가되었습니다.',
                        'project_id': project.id,
                        'redirect_url': url_for('admin')
                    })
                
                flash('프로젝트가 성공적으로 추가되었습니다!', 'success')
                return redirect(url_for('admin'))
                
            except Exception as e:
                db.session.rollback()
                error_msg = f"프로젝트 추가 중 오류가 발생했습니다: {str(e)}"
                logger.error(f"프로젝트 추가 오류: {str(e)}", exc_info=True)
                
                # 업로드된 이미지 파일 정리 (오류 발생시)
                if 'image_path' in locals() and image_path:
                    try:
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_path)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception as cleanup_error:
                        logger.error(f"이미지 파일 정리 실패: {cleanup_error}")
                
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False, 
                        'message': error_msg
                    }), 500
                
                flash(error_msg, 'error')
        
        else:
            # 폼 유효성 검사 실패
            logger.warning(f"폼 유효성 검사 실패: {form.errors}")
            
            # 에러 메시지를 플래시 메시지로 표시
            for field_name, errors in form.errors.items():
                field_label = getattr(form, field_name).label.text if hasattr(form, field_name) else field_name
                for error in errors:
                    flash(f'{field_label}: {error}', 'error')
            
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': '입력한 정보를 다시 확인해주세요.',
                    'errors': form.errors
                }), 400
    
    # GET 요청이거나 오류 발생시
    recent_works = get_recent_works()
    return render_template('add_work.html', form=form, recent_works=recent_works)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/health')
def health():
    """애플리케이션 상태 확인"""
    try:
        # 데이터베이스 연결 확인
        db.session.execute(db.text('SELECT 1'))
        db.session.commit()
        db_status = 'healthy'
        
        # 업로드 폴더 확인
        upload_dir_exists = os.path.exists(app.config['UPLOAD_FOLDER'])
        upload_dir_writable = os.access(app.config['UPLOAD_FOLDER'], os.W_OK) if upload_dir_exists else False
        
        upload_status = 'healthy' if upload_dir_exists and upload_dir_writable else 'warning'
        
        # 기본 데이터 확인
        user_count = User.query.count()
        project_count = Project.query.count()
        
        return jsonify({
            'status': 'healthy',
            'database': db_status,
            'upload_directory': upload_status,
            'upload_path': app.config['UPLOAD_FOLDER'],
            'upload_exists': upload_dir_exists,
            'upload_writable': upload_dir_writable,
            'statistics': {
                'users': user_count,
                'projects': project_count
            },
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
        
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/readiness')
def readiness():
    if not _db_initialized:
        return jsonify({'status': 'not ready', 'reason': 'database not initialized'}), 503
    
    try:
        User.query.first()
        return jsonify({'status': 'ready', 'timestamp': datetime.utcnow().isoformat()})
    except Exception as e:
        return jsonify({'status': 'not ready', 'reason': str(e)}), 503

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin'))
        else:
            flash('잘못된 사용자명 또는 비밀번호입니다.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/delete_work/<int:work_id>', methods=['DELETE'])
@login_required
def delete_work(work_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    try:
        project = Project.query.get_or_404(work_id)
        
        # 이미지 파일 삭제
        if project.image_path:
            try:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], project.image_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Failed to delete image file: {e}")
        
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '프로젝트가 삭제되었습니다.'})
    except Exception as e:
        logger.error(f"Failed to delete project: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': '삭제 중 오류가 발생했습니다.'}), 500

@app.route('/admin/edit_work/<int:work_id>', methods=['GET', 'POST'])
@login_required
def edit_work(work_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    project = Project.query.get_or_404(work_id)
    
    if request.method == 'POST':
        try:
            # 폼 데이터 업데이트
            project.title = request.form.get('title', '').strip()
            project.description = request.form.get('description', '').strip()
            project.detailed_description = request.form.get('detailed_description', '').strip()
            project.project_type = request.form.get('project_type', '').strip()
            project.category = request.form.get('category', '').strip()
            project.my_role = request.form.get('my_role', '').strip()
            project.tech_stack = request.form.get('tech_stack', '').strip()
            project.github_url = request.form.get('github_url', '').strip() or None
            project.demo_url = request.form.get('demo_url', '').strip() or None
            project.video_url = request.form.get('video_url', '').strip() or None
            project.achievements = request.form.get('achievements', '').strip() or None
            project.metrics = request.form.get('metrics', '').strip() or None
            project.is_featured = 'is_featured' in request.form
            project.is_public = 'is_public' in request.form
            project.sort_order = int(request.form.get('sort_order', 0))
            
            # 날짜 처리
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            
            if start_date_str:
                project.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if end_date_str and 'is_ongoing' not in request.form:
                project.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            elif 'is_ongoing' in request.form:
                project.end_date = None
            
            # 팀 크기 처리
            team_size_str = request.form.get('team_size')
            if team_size_str and team_size_str.isdigit():
                project.team_size = int(team_size_str)
            
            # 새 이미지 업로드 처리
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    # 기존 이미지 삭제
                    if project.image_path:
                        try:
                            old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], project.image_path)
                            if os.path.exists(old_file_path):
                                os.remove(old_file_path)
                        except Exception as e:
                            logger.error(f"Failed to delete old image: {e}")
                    
                    # 새 이미지 저장
                    filename = secure_filename(file.filename)
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{int(datetime.now().timestamp())}{ext}"
                    
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    file.save(file_path)
                    
                    # 이미지 최적화
                    try:
                        with Image.open(file_path) as img:
                            if img.width > 1200:
                                ratio = 1200 / img.width
                                new_height = int(img.height * ratio)
                                img = img.resize((1200, new_height), Image.Resampling.LANCZOS)
                                img.save(file_path, optimize=True, quality=85)
                    except Exception as e:
                        logger.error(f"Image processing error: {e}")
                    
                    project.image_path = filename
            
            db.session.commit()
            flash('프로젝트가 수정되었습니다.', 'success')
            return redirect(url_for('admin'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating project: {e}")
            flash(f'프로젝트 수정 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return render_template('edit_work.html', project=project)

# API 엔드포인트들
@app.route('/api/project/<int:project_id>/quick-view')
def api_project_quick_view(project_id):
    project = Project.query.get_or_404(project_id)
    
    if not project.is_public and (not current_user.is_authenticated or not current_user.is_admin):
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({
        'id': project.id,
        'title': project.title,
        'description': project.description,
        'tech_stack': project.tech_stack,
        'achievements': project.achievements,
        'github_url': project.github_url,
        'demo_url': project.demo_url,
        'image_path': project.image_path
    })

@app.route('/api/projects')
def api_projects():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    project_type = request.args.get('type', 'all')
    
    query = Project.query.filter_by(is_public=True)
    
    if project_type != 'all':
        query = query.filter_by(project_type=project_type)
    
    projects = query.order_by(Project.sort_order, Project.created_at.desc())\
                   .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'projects': [
            {
                'id': p.id,
                'title': p.title,
                'description': p.description,
                'project_type': p.project_type,
                'tech_stack': p.tech_stack,
                'image_path': p.image_path,
                'github_url': p.github_url,
                'demo_url': p.demo_url,
                'created_at': p.created_at.isoformat()
            } for p in projects.items
        ],
        'has_next': projects.has_next,
        'has_prev': projects.has_prev,
        'page': page,
        'total': projects.total
    })

# 개선된 에러 핸들러들
@app.errorhandler(413)
def file_too_large(error):
    """파일 크기 초과 에러"""
    logger.warning(f"파일 크기 초과: {request.remote_addr}")
    
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'message': '업로드 파일이 너무 큽니다. 16MB 이하의 파일을 업로드해주세요.'
        }), 413
    
    flash('업로드 파일이 너무 큽니다. 16MB 이하의 파일을 업로드해주세요.', 'error')
    return redirect(request.url or url_for('add_work'))

@app.errorhandler(400)
def bad_request(error):
    """잘못된 요청 에러"""
    logger.warning(f"잘못된 요청: {error} - {request.remote_addr}")
    
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'message': '잘못된 요청입니다.'
        }), 400
    
    flash('잘못된 요청입니다.', 'error')
    return redirect(url_for('index'))

@app.errorhandler(403)
def forbidden(error):
    """접근 금지 에러"""
    logger.warning(f"접근 금지: {error} - {request.remote_addr}")
    
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'message': '접근 권한이 없습니다.'
        }), 403
    
    flash('접근 권한이 없습니다.', 'error')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    """페이지를 찾을 수 없음 에러"""
    logger.info(f"404 에러: {request.url} - {request.remote_addr}")
    
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'message': '요청한 리소스를 찾을 수 없습니다.'
        }), 404
    
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """내부 서버 에러"""
    db.session.rollback()
    logger.error(f"내부 서버 에러: {error}", exc_info=True)
    
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'message': '서버에서 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
        }), 500
    
    return render_template('500.html'), 500

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """CSRF 토큰 에러 처리"""
    logger.warning(f"CSRF 에러: {e.description} - {request.remote_addr}")
    
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'message': 'CSRF 토큰이 유효하지 않습니다. 페이지를 새로고침해주세요.'
        }), 400
    
    flash('보안 토큰이 유효하지 않습니다. 페이지를 새로고침해주세요.', 'error')
    return redirect(request.url or url_for('add_work'))

# 디버그용 라우트 (개발 환경에서만)
@app.route('/debug/form-test', methods=['GET', 'POST'])
def debug_form_test():
    """폼 테스트용 디버그 라우트"""
    if not app.debug:
        return "Debug mode only", 404
    
    form = ProjectForm()
    
    if request.method == 'POST':
        logger.info("=== 폼 디버그 정보 ===")
        logger.info(f"Form valid: {form.validate()}")
        logger.info(f"Form errors: {form.errors}")
        logger.info(f"Request form: {dict(request.form)}")
        logger.info(f"Request files: {dict(request.files)}")
        logger.info(f"CSRF token valid: {form.csrf_token.data}")
        
        return jsonify({
            'form_valid': form.validate(),
            'form_errors': form.errors,
            'request_form': dict(request.form),
            'request_files': {k: v.filename for k, v in request.files.items()},
            'csrf_token': form.csrf_token.data
        })
    
    return f'''
    <form method="POST" enctype="multipart/form-data">
        {form.hidden_tag()}
        <input name="title" placeholder="제목 (최소 5자)" required><br><br>
        <textarea name="description" placeholder="설명 (최소 20자)" required></textarea><br><br>
        <select name="project_type" required>
            <option value="">선택</option>
            <option value="tech">기술</option>
        </select><br><br>
        <input type="file" name="image"><br><br>
        <input type="submit" value="테스트">
    </form>
    <br>
    <a href="/health">Health Check</a> |
    <a href="/admin">Admin</a> |
    <a href="/admin/add_work">Add Work</a>
    '''

# 업로드 폴더 초기화
def init_upload_folder():
    """업로드 폴더 초기화"""
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        # 권한 확인
        if not os.access(upload_folder, os.W_OK):
            logger.error(f"업로드 폴더 쓰기 권한 없음: {upload_folder}")
            return False
        
        logger.info(f"업로드 폴더 초기화 완료: {upload_folder}")
        return True
        
    except Exception as e:
        logger.error(f"업로드 폴더 초기화 실패: {e}")
        return False

# 애플리케이션 팩토리 함수
def create_app():
    """애플리케이션 팩토리 함수"""
    # 업로드 폴더 생성
    init_upload_folder()
    
    # 데이터베이스 안전 초기화
    with app.app_context():
        if not safe_init_db():
            logger.error("Failed to initialize database")
            raise RuntimeError("Database initialization failed")
    
    return app

# 컨텍스트 프로세서 (템플릿에서 사용할 전역 변수)
@app.context_processor
def inject_global_vars():
    return dict(
        current_year=datetime.now().year,
        app_version='1.0.0'
    )

# 애플리케이션 시작시 초기화
if __name__ == '__main__':
    # 개발 모드에서만 실행
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
else:
    # 프로덕션 모드 (gunicorn 등)에서 실행
    with app.app_context():
        try:
            init_upload_folder()
            safe_init_db()
        except Exception as e:
            logger.error(f"Failed to initialize application in production: {e}")
            # 프로덕션에서는 예외를 발생시키지 않고 로그만 기록