# 🌟 IT 엔지니어 포트폴리오 웹사이트

클라우드 네이티브 환경에서 Kubernetes로 배포되는 Flask 기반의 풀스택 개인 포트폴리오 웹사이트입니다. 프로젝트 관리, 경력 소개, 기술 스택 전시, 학습 블로그 등의 기능을 제공합니다.

![Portfolio Preview](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Kubernetes](https://img.shields.io/badge/Kubernetes-v1.28+-blue)
![Flask](https://img.shields.io/badge/Flask-2.3.3-red)
![Python](https://img.shields.io/badge/Python-3.9+-yellow)

## ✨ 주요 기능

### 🎯 핵심 기능
- **포트폴리오 관리**: 프로젝트 CRUD 및 카테고리별 분류 (웹/앱, 인프라, 데이터분석, AI/ML, 아트워크)
- **학습 블로그**: 마크다운 기반의 학습 포스트 작성 및 관리 시스템
- **반응형 디자인**: 모바일 우선 설계로 모든 디바이스 완벽 지원
- **동적 배경**: 아트워크 프로젝트를 활용한 슬라이드쇼 배경
- **관리자 대시보드**: 컨텐츠 관리를 위한 보안 관리 인터페이스

### 📋 상세 기능
- **프로젝트 상세 페이지**: GitHub/Demo 링크, 기술 스택, 성과 지표 포함
- **기술 스택 시각화**: 카테고리별 숙련도 및 경험 표시
- **경력 및 학력 타임라인**: 시간순 정렬된 경력 사항
- **자격증 관리**: 취득 자격증 및 만료일 추적
- **이미지 자동 최적화**: Pillow를 활용한 업로드 이미지 압축 및 리사이징
- **조회수 추적**: 프로젝트별 조회수 통계
- **검색 기능**: 학습 포스트 검색 및 자동완성
- **SEO 최적화**: 메타태그 및 구조화된 데이터

## 🏗️ 아키텍처

### 전체 시스템 구조
```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Ingress (NGINX)                          │
│              SSL/TLS Termination                           │
│             byungju.me / www.byungju.me                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  Namespace: web                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              NGINX Service                          │   │
│  │         (Static Files, Reverse Proxy)              │   │
│  └─────────────────────┬───────────────────────────────┘   │
└────────────────────────┼───────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────┐
│                  Namespace: was                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Flask Application                      │  │
│  │    - Portfolio Management                          │  │
│  │    - Learning Blog                                 │  │
│  │    - Admin Dashboard                               │  │
│  │    - Image Processing                              │  │
│  └─────────────────────┬───────────────────────────────┘  │
└────────────────────────┼──────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────┐
│                  Namespace: db                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                MySQL 8.0                           │  │
│  │         - User Authentication                      │  │
│  │         - Project Data                             │  │
│  │         - Learning Posts                           │  │
│  │         - File Metadata                            │  │
│  └─────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### Kubernetes 리소스 구조
```
Kubernetes Cluster
├── Namespaces
│   ├── web (Frontend Tier)
│   ├── was (Backend Tier)
│   └── db (Database Tier)
├── Persistent Storage
│   ├── MySQL Data (20Gi)
│   └── Uploaded Files (20Gi)
├── Secrets Management
│   ├── Database Credentials
│   ├── Admin Credentials
│   └── Application Secret Keys
└── Network Policies
    ├── SSL Termination
    ├── Inter-service Communication
    └── External Access Control
```

## 🚀 기술 스택

### Backend Infrastructure
- **Flask 2.3.3**: 웹 애플리케이션 프레임워크
- **SQLAlchemy**: ORM 및 데이터베이스 관리
- **Flask-Login**: 사용자 세션 관리
- **Flask-WTF**: 폼 처리 및 CSRF 보호
- **Flask-CSRF**: Cross-Site Request Forgery 방어
- **Pillow**: 이미지 처리 및 최적화
- **Markdown**: 학습 포스트 컨텐츠 렌더링

### Frontend Stack
- **Bootstrap 5.3.0**: 반응형 UI 프레임워크
- **Font Awesome 6.4.0**: 아이콘 라이브러리
- **Vanilla JavaScript**: 동적 상호작용
- **CSS3**: 커스텀 애니메이션 및 스타일링

### Database & Storage
- **MySQL 8.0**: 주 데이터베이스 (프로덕션)
- **SQLite**: 개발 환경 데이터베이스
- **Persistent Volumes**: Kubernetes 영구 저장소

### Container & Orchestration
- **Docker**: 컨테이너화
- **Kubernetes**: 컨테이너 오케스트레이션
- **NGINX**: 리버스 프록시 및 정적 파일 서빙
- **K3s**: 경량 Kubernetes 배포 (권장)

### DevOps & Deployment
- **Helm**: Kubernetes 패키지 관리 (선택사항)
- **Let's Encrypt**: 자동 SSL/TLS 인증서
- **cert-manager**: Kubernetes SSL 인증서 관리
- **NGINX Ingress Controller**: 트래픽 라우팅

## 📦 쿠버네티스 배포

### 1. 사전 요구사항
```bash
# Kubernetes 클러스터 (v1.28 이상)
kubectl version --short

# cert-manager 설치 (Let's Encrypt 용)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# NGINX Ingress Controller 설치
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.0/deploy/static/provider/cloud/deploy.yaml
```

### 2. 네임스페이스 생성
```bash
kubectl apply -f k8s/namespaces.yaml
```

### 3. Secrets 생성
```bash
# 환경변수 설정 후 실행
chmod +x scripts/secret.sh
./scripts/secret.sh
kubectl apply -f k8s/secrets.yaml
```

### 4. 데이터베이스 배포
```bash
kubectl apply -f k8s/db-deployment.yaml
```

### 5. WAS(백엔드) 배포
```bash
# Docker 이미지 빌드
docker build -t portfolio-was:latest ./was/

# k3s 환경에서 이미지 로드 (로컬 빌드 시)
docker save portfolio-was:latest | sudo k3s ctr images import -

# 배포
kubectl apply -f k8s/was-deployment.yaml
```

### 6. Web Server 배포
```bash
# Docker 이미지 빌드
docker build -t portfolio-web:latest ./web/

# k3s 환경에서 이미지 로드
docker save portfolio-web:latest | sudo k3s ctr images import -

# 배포
kubectl apply -f k8s/web-deployment.yaml
```

### 7. Ingress 설정
```bash
# 도메인을 본인의 도메인으로 수정 후
kubectl apply -f k8s/ingress.yaml
```

## 🔧 설정 및 환경변수

### 환경변수 구성 (.env)
```env
# 보안 설정
SECRET_KEY=your-super-secret-key-change-this-in-production
CSRF_SECRET_KEY=another-secret-key-for-csrf

# 데이터베이스 설정
DB_HOST=mysql-service.db.svc.cluster.local
DB_PORT=3306
DB_NAME=portfolio
DB_USER=root
DB_PASSWORD=your-secure-password

# 관리자 계정
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=your-secure-admin-password

# 애플리케이션 설정
FLASK_ENV=production
PYTHONUNBUFFERED=1
MAX_CONTENT_LENGTH=31457280  # 30MB
UPLOAD_FOLDER=/app/uploads
MAX_FILE_SIZE_MB=30
```

### Kubernetes 리소스 사양
```yaml
# WAS 리소스 설정
resources:
  requests:
    memory: "512Mi"
    cpu: "200m"
  limits:
    memory: "1Gi"
    cpu: "500m"

# Web Server 리소스 설정
resources:
  requests:
    memory: "64Mi"
    cpu: "100m"
  limits:
    memory: "128Mi"
    cpu: "200m"

# MySQL 리소스 설정
resources:
  requests:
    memory: "512Mi"
    cpu: "300m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

## 📁 프로젝트 구조

```
portfolio-website/
├── was/                          # Flask 백엔드 애플리케이션
│   ├── app.py                   # 메인 애플리케이션 파일
│   ├── Dockerfile               # WAS 컨테이너 설정
│   ├── requirements.txt         # Python 의존성
│   ├── templates/               # Jinja2 템플릿
│   │   ├── base.html           # 기본 레이아웃
│   │   ├── index.html          # 메인 페이지
│   │   ├── portfolio.html      # 프로젝트 목록
│   │   ├── about.html          # 소개 페이지
│   │   ├── admin/              # 관리자 페이지
│   │   └── learning/           # 학습 블로그 페이지
│   └── static/                 # 정적 파일
├── web/                         # NGINX 웹서버
│   ├── Dockerfile              # 웹서버 컨테이너 설정
│   ├── nginx.conf              # NGINX 메인 설정
│   ├── default.conf            # 사이트별 설정
│   └── static/                 # 정적 리소스
├── mysql/                       # MySQL 설정
│   └── conf.d/
│       └── custom.cnf          # MySQL 커스텀 설정
├── k8s/                        # Kubernetes 매니페스트
│   ├── namespaces.yaml         # 네임스페이스 정의
│   ├── secrets.yaml            # 시크릿 정의 (gitignore)
│   ├── db-deployment.yaml      # MySQL 배포
│   ├── was-deployment.yaml     # Flask 앱 배포
│   ├── web-deployment.yaml     # NGINX 배포
│   ├── ingress.yaml            # 외부 접근 설정
│   └── pvc-was.yaml           # 영구 볼륨 클레임
├── scripts/                    # 유틸리티 스크립트
│   └── secret.sh              # 시크릿 생성 스크립트
├── .env.example               # 환경변수 예시
├── .gitignore                 # Git 제외 파일
├── docker-compose.yml         # 로컬 개발용 (선택사항)
└── README.md                  # 프로젝트 문서
```

## 🎨 주요 기능 상세

### 1. 프로젝트 관리 시스템
- **CRUD 연산**: 프로젝트 생성, 읽기, 수정, 삭제
- **카테고리 필터링**: 기술/인프라/데이터/AI/아트워크별 분류
- **이미지 업로드**: 자동 리사이징 및 최적화 (30MB 지원)
- **기술 스택 태깅**: 쉼표로 구분된 기술 목록
- **GitHub/Demo 링크**: 외부 리소스 연동
- **조회수 추적**: 실시간 통계

### 2. 학습 블로그 시스템
- **마크다운 에디터**: 코드 하이라이팅 지원
- **카테고리 관리**: 색상 및 아이콘 커스터마이징
- **태그 시스템**: 검색 및 필터링 지원
- **이미지 업로드**: 본문 내 이미지 삽입
- **발행 관리**: 초안/발행 상태 관리
- **검색 기능**: 제목/내용/태그 기반 검색

### 3. 반응형 디자인
- **모바일 우선**: 320px부터 4K까지 지원
- **다크모드**: 사용자 선호도 기반 테마
- **애니메이션**: CSS3 및 JavaScript 기반
- **터치 지원**: 스와이프 제스처 구현
- **성능 최적화**: 지연 로딩 및 캐싱

### 4. 보안 기능
- **CSRF 보호**: 모든 폼에 토큰 적용
- **파일 업로드 보안**: 형식 및 크기 제한
- **세션 관리**: Flask-Login 기반 인증
- **SQL 인젝션 방지**: SQLAlchemy ORM 사용
- **XSS 방지**: 자동 이스케이핑

## 🔐 보안 고려사항

### Kubernetes 보안
```yaml
# Pod Security Context
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: false
  capabilities:
    drop:
    - ALL
```

### 네트워크 보안
- **Network Policies**: 네임스페이스 간 트래픽 제어
- **TLS 종료**: Ingress에서 SSL/TLS 처리
- **서비스 통신**: 클러스터 내부 DNS 사용

### 애플리케이션 보안
- **환경변수 격리**: Kubernetes Secrets 사용
- **파일 권한**: 최소 권한 원칙 적용
- **로그 보안**: 민감정보 마스킹

## 📈 모니터링 및 로깅

### Health Checks
```yaml
# Liveness Probe
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 60
  periodSeconds: 15

# Readiness Probe
readinessProbe:
  httpGet:
    path: /readiness
    port: 5000
  initialDelaySeconds: 15
  periodSeconds: 5
```

### 로그 관리
- **구조화된 로깅**: JSON 형태 로그 출력
- **로그 레벨**: DEBUG/INFO/WARNING/ERROR
- **액세스 로그**: NGINX 접근 기록
- **에러 추적**: 스택 트레이스 포함

## 🚀 성능 최적화

### 이미지 최적화
```python
def optimize_image(file_path, max_width=1920, max_height=1080, quality=85):
    """이미지 자동 최적화"""
    with Image.open(file_path) as img:
        # EXIF 회전 보정
        # 크기 조정
        # 형식 변환 (JPEG/PNG)
        # 품질 압축
```

### 데이터베이스 최적화
- **인덱싱**: 주요 검색 필드에 인덱스 적용
- **연결 풀링**: SQLAlchemy 연결 풀 사용
- **쿼리 최적화**: N+1 문제 방지
- **캐싱**: 정적 데이터 메모리 캐싱

### Kubernetes 최적화
- **리소스 제한**: CPU/메모리 적절한 설정
- **HPA**: 자동 수평 확장 설정
- **PDB**: Pod Disruption Budget 적용
- **Node Affinity**: 노드 배치 최적화

## 🐛 문제 해결

### 일반적인 문제들

**1. Pod가 시작되지 않는 경우**
```bash
# Pod 상태 확인
kubectl get pods -n was
kubectl describe pod <pod-name> -n was
kubectl logs <pod-name> -n was

# 일반적인 원인
# - 이미지 pull 실패
# - Secret 설정 오류
# - 리소스 부족
# - Volume 마운트 실패
```

**2. 데이터베이스 연결 오류**
```bash
# MySQL 서비스 확인
kubectl get svc -n db
kubectl logs deployment/mysql-deployment -n db

# 연결 테스트
kubectl exec -it <was-pod> -n was -- python -c "
from app import db
db.session.execute('SELECT 1')
print('DB Connection OK')
"
```

**3. 이미지 업로드 실패**
```bash
# PVC 상태 확인
kubectl get pvc -n was
kubectl describe pvc upload-pvc -n was

# Volume 마운트 확인
kubectl exec -it <was-pod> -n was -- ls -la /app/uploads
kubectl exec -it <was-pod> -n was -- touch /app/uploads/test.txt
```

**4. SSL 인증서 문제**
```bash
# cert-manager 상태 확인
kubectl get certificates -n web
kubectl describe certificate byungju-me-tls -n web

# Let's Encrypt 클러스터 이슈어 확인
kubectl get clusterissuer
```

### 로그 분석
```bash
# 전체 로그 모니터링
kubectl logs -f deployment/flask-deployment -n was

# 에러 로그만 필터링
kubectl logs deployment/flask-deployment -n was | grep ERROR

# 특정 시간대 로그
kubectl logs deployment/flask-deployment -n was --since=1h
```

## 📊 성능 메트릭

### 리소스 사용량 모니터링
```bash
# 리소스 사용량 확인
kubectl top pods -n was
kubectl top nodes

# 메트릭 서버 필요시 설치
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### 애플리케이션 메트릭
- **응답 시간**: 평균 200ms 이하
- **처리량**: 초당 100+ 요청
- **에러율**: 1% 이하
- **가용성**: 99.9% 이상

## 🔄 CI/CD 파이프라인 (권장)

### GitHub Actions 예시
```yaml
name: Deploy to Kubernetes
on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Build and Push Docker Images
      run: |
        docker build -t ${{ secrets.REGISTRY }}/portfolio-was:${{ github.sha }} ./was/
        docker build -t ${{ secrets.REGISTRY }}/portfolio-web:${{ github.sha }} ./web/
        docker push ${{ secrets.REGISTRY }}/portfolio-was:${{ github.sha }}
        docker push ${{ secrets.REGISTRY }}/portfolio-web:${{ github.sha }}
    
    - name: Deploy to Kubernetes
      uses: azure/k8s-deploy@v1
      with:
        manifests: |
          k8s/was-deployment.yaml
          k8s/web-deployment.yaml
        images: |
          ${{ secrets.REGISTRY }}/portfolio-was:${{ github.sha }}
          ${{ secrets.REGISTRY }}/portfolio-web:${{ github.sha }}
```

## 🚢 배포 전략

### 1. Rolling Update (권장)
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

### 2. Blue-Green Deployment
```bash
# Green 환경 배포
kubectl apply -f k8s/was-deployment-green.yaml

# 트래픽 전환
kubectl patch service flask-service -p '{"spec":{"selector":{"version":"green"}}}'

# Blue 환경 정리
kubectl delete -f k8s/was-deployment-blue.yaml
```

### 3. Canary Deployment
```yaml
# Canary용 별도 배포
replicas: 1  # 전체 트래픽의 10%
selector:
  matchLabels:
    app: flask
    version: canary
```

## 📚 API 문서

### 공개 엔드포인트
```
GET  /                              # 메인 페이지
GET  /portfolio                     # 프로젝트 목록
GET  /portfolio?type=tech           # 필터링된 프로젝트
GET  /project/<int:id>              # 프로젝트 상세
GET  /about                         # 소개 페이지
GET  /learning                      # 학습 블로그
GET  /learning/post/<slug>          # 블로그 포스트
GET  /learning/category/<int:id>    # 카테고리별 포스트
GET  /learning/search?q=query       # 검색 결과
GET  /uploads/<filename>            # 업로드된 파일
```

### 관리자 엔드포인트 (인증 필요)
```
GET  /admin                         # 관리자 대시보드
GET  /admin/add_work               # 프로젝트 추가 폼
POST /admin/add_work               # 프로젝트 생성
GET  /admin/edit_work/<int:id>     # 프로젝트 수정 폼
POST /admin/edit_work/<int:id>     # 프로젝트 업데이트
DEL  /admin/delete_work/<int:id>   # 프로젝트 삭제

GET  /admin/learning               # 학습 블로그 관리
GET  /admin/learning/posts         # 포스트 목록
GET  /admin/learning/post/new      # 새 포스트 작성
POST /admin/learning/post/new      # 포스트 생성
GET  /admin/learning/post/<id>/edit # 포스트 수정
DEL  /admin/learning/post/<id>/delete # 포스트 삭제
```

### API 응답 형식
```json
{
  "success": true,
  "message": "작업이 완료되었습니다.",
  "data": {
    "id": 123,
    "title": "프로젝트 제목"
  }
}
```

## 🤝 기여하기

### 개발 환경 설정
```bash
# 1. 저장소 포크 및 클론
git clone https://github.com/yourusername/portfolio-website.git
cd portfolio-website

# 2. 가상환경 설정
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 개발 의존성 설치
pip install -r was/requirements.txt

# 4. 로컬 개발 서버 실행
cd was
python app.py
```

### 코드 스타일
- **Python**: PEP 8 준수
- **JavaScript**: ES6+ 표준
- **HTML/CSS**: BEM 방법론 권장
- **Git**: Conventional Commits 사용

### Pull Request 프로세스
1. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
2. 변경사항 커밋 (`git commit -m 'feat: add amazing feature'`)
3. 브랜치 푸시 (`git push origin feature/amazing-feature`)
4. Pull Request 생성

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 연락처

- **이메일**: qudwndh@gmail.com

- **웹사이트**: [https://byungju.me](https://byungju.me)

## 🙏 감사의 말

- [Flask](https://flask.palletsprojects.com/) - 훌륭한 웹 프레임워크
- [Kubernetes](https://kubernetes.io/) - 컨테이너 오케스트레이션 플랫폼
- [Bootstrap](https://getbootstrap.com/) - 반응형 UI 프레임워크
- [Font Awesome](https://fontawesome.com/) - 아이콘 라이브러리
- [MySQL](https://www.mysql.com/) - 안정적인 데이터베이스
- [NGINX](https://nginx.org/) - 고성능 웹서버
- [Let's Encrypt](https://letsencrypt.org/) - 무료 SSL 인증서

## 📋 체크리스트

### 배포 전 확인사항
- [ ] 환경변수 설정 완료
- [ ] 도메인 DNS 설정
- [ ] SSL 인증서 설정
- [ ] 데이터베이스 백업
- [ ] 이미지 빌드 및 테스트
- [ ] 리소스 제한 설정
- [ ] 모니터링 설정
- [ ] 로그 수집 설정

### 운영 중 체크사항
- [ ] 정기적인 백업
- [ ] 보안 업데이트
- [ ] 성능 모니터링
- [ ] 로그 분석
- [ ] 인증서 만료 확인
- [ ] 리소스 사용률 체크

---

**Made with ❤️ for the Cloud-Native Community**
