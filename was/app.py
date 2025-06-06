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

import re
from markupsafe import Markup
import markdown
from datetime import datetime, date

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
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024  # 30MB max file size

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
                                 Length(min=1, max=200, message='프로젝트명은 1-200자 사이여야 합니다.')])
    
    description = TextAreaField('간단한 설명', 
                              validators=[DataRequired(message='프로젝트 설명을 입력해주세요.'), 
                                        Length(max=1000)])
    
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
        


class LearningCategory(db.Model):
    """학습 카테고리 모델"""
    __tablename__ = 'learning_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#007bff')  # 카테고리 색상
    icon_class = db.Column(db.String(100), default='fas fa-book')  # 아이콘 클래스
    parent_id = db.Column(db.Integer, db.ForeignKey('learning_categories.id'))  # 상위 카테고리
    
    sort_order = db.Column(db.Integer, default=0, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # 관계 정의
    children = db.relationship('LearningCategory', backref=db.backref('parent', remote_side=[id]))
    posts = db.relationship('LearningPost', backref='category', lazy='dynamic')

class LearningPost(db.Model):
    """학습 포스트 모델"""
    __tablename__ = 'learning_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    slug = db.Column(db.String(200), unique=True, index=True)  # URL용 슬러그
    content = db.Column(db.Text, nullable=False)  # 마크다운 컨텐츠
    summary = db.Column(db.Text)  # 요약
    
    category_id = db.Column(db.Integer, db.ForeignKey('learning_categories.id'), index=True)
    
    # 메타 정보
    reading_time = db.Column(db.Integer, default=0)  # 예상 읽기 시간(분)
    difficulty = db.Column(db.String(20), index=True)  # 초급, 중급, 고급
    
    # 이미지 및 미디어
    thumbnail_path = db.Column(db.String(500))  # 썸네일 이미지
    images = db.relationship('LearningImage', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    
    # 태그 및 키워드
    tags = db.Column(db.Text)  # 쉼표로 구분된 태그
    keywords = db.Column(db.Text)  # 검색 키워드
    
    # 학습 정보
    learning_date = db.Column(db.Date, index=True)  # 학습한 날짜
    source_url = db.Column(db.String(500))  # 학습 자료 출처
    reference_books = db.Column(db.Text)  # 참고 도서
    practice_code_url = db.Column(db.String(500))  # 실습 코드 URL
    
    # 공개 설정
    is_published = db.Column(db.Boolean, default=True, index=True)
    is_featured = db.Column(db.Boolean, default=False, index=True)
    password = db.Column(db.String(255))  # 비밀번호 보호
    
    # 통계
    view_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    
    # 날짜 정보
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime, index=True)
    
    # 인덱스
    __table_args__ = (
        db.Index('idx_learning_posts_category_date', 'category_id', 'created_at'),
        db.Index('idx_learning_posts_published', 'is_published', 'published_at'),
    )

class LearningImage(db.Model):
    """학습 포스트 이미지 모델"""
    __tablename__ = 'learning_images'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('learning_posts.id'), nullable=False)
    filename = db.Column(db.String(500), nullable=False)
    original_name = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    alt_text = db.Column(db.String(200))
    caption = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LearningTag(db.Model):
    """학습 태그 모델"""
    __tablename__ = 'learning_tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    color = db.Column(db.String(7), default='#6c757d')
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
            
            {'name': 'Django', 'category': 'framework', 'icon_class': 'fas fa-server', 'color': '#092e20', 'proficiency': 85},
            {'name': 'Flask', 'category': 'framework', 'icon_class': 'fas fa-flask', 'color': '#000000', 'proficiency': 90},
            {'name': 'React', 'category': 'framework', 'icon_class': 'fab fa-react', 'color': '#61dafb', 'proficiency': 80, 'is_primary': True},
            
            {'name': 'PostgreSQL', 'category': 'database', 'icon_class': 'fas fa-database', 'color': '#336791', 'proficiency': 85},
            {'name': 'MySQL', 'category': 'database', 'icon_class': 'fas fa-database', 'color': '#4479a1', 'proficiency': 90},
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
                'name': '빅데이터분석기사',
                'issuer': '한국데이터산업진흥원',
                'issue_date': date(2021, 12, 31),
                'category': 'cloud',
                'is_featured': True
            },
            {
                'name': 'Certified Kubernetes Administrator (CKA)',
                'issuer': 'Linux Foundation',
                'issue_date': date(2024, 8, 20),
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
        
        # 학습 블로그 기본 데이터 초기화 호출
        init_learning_default_data()
        
        db.session.commit()
        logger.info("Default data initialized")
    except Exception as e:
        logger.error(f"Failed to initialize default data: {e}")
        db.session.rollback()

def init_learning_default_data():
    """학습 블로그 기본 데이터 초기화"""
    try:
        # 기본 학습 카테고리 생성
        default_categories = [
            {
                'name': 'Programming',
                'description': '프로그래밍 언어 및 개발 기법',
                'color': '#007bff',
                'icon_class': 'fas fa-code',
                'sort_order': 1
            },
            {
                'name': 'Web Development',
                'description': '웹 개발 관련 학습',
                'color': '#28a745',
                'icon_class': 'fas fa-globe',
                'sort_order': 2
            },
            {
                'name': 'Database',
                'description': '데이터베이스 설계 및 최적화',
                'color': '#ffc107',
                'icon_class': 'fas fa-database',
                'sort_order': 3
            },
            {
                'name': 'DevOps',
                'description': '인프라 및 배포 자동화',
                'color': '#dc3545',
                'icon_class': 'fas fa-cogs',
                'sort_order': 4
            },
            {
                'name': 'Data Science',
                'description': '데이터 분석 및 머신러닝',
                'color': '#6f42c1',
                'icon_class': 'fas fa-chart-bar',
                'sort_order': 5
            },
            {
                'name': 'Algorithm',
                'description': '알고리즘 및 자료구조',
                'color': '#fd7e14',
                'icon_class': 'fas fa-project-diagram',
                'sort_order': 6
            }
        ]
        
        for cat_data in default_categories:
            existing = LearningCategory.query.filter_by(name=cat_data['name']).first()
            if not existing:
                category = LearningCategory(**cat_data)
                db.session.add(category)
        
        # 기본 태그 생성
        default_tags = [
            'Python', 'JavaScript', 'React', 'Django', 'Flask',
            'PostgreSQL', 'MySQL', 'Docker', 'Kubernetes', 'AWS',
            'Git', 'Linux', 'API', 'Testing', 'Performance'
        ]
        
        for tag_name in default_tags:
            existing = LearningTag.query.filter_by(name=tag_name).first()
            if not existing:
                tag = LearningTag(name=tag_name)
                db.session.add(tag)
        
        # 여기서 commit하지 않음 - 상위 함수에서 처리
        logger.info("학습 블로그 기본 데이터 초기화 완료")
        
    except Exception as e:
        logger.error(f"학습 블로그 기본 데이터 초기화 실패: {e}")
        # 여기서 rollback하지 않음 - 상위 함수에서 처리
#######################################################################
# 유틸리티 함수들 추가

def generate_slug(title):
    """제목으로부터 URL 슬러그 생성"""
    # 한글 및 영문자, 숫자만 남기고 제거
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')

def calculate_reading_time(content):
    """컨텐츠 읽기 시간 계산 (분)"""
    words = len(content.split())
    return max(1, round(words / 200))  # 분당 200단어 기준


def handle_image_upload(file, max_size_mb=10):
    """향상된 이미지 파일 업로드 처리"""
    try:
        if not file or not file.filename:
            return None
        
        # 파일 크기 체크 (업로드 전)
        file.seek(0, 2)  # 파일 끝으로 이동
        file_size = file.tell()
        file.seek(0)  # 파일 시작으로 되돌림
        
        if file_size > max_size_mb * 1024 * 1024:
            logger.warning(f"파일 크기 초과: {file_size / 1024 / 1024:.1f}MB > {max_size_mb}MB")
            # 큰 파일도 처리하되 로그만 남김
        
        filename = secure_filename(file.filename)
        if not filename:
            logger.error("잘못된 파일명")
            return None
        
        # 허용된 확장자 확인
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext not in allowed_extensions:
            logger.error(f"허용되지 않는 파일 형식: {file_ext}")
            return None
        
        # 고유한 파일명 생성
        name, ext = os.path.splitext(filename)
        timestamp = int(datetime.now().timestamp())
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}_{timestamp}{ext}"
        
        # 업로드 폴더 확인 및 생성
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        # 파일 저장
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # 이미지 최적화 (크기가 큰 경우에만)
        if file_size > 2 * 1024 * 1024:  # 2MB 이상인 경우
            logger.info(f"대용량 파일 최적화 시작: {file_size / 1024 / 1024:.1f}MB")
            optimize_image(file_path, max_width=1920, max_height=1080, quality=85)
        else:
            # 작은 파일도 기본 최적화
            optimize_image(file_path, max_width=2560, max_height=1440, quality=90)
        
        logger.info(f"이미지 업로드 성공: {unique_filename}")
        return unique_filename
        
    except Exception as e:
        logger.error(f"이미지 업로드 실패: {str(e)}", exc_info=True)
        # 업로드 실패시 임시 파일 정리
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        return None


def optimize_image(file_path, max_width=1920, max_height=1080, quality=85):
    """이미지 최적화 - 크기 조정 및 압축"""
    try:
        with Image.open(file_path) as img:
            # EXIF 데이터 기반 회전 보정
            if hasattr(img, '_getexif'):
                exif = img._getexif()
                if exif is not None:
                    orientation = exif.get(274)
                    if orientation == 3:
                        img = img.rotate(180, expand=True)
                    elif orientation == 6:
                        img = img.rotate(270, expand=True)
                    elif orientation == 8:
                        img = img.rotate(90, expand=True)
            
            # 원본 크기 저장
            original_width, original_height = img.size
            logger.info(f"원본 이미지 크기: {original_width}x{original_height}")
            
            # 크기 조정이 필요한지 확인
            if original_width > max_width or original_height > max_height:
                # 비율 유지하면서 리사이징
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                logger.info(f"리사이징된 크기: {img.size}")
            
            # RGBA나 P 모드를 RGB로 변환 (JPEG 저장용)
            if img.mode in ('RGBA', 'P'):
                # RGBA인 경우 흰색 배경과 합성
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])  # alpha 채널을 마스크로 사용
                    img = background
                else:
                    img = img.convert('RGB')
            
            # 파일 확장자 확인
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in ['.jpg', '.jpeg']:
                # JPEG 최적화
                img.save(file_path, format='JPEG', optimize=True, quality=quality)
            elif file_ext == '.png':
                # PNG 최적화 (품질 손실 없이)
                img.save(file_path, format='PNG', optimize=True)
            elif file_ext == '.gif':
                # GIF는 그대로 유지 (애니메이션 보존)
                pass
            else:
                # 기타 형식은 JPEG로 변환
                new_file_path = os.path.splitext(file_path)[0] + '.jpg'
                img.save(new_file_path, format='JPEG', optimize=True, quality=quality)
                # 원본 파일 삭제하고 새 파일로 교체
                if os.path.exists(file_path):
                    os.remove(file_path)
                os.rename(new_file_path, file_path)
            
            # 최적화 후 파일 크기 확인
            final_size = os.path.getsize(file_path)
            logger.info(f"최적화 완료 - 파일 크기: {final_size / 1024:.1f}KB")
            
    except Exception as e:
        logger.error(f"이미지 최적화 실패: {str(e)}")
        raise e


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

# app.py에 추가할 코드

# 기존 index 라우트를 다음과 같이 수정
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
    
    # 배경용 아트워크 이미지들 가져오기 (아트워크 타입이면서 이미지가 있는 프로젝트만)
    artwork_projects = Project.query.filter(
        Project.is_public == True,
        Project.project_type == 'art',
        Project.image_path.isnot(None),
        Project.image_path != ''
    ).order_by(Project.created_at.desc()).all()
    
    # 아트워크가 없으면 기본 배경 사용
    if not artwork_projects:
        artwork_projects = []
    
    return render_template('index.html', 
                         featured_projects=featured_projects,
                         recent_projects=recent_projects,
                         primary_techs=primary_techs,
                         recent_experiences=recent_experiences,
                         artwork_projects=artwork_projects)

# 배경 이미지 API 엔드포인트 추가
@app.route('/api/background-images')
def api_background_images():
    """배경용 이미지 목록 API"""
    try:
        artwork_projects = Project.query.filter(
            Project.is_public == True,
            Project.project_type == 'art',
            Project.image_path.isnot(None),
            Project.image_path != ''
        ).order_by(Project.created_at.desc()).all()
        
        images = []
        for project in artwork_projects:
            images.append({
                'id': project.id,
                'title': project.title,
                'description': project.description,
                'image_url': url_for('uploaded_file', filename=project.image_path),
                'project_type': project.project_type,
                'category': project.category
            })
        
        return jsonify({
            'success': True,
            'images': images,
            'total': len(images)
        })
        
    except Exception as e:
        logger.error(f"배경 이미지 API 오류: {e}")
        return jsonify({
            'success': False,
            'message': '이미지를 불러오는 중 오류가 발생했습니다.',
            'images': []
        }), 500

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
    """프로젝트 상세 페이지"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # 공개 여부 확인
        if not project.is_public and (not current_user.is_authenticated or not current_user.is_admin):
            logger.warning(f"비공개 프로젝트 접근 시도: {project_id} by {request.remote_addr}")
            flash('접근 권한이 없습니다.', 'error')
            return redirect(url_for('portfolio'))
        
        # 조회수 증가
        try:
            project.view_count = (project.view_count or 0) + 1
            db.session.commit()
        except Exception as e:
            logger.error(f"조회수 업데이트 실패: {e}")
            db.session.rollback()
        
        # 관련 프로젝트 조회
        related_projects = []
        try:
            if project.category:
                related_projects = Project.query.filter(
                    Project.id != project_id,
                    Project.category == project.category,
                    Project.is_public == True
                ).order_by(Project.created_at.desc()).limit(3).all()
            
            # 카테고리가 같은 프로젝트가 없으면 같은 타입의 프로젝트 찾기
            if not related_projects and project.project_type:
                related_projects = Project.query.filter(
                    Project.id != project_id,
                    Project.project_type == project.project_type,
                    Project.is_public == True
                ).order_by(Project.created_at.desc()).limit(3).all()
        except Exception as e:
            logger.error(f"관련 프로젝트 조회 실패: {e}")
            related_projects = []
        
        logger.info(f"프로젝트 상세 페이지 접근: {project.title} (ID: {project_id})")
        
        return render_template('project_detail.html', 
                             project=project,
                             related_projects=related_projects)
        
    except Exception as e:
        logger.error(f"프로젝트 상세 페이지 오류: {e}", exc_info=True)
        flash('프로젝트를 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('portfolio'))

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
    
    try:
        # 기존 포트폴리오 데이터
        projects = Project.query.order_by(Project.created_at.desc()).all()
        tech_stacks = TechStack.query.order_by(TechStack.proficiency.desc()).all()
        certifications = Certification.query.order_by(Certification.issue_date.desc()).all()
        experiences = Experience.query.order_by(Experience.created_at.desc()).all()
        
        # 학습 블로그 데이터 추가
        learning_stats = {}
        recent_learning_posts = []
        
        try:
            # 학습 블로그 통계
            learning_stats = {
                'total_posts': LearningPost.query.count(),
                'published_posts': LearningPost.query.filter_by(is_published=True).count(),
                'total_categories': LearningCategory.query.filter_by(is_active=True).count(),
                'total_views': db.session.query(db.func.sum(LearningPost.view_count)).scalar() or 0
            }
            
            # 최근 학습 포스트
            recent_learning_posts = LearningPost.query.order_by(LearningPost.created_at.desc()).limit(5).all()
            
        except Exception as e:
            # 학습 블로그 테이블이 아직 없는 경우 기본값
            logger.warning(f"학습 블로그 데이터 조회 실패 (테이블이 없을 수 있음): {e}")
            learning_stats = {
                'total_posts': 0,
                'published_posts': 0,
                'total_categories': 0,
                'total_views': 0
            }
            recent_learning_posts = []
        
        return render_template('admin.html', 
                             works=projects,  # 기존 템플릿 호환성
                             projects=projects,
                             tech_stacks=tech_stacks,
                             certifications=certifications,
                             experiences=experiences,
                             # 학습 블로그 데이터 추가
                             learning_stats=learning_stats,
                             recent_learning_posts=recent_learning_posts)
                             
    except Exception as e:
        logger.error(f"관리자 페이지 오류: {e}")
        flash('관리자 페이지를 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('index'))
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
                    image_path = handle_image_upload(form.image.data, max_size_mb=30)  # 20MB까지 허용
                    if not image_path:
                        flash('이미지 업로드에 실패했습니다. 파일 형식을 확인하거나 크기를 줄여주세요.', 'error')
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
        try:
            # CSRF 토큰 검증은 CSRFProtect가 자동으로 처리
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            remember = request.form.get('remember') == 'on'
            
            if not username or not password:
                flash('사용자명과 비밀번호를 입력해주세요.', 'error')
                return render_template('login.html')
            
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                login_user(user, remember=remember)
                logger.info(f"로그인 성공: {username}")
                
                # AJAX 요청인 경우 JSON 응답
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True,
                        'message': '로그인되었습니다.',
                        'redirect_url': url_for('admin')
                    })
                
                # 일반 폼 제출인 경우
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('admin'))
            else:
                logger.warning(f"로그인 실패: {username}")
                flash('잘못된 사용자명 또는 비밀번호입니다.', 'error')
                
                # AJAX 요청인 경우 JSON 응답
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'message': '잘못된 사용자명 또는 비밀번호입니다.'
                    }), 401
                
        except Exception as e:
            logger.error(f"로그인 처리 중 오류: {e}")
            flash('로그인 처리 중 오류가 발생했습니다.', 'error')
            
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': '로그인 처리 중 오류가 발생했습니다.'
                }), 500
    
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
    """프로젝트 수정"""
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('index'))
    
    try:
        project = Project.query.get_or_404(work_id)
        
        if request.method == 'POST':
            logger.info(f"프로젝트 수정 요청 - ID: {work_id}, 사용자: {current_user.username}")
            
            try:
                # 기본 정보 업데이트
                project.title = request.form.get('title', '').strip()
                project.description = request.form.get('description', '').strip()
                project.detailed_description = request.form.get('detailed_description', '').strip() or None
                project.project_type = request.form.get('project_type', '').strip()
                project.category = request.form.get('category', '').strip() or None
                project.my_role = request.form.get('my_role', '').strip() or None
                project.tech_stack = request.form.get('tech_stack', '').strip() or None
                
                # URL 정보 업데이트
                project.github_url = request.form.get('github_url', '').strip() or None
                project.demo_url = request.form.get('demo_url', '').strip() or None
                project.video_url = request.form.get('video_url', '').strip() or None
                
                # 성과 정보 업데이트
                project.achievements = request.form.get('achievements', '').strip() or None
                project.metrics = request.form.get('metrics', '').strip() or None
                
                # 공개 설정 업데이트
                project.is_featured = 'is_featured' in request.form
                project.is_public = 'is_public' in request.form
                project.sort_order = int(request.form.get('sort_order', 0))
                
                # 날짜 처리
                start_date_str = request.form.get('start_date')
                end_date_str = request.form.get('end_date')
                is_ongoing = 'is_ongoing' in request.form
                
                if start_date_str:
                    try:
                        project.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        project.start_date = None
                
                if is_ongoing:
                    project.end_date = None
                elif end_date_str:
                    try:
                        project.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        project.end_date = None
                
                # 팀 크기 처리
                team_size_str = request.form.get('team_size')
                if team_size_str and team_size_str.isdigit():
                    project.team_size = int(team_size_str)
                else:
                    project.team_size = None
                
                # 기존 이미지 삭제 처리
                if request.form.get('remove_image') == 'true' and project.image_path:
                    try:
                        old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], project.image_path)
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                            logger.info(f"기존 이미지 삭제: {project.image_path}")
                    except Exception as e:
                        logger.error(f"기존 이미지 삭제 실패: {e}")
                    project.image_path = None
                
                # 새 이미지 업로드 처리
                if 'image' in request.files:
                    file = request.files['image']
                    if file and file.filename:
                        # 기존 이미지 삭제 (새 이미지로 교체하는 경우)
                        if project.image_path:
                            try:
                                old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], project.image_path)
                                if os.path.exists(old_file_path):
                                    os.remove(old_file_path)
                                    logger.info(f"기존 이미지 교체: {project.image_path}")
                            except Exception as e:
                                logger.error(f"기존 이미지 삭제 실패: {e}")
                        
                        # 새 이미지 업로드
                        new_image_path = handle_image_upload(file)
                        if new_image_path:
                            project.image_path = new_image_path
                            logger.info(f"새 이미지 업로드: {new_image_path}")
                        else:
                            flash('이미지 업로드에 실패했습니다.', 'warning')
                
                # 데이터베이스 업데이트
                db.session.commit()
                
                logger.info(f"프로젝트 수정 완료: {project.title} (ID: {work_id})")
                flash('프로젝트가 성공적으로 수정되었습니다!', 'success')
                
                # AJAX 요청인 경우 JSON 응답
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True,
                        'message': '프로젝트가 성공적으로 수정되었습니다.',
                        'redirect_url': url_for('admin')
                    })
                
                return redirect(url_for('admin'))
                
            except Exception as e:
                db.session.rollback()
                error_msg = f"프로젝트 수정 중 오류가 발생했습니다: {str(e)}"
                logger.error(f"프로젝트 수정 오류: {str(e)}", exc_info=True)
                
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'message': error_msg
                    }), 500
                
                flash(error_msg, 'error')
        
        # GET 요청 처리
        return render_template('edit_work.html', project=project)
        
    except Exception as e:
        logger.error(f"프로젝트 수정 페이지 오류: {str(e)}", exc_info=True)
        flash('프로젝트를 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('admin'))
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
    """파일 크기 초과 에러 개선"""
    logger.warning(f"파일 크기 초과: {request.remote_addr}")
    
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'message': '업로드 파일이 너무 큽니다. 30MB 이하의 파일을 업로드해주세요. 큰 이미지는 자동으로 최적화됩니다.'
        }), 413
    
    flash('업로드 파일이 너무 큽니다. 30MB 이하의 파일을 업로드해주세요.', 'error')
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

######################ㅂ블로그
@app.template_filter('markdown')
def markdown_filter(text):
    """마크다운을 HTML로 변환"""
    if not text:
        return ''
    try:
        md = markdown.Markdown(extensions=['codehilite', 'fenced_code', 'tables', 'toc'])
        html = md.convert(text)
        return Markup(html)
    except Exception as e:
        logger.error(f"마크다운 변환 오류: {e}")
        return Markup(text.replace('\n', '<br>'))

# 공개 학습 블로그 라우트들
@app.route('/learning')
def learning_blog():
    """학습 블로그 메인 페이지"""
    try:
        # 카테고리별 포스트 수 조회
        categories = db.session.query(
            LearningCategory,
            db.func.count(LearningPost.id).label('post_count')
        ).outerjoin(LearningPost, 
            (LearningCategory.id == LearningPost.category_id) & 
            (LearningPost.is_published == True)
        ).filter(LearningCategory.is_active == True)\
         .group_by(LearningCategory.id)\
         .order_by(LearningCategory.sort_order).all()
        
        # 최근 포스트
        recent_posts = LearningPost.query.filter_by(is_published=True)\
                                        .order_by(LearningPost.published_at.desc())\
                                        .limit(6).all()
        
        # 추천 포스트 (조회수 높은 순)
        featured_posts = LearningPost.query.filter_by(is_published=True, is_featured=True)\
                                          .order_by(LearningPost.view_count.desc())\
                                          .limit(3).all()
        
        # 인기 태그
        popular_tags = LearningTag.query.order_by(LearningTag.usage_count.desc()).limit(20).all()
        
        return render_template('learning/index.html',
                             categories=categories,
                             recent_posts=recent_posts,
                             featured_posts=featured_posts,
                             popular_tags=popular_tags)
    except Exception as e:
        logger.error(f"학습 블로그 메인 페이지 오류: {e}")
        flash('페이지를 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('index'))

@app.route('/learning/category/<int:category_id>')
def learning_category(category_id):
    """카테고리별 학습 포스트 목록"""
    try:
        category = LearningCategory.query.get_or_404(category_id)
        
        page = request.args.get('page', 1, type=int)
        per_page = 12
        
        posts = LearningPost.query.filter_by(
            category_id=category_id, 
            is_published=True
        ).order_by(LearningPost.published_at.desc())\
         .paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template('learning/category.html',
                             category=category,
                             posts=posts)
    except Exception as e:
        logger.error(f"카테고리 페이지 오류: {e}")
        flash('카테고리를 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('learning_blog'))

@app.route('/learning/post/<slug>')
def learning_post_detail(slug):
    """학습 포스트 상세 페이지"""
    try:
        post = LearningPost.query.filter_by(slug=slug, is_published=True).first_or_404()
        
        # 조회수 증가
        post.view_count = (post.view_count or 0) + 1
        db.session.commit()
        
        # 관련 포스트 (같은 카테고리)
        related_posts = LearningPost.query.filter(
            LearningPost.id != post.id,
            LearningPost.category_id == post.category_id,
            LearningPost.is_published == True
        ).order_by(LearningPost.published_at.desc()).limit(3).all()
        
        # 이전/다음 포스트
        prev_post = LearningPost.query.filter(
            LearningPost.published_at < post.published_at,
            LearningPost.is_published == True
        ).order_by(LearningPost.published_at.desc()).first()
        
        next_post = LearningPost.query.filter(
            LearningPost.published_at > post.published_at,
            LearningPost.is_published == True
        ).order_by(LearningPost.published_at.asc()).first()
        
        return render_template('learning/post_detail.html',
                             post=post,
                             related_posts=related_posts,
                             prev_post=prev_post,
                             next_post=next_post)
    except Exception as e:
        logger.error(f"포스트 상세 페이지 오류: {e}")
        flash('포스트를 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('learning_blog'))

# 관리자 학습 블로그 라우트들
@app.route('/admin/learning')
@login_required
def admin_learning():
    """관리자 학습 블로그 대시보드"""
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('index'))
    
    try:
        # 통계 정보
        total_posts = LearningPost.query.count()
        published_posts = LearningPost.query.filter_by(is_published=True).count()
        total_categories = LearningCategory.query.filter_by(is_active=True).count()
        total_views = db.session.query(db.func.sum(LearningPost.view_count)).scalar() or 0
        
        # 최근 포스트
        recent_posts = LearningPost.query.order_by(LearningPost.created_at.desc()).limit(10).all()
        
        # 카테고리별 포스트 수
        category_stats = db.session.query(
            LearningCategory.name,
            db.func.count(LearningPost.id).label('count')
        ).outerjoin(LearningPost)\
         .group_by(LearningCategory.id)\
         .order_by(db.text('count DESC')).all()
        
        return render_template('admin/learning/dashboard.html',
                             total_posts=total_posts,
                             published_posts=published_posts,
                             total_categories=total_categories,
                             total_views=total_views,
                             recent_posts=recent_posts,
                             category_stats=category_stats)
    except Exception as e:
        logger.error(f"관리자 학습 대시보드 오류: {e}")
        flash('대시보드를 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('admin'))

@app.route('/admin/learning/posts')
@login_required
def admin_learning_posts():
    """관리자 학습 포스트 목록"""
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('index'))
    
    try:
        page = request.args.get('page', 1, type=int)
        category_id = request.args.get('category', type=int)
        status = request.args.get('status')
        
        query = LearningPost.query
        
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        if status == 'published':
            query = query.filter_by(is_published=True)
        elif status == 'draft':
            query = query.filter_by(is_published=False)
        
        posts = query.order_by(LearningPost.created_at.desc())\
                    .paginate(page=page, per_page=20, error_out=False)
        
        categories = LearningCategory.query.filter_by(is_active=True)\
                                          .order_by(LearningCategory.sort_order).all()
        
        return render_template('admin/learning/posts.html',
                             posts=posts,
                             categories=categories,
                             current_category=category_id,
                             current_status=status)
    except Exception as e:
        logger.error(f"관리자 포스트 목록 오류: {e}")
        flash('포스트 목록을 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('admin_learning'))

@app.route('/admin/learning/post/new', methods=['GET', 'POST'])
@login_required
def admin_learning_post_new():
    """새 학습 포스트 작성"""
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # 폼 데이터 처리
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            summary = request.form.get('summary', '').strip()
            category_id = request.form.get('category_id', type=int)
            tags = request.form.get('tags', '').strip()
            difficulty = request.form.get('difficulty', 'beginner')
            learning_date_str = request.form.get('learning_date')
            source_url = request.form.get('source_url', '').strip()
            is_published = 'is_published' in request.form
            is_featured = 'is_featured' in request.form
            
            if not title or not content:
                flash('제목과 내용을 입력해주세요.', 'error')
                return redirect(request.url)
            
            # 슬러그 생성
            slug = generate_slug(title)
            
            # 슬러그 중복 확인
            existing = LearningPost.query.filter_by(slug=slug).first()
            if existing:
                slug = f"{slug}-{int(datetime.now().timestamp())}"
            
            # 학습 날짜 처리
            learning_date = None
            if learning_date_str:
                try:
                    learning_date = datetime.strptime(learning_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # 포스트 생성
            post = LearningPost(
                title=title,
                slug=slug,
                content=content,
                summary=summary,
                category_id=category_id,
                tags=tags,
                difficulty=difficulty,
                learning_date=learning_date,
                source_url=source_url if source_url else None,
                
                is_published=is_published,
                is_featured=is_featured,
                published_at=datetime.utcnow() if is_published else None
            )
            
            # 썸네일 이미지 처리
            if 'thumbnail' in request.files:
                file = request.files['thumbnail']
                if file and file.filename:
                    thumbnail_path = handle_image_upload(file)
                    if thumbnail_path:
                        post.thumbnail_path = thumbnail_path
            
            db.session.add(post)
            db.session.commit()
            
            logger.info(f"새 학습 포스트 생성: {post.title} (ID: {post.id})")
            flash('학습 포스트가 성공적으로 작성되었습니다!', 'success')
            return redirect(url_for('admin_learning_posts'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"학습 포스트 작성 오류: {e}")
            flash('포스트 작성 중 오류가 발생했습니다.', 'error')
    
    # GET 요청 처리
    categories = LearningCategory.query.filter_by(is_active=True)\
                                      .order_by(LearningCategory.sort_order).all()
    return render_template('admin/learning/post_form.html', categories=categories, post=None)

@app.route('/admin/learning/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_learning_post_edit(post_id):
    """학습 포스트 수정"""
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('index'))
    
    try:
        post = LearningPost.query.get_or_404(post_id)
        
        if request.method == 'POST':
            # 수정 로직 (새 포스트 작성과 유사)
            post.title = request.form.get('title', '').strip()
            post.content = request.form.get('content', '').strip()
            post.summary = request.form.get('summary', '').strip()
            post.category_id = request.form.get('category_id', type=int)
            post.tags = request.form.get('tags', '').strip()
            post.difficulty = request.form.get('difficulty', 'beginner')
            post.source_url = request.form.get('source_url', '').strip() or None
            post.is_published = 'is_published' in request.form
            post.is_featured = 'is_featured' in request.form
            
            post.updated_at = datetime.utcnow()
            
            # 발행 상태 변경시 발행일 업데이트
            if post.is_published and not post.published_at:
                post.published_at = datetime.utcnow()
            
            # 학습 날짜 처리
            learning_date_str = request.form.get('learning_date')
            if learning_date_str:
                try:
                    post.learning_date = datetime.strptime(learning_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # 새 썸네일 업로드 처리
            if 'thumbnail' in request.files:
                file = request.files['thumbnail']
                if file and file.filename:
                    new_thumbnail = handle_image_upload(file)
                    if new_thumbnail:
                        # 기존 썸네일 삭제
                        if post.thumbnail_path:
                            try:
                                old_path = os.path.join(app.config['UPLOAD_FOLDER'], post.thumbnail_path)
                                if os.path.exists(old_path):
                                    os.remove(old_path)
                            except Exception as e:
                                logger.error(f"기존 썸네일 삭제 실패: {e}")
                        post.thumbnail_path = new_thumbnail
            
            db.session.commit()
            
            logger.info(f"학습 포스트 수정: {post.title} (ID: {post_id})")
            flash('학습 포스트가 수정되었습니다!', 'success')
            return redirect(url_for('admin_learning_posts'))
        
        # GET 요청 처리
        categories = LearningCategory.query.filter_by(is_active=True)\
                                          .order_by(LearningCategory.sort_order).all()
        return render_template('admin/learning/post_form.html', categories=categories, post=post)
        
    except Exception as e:
        logger.error(f"학습 포스트 수정 오류: {e}")
        flash('포스트 수정 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('admin_learning_posts'))

@app.route('/admin/learning/post/<int:post_id>/delete', methods=['DELETE'])
@login_required
def admin_learning_post_delete(post_id):
    """학습 포스트 삭제"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    try:
        post = LearningPost.query.get_or_404(post_id)
        
        # 관련 이미지 파일들 삭제
        if post.thumbnail_path:
            try:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], post.thumbnail_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"썸네일 삭제 실패: {e}")
        
        # 포스트 삭제
        db.session.delete(post)
        db.session.commit()
        
        logger.info(f"학습 포스트 삭제: {post.title} (ID: {post_id})")
        return jsonify({'success': True, 'message': '포스트가 삭제되었습니다.'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"학습 포스트 삭제 오류: {e}")
        return jsonify({'success': False, 'message': '삭제 중 오류가 발생했습니다.'}), 500

@app.route('/admin/learning/categories')
@login_required
def admin_learning_categories():
    """학습 카테고리 관리"""
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.', 'error')
        return redirect(url_for('index'))
    
    try:
        categories = LearningCategory.query.order_by(LearningCategory.sort_order).all()
        return render_template('admin/learning/categories.html', categories=categories)
    except Exception as e:
        logger.error(f"카테고리 관리 페이지 오류: {e}")
        flash('카테고리 목록을 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('admin_learning'))
    
    ##################################################################################
@app.route('/admin/learning/category', methods=['POST'])
@app.route('/admin/learning/category/<int:category_id>', methods=['PUT', 'DELETE'])
@login_required
def admin_learning_category_manage(category_id=None):
    """학습 카테고리 생성/수정/삭제"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    try:
        if request.method == 'POST':
            # 새 카테고리 생성
            category = LearningCategory(
                name=request.form.get('name'),
                description=request.form.get('description'),
                color=request.form.get('color', '#007bff'),
                icon_class=request.form.get('icon_class', 'fas fa-book'),
                sort_order=int(request.form.get('sort_order', 0)),
                is_active=request.form.get('is_active') == 'on'
            )
            
            db.session.add(category)
            db.session.commit()
            
            return jsonify({'success': True, 'message': '카테고리가 생성되었습니다.'})
            
        elif request.method == 'PUT':
            # 카테고리 수정
            category = LearningCategory.query.get_or_404(category_id)
            
            category.name = request.form.get('name')
            category.description = request.form.get('description')
            category.color = request.form.get('color', '#007bff')
            category.icon_class = request.form.get('icon_class', 'fas fa-book')
            category.sort_order = int(request.form.get('sort_order', 0))
            category.is_active = request.form.get('is_active') == 'on'
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': '카테고리가 수정되었습니다.'})
            
        elif request.method == 'DELETE':
            # 카테고리 삭제
            category = LearningCategory.query.get_or_404(category_id)
            
            # 해당 카테고리의 포스트들을 다른 카테고리로 이동하거나 삭제
            posts_count = LearningPost.query.filter_by(category_id=category_id).count()
            if posts_count > 0:
                return jsonify({
                    'success': False, 
                    'message': f'이 카테고리에 {posts_count}개의 포스트가 있습니다. 먼저 포스트들을 이동하거나 삭제해주세요.'
                }), 400
            
            db.session.delete(category)
            db.session.commit()
            
            return jsonify({'success': True, 'message': '카테고리가 삭제되었습니다.'})
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"카테고리 관리 오류: {e}")
        return jsonify({'success': False, 'message': '처리 중 오류가 발생했습니다.'}), 500
    
@app.route('/admin/learning/upload-image', methods=['POST'])
@login_required
def admin_learning_upload_image():
    """학습 포스트 본문 이미지 업로드 API"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    try:
        # CSRF 토큰 검증은 자동으로 처리됨
        
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': '이미지 파일이 없습니다.'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': '파일이 선택되지 않았습니다.'}), 400
        
        # 파일 크기 확인 (10MB)
        if file.content_length and file.content_length > 10 * 1024 * 1024:
            return jsonify({'success': False, 'message': '파일 크기가 10MB를 초과합니다.'}), 400
        
        # 파일 타입 확인
        if not file.content_type.startswith('image/'):
            return jsonify({'success': False, 'message': '이미지 파일만 업로드 가능합니다.'}), 400
        
        # 파일명 보안 처리
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({'success': False, 'message': '잘못된 파일명입니다.'}), 400
        
        # 고유한 파일명 생성
        name, ext = os.path.splitext(filename)
        unique_filename = f"content_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}{ext}"
        
        # 업로드 폴더 확인
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
        
        # 파일 저장
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # 이미지 최적화 (선택사항)
        try:
            optimize_image(file_path)
        except Exception as e:
            logger.warning(f"이미지 최적화 실패: {e}")
        
        # URL 생성
        image_url = url_for('uploaded_file', filename=unique_filename, _external=False)
        
        logger.info(f"학습 포스트 이미지 업로드 성공: {unique_filename}")
        
        return jsonify({
            'success': True,
            'message': '이미지가 성공적으로 업로드되었습니다.',
            'filename': unique_filename,
            'url': image_url,
            'markdown': f'![이미지 설명]({image_url})'
        })
        
    except Exception as e:
        logger.error(f"학습 포스트 이미지 업로드 오류: {e}", exc_info=True)
        return jsonify({
            'success': False, 
            'message': f'이미지 업로드 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/admin/learning/delete-image', methods=['POST'])
@login_required
def admin_learning_delete_image():
    """학습 포스트 이미지 삭제 API"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    try:
        filename = request.json.get('filename')
        
        if not filename:
            return jsonify({'success': False, 'message': '파일명이 제공되지 않았습니다.'}), 400
        
        # 보안: 파일명 검증 (path traversal 방지)
        filename = secure_filename(filename)
        if not filename or '..' in filename or filename.startswith('/'):
            return jsonify({'success': False, 'message': '잘못된 파일명입니다.'}), 400
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # 파일 존재 확인 및 삭제
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"학습 포스트 이미지 삭제: {filename}")
            return jsonify({'success': True, 'message': '이미지가 삭제되었습니다.'})
        else:
            return jsonify({'success': False, 'message': '파일을 찾을 수 없습니다.'}), 404
            
    except Exception as e:
        logger.error(f"학습 포스트 이미지 삭제 오류: {e}", exc_info=True)
        return jsonify({
            'success': False, 
            'message': f'이미지 삭제 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/admin/learning/upload-bulk-images', methods=['POST'])
@login_required
def admin_learning_upload_bulk_images():
    """다중 이미지 업로드 API (선택사항)"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    try:
        uploaded_files = []
        failed_files = []
        
        # 다중 파일 처리
        for key in request.files:
            files = request.files.getlist(key)
            
            for file in files:
                if file.filename == '':
                    continue
                
                try:
                    # 개별 파일 업로드 처리
                    if not file.content_type.startswith('image/'):
                        failed_files.append({
                            'filename': file.filename,
                            'error': '이미지 파일이 아닙니다.'
                        })
                        continue
                    
                    filename = secure_filename(file.filename)
                    if not filename:
                        failed_files.append({
                            'filename': file.filename,
                            'error': '잘못된 파일명입니다.'
                        })
                        continue
                    
                    # 고유한 파일명 생성
                    name, ext = os.path.splitext(filename)
                    unique_filename = f"content_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}{ext}"
                    
                    # 파일 저장
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    
                    # 이미지 최적화
                    try:
                        optimize_image(file_path)
                    except Exception as e:
                        logger.warning(f"이미지 최적화 실패: {e}")
                    
                    # URL 생성
                    image_url = url_for('uploaded_file', filename=unique_filename, _external=False)
                    
                    uploaded_files.append({
                        'original_name': file.filename,
                        'filename': unique_filename,
                        'url': image_url,
                        'markdown': f'![{name}]({image_url})'
                    })
                    
                except Exception as e:
                    failed_files.append({
                        'filename': file.filename,
                        'error': str(e)
                    })
        
        logger.info(f"다중 이미지 업로드 완료: {len(uploaded_files)}개 성공, {len(failed_files)}개 실패")
        
        return jsonify({
            'success': True,
            'message': f'{len(uploaded_files)}개 이미지 업로드 완료',
            'uploaded_files': uploaded_files,
            'failed_files': failed_files
        })
        
    except Exception as e:
        logger.error(f"다중 이미지 업로드 오류: {e}", exc_info=True)
        return jsonify({
            'success': False, 
            'message': f'다중 이미지 업로드 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 디버그용 샘플 데이터 생성 라우트
@app.route('/debug/create-sample-learning-data')
def create_sample_learning_data():
    """샘플 학습 데이터 생성"""
    try:
        if LearningCategory.query.count() == 0:
            init_learning_default_data()
            db.session.commit()
        
        programming_cat = LearningCategory.query.filter_by(name='Programming').first()
        if programming_cat and LearningPost.query.count() == 0:
            sample_post = LearningPost(
                title='Python 기초 학습',
                slug='python-basics-learning',
                content='# Python 기초\n\nPython은 강력하고 배우기 쉬운 프로그래밍 언어입니다.',
                summary='Python 프로그래밍 언어의 기초를 학습합니다.',
                category_id=programming_cat.id,
                tags='Python, Programming, Basics',
                difficulty='beginner',
                reading_time=5,
                is_published=True,
                published_at=datetime.utcnow()
            )
            db.session.add(sample_post)
            db.session.commit()
        
        return True
    except Exception as e:
        logger.error(f"샘플 데이터 생성 실패: {e}")
        db.session.rollback()
        return False

def debug_create_sample_data():
    """샘플 학습 데이터 생성 (디버그용)"""
    if not app.debug:
        return "Debug mode only", 404
    
    try:
        success = create_sample_learning_data()
        if success:
            return jsonify({
                'success': True,
                'message': '샘플 데이터가 생성되었습니다.',
                'categories': LearningCategory.query.count(),
                'posts': LearningPost.query.count()
            })
        else:
            return jsonify({'success': False, 'message': '샘플 데이터 생성에 실패했습니다.'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500





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

# 템플릿 필터 추가
@app.template_filter('nl2br')
def nl2br_filter(text):
    """개행 문자를 HTML <br> 태그로 변환"""
    if text is None:
        return ''
    # HTML 이스케이프 처리 후 개행을 <br>로 변환
    from markupsafe import Markup, escape
    result = escape(text).replace('\n', Markup('<br>\n'))
    return Markup(result)



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