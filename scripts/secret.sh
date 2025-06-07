#!/bin/bash

# 간소화된 Kubernetes Secret 생성 스크립트
# 하나의 데이터베이스 계정으로 통합 관리

set -e

echo "🔐 애플리케이션 전용 사용자 Secret 생성기"
echo "============================================"

# .env 파일 로드
if [ -f ".env" ]; then
    source .env
    echo "✅ .env 파일을 로드했습니다."
else
    echo "❌ .env 파일을 찾을 수 없습니다."
    echo "💡 .env.example을 복사하여 .env 파일을 먼저 생성해주세요:"
    echo "   cp .env.example .env"
    exit 1
fi

# Base64 인코딩 함수
encode_base64() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo -n "$1" | base64
    else
        # Linux
        echo -n "$1" | base64 -w 0
    fi
}

# 애플리케이션 전용 MySQL 사용자 설정
SECRET_KEY=${SECRET_KEY:-"your-super-secret-key-change-this-in-production"}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-"secure_root_password_here"}
DB_HOST=${DB_HOST:-"mysql-service.db.svc.cluster.local"}
DB_PORT=${DB_PORT:-"3306"}
DB_NAME=${DB_NAME:-"portfolio"}
DB_USER=${DB_USER:-"portfolio_app"}
DB_PASSWORD=${DB_PASSWORD:-"secure_app_password_here"}
ADMIN_USERNAME=${ADMIN_USERNAME:-"admin"}
ADMIN_EMAIL=${ADMIN_EMAIL:-"admin@example.com"}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-"secure_admin_password_here"}

# DATABASE_URL 자동 구성
DATABASE_URL="mysql+pymysql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# 보안 검증
echo ""
echo "🔍 보안 설정 검증..."

warnings=0
if [ "$SECRET_KEY" = "your-super-secret-key-change-this-in-production" ]; then
    echo "⚠️  WARNING: 기본 SECRET_KEY를 사용 중입니다. 변경하세요!"
    warnings=$((warnings + 1))
fi

if [ "$MYSQL_ROOT_PASSWORD" = "secure_root_password_here" ]; then
    echo "⚠️  WARNING: 기본 MySQL Root 비밀번호를 사용 중입니다. 변경하세요!"
    warnings=$((warnings + 1))
fi

if [ "$ADMIN_PASSWORD" = "secure_admin_password_here" ] || [ "$ADMIN_PASSWORD" = "admin123" ]; then
    echo "⚠️  WARNING: 기본 관리자 비밀번호를 사용 중입니다. 변경하세요!"
    warnings=$((warnings + 1))
fi

if [ "$DB_PASSWORD" = "secure_app_password_here" ] || [ "$DB_PASSWORD" = "1234" ]; then
    echo "⚠️  WARNING: 기본 애플리케이션 DB 비밀번호를 사용 중입니다. 변경하세요!"
    warnings=$((warnings + 1))
fi

if [ "$MYSQL_ROOT_PASSWORD" = "$DB_PASSWORD" ]; then
    echo "⚠️  WARNING: Root 비밀번호와 앱 비밀번호가 같습니다. 다르게 설정하세요!"
    warnings=$((warnings + 1))
fi

if [ ${#SECRET_KEY} -lt 32 ]; then
    echo "⚠️  WARNING: SECRET_KEY가 너무 짧습니다. 32자 이상 권장!"
    warnings=$((warnings + 1))
fi

if [ $warnings -gt 0 ]; then
    echo ""
    echo "⚠️  $warnings 개의 보안 경고가 있습니다."
    echo ""
    read -p "계속 진행하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 취소되었습니다."
        exit 1
    fi
fi

# k8s 디렉토리 확인
if [ ! -d "k8s" ]; then
    echo "📁 k8s 디렉토리를 생성합니다..."
    mkdir -p k8s
fi

echo ""
echo "🔑 애플리케이션 전용 사용자 Secret 파일을 생성합니다..."

# 애플리케이션 전용 사용자 Secret YAML 파일 생성
cat > k8s/secrets.yaml << EOF
# k8s/secrets.yaml
# 애플리케이션 전용 MySQL 사용자 설정
# 생성 시간: $(date)

# Flask 애플리케이션 Secret
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: was
  labels:
    app: portfolio
    component: backend
type: Opaque
data:
  # 애플리케이션 전용 데이터베이스 연결 정보
  database-url: $(encode_base64 "$DATABASE_URL")
  db-host: $(encode_base64 "$DB_HOST")
  db-port: $(encode_base64 "$DB_PORT")
  db-name: $(encode_base64 "$DB_NAME")
  db-user: $(encode_base64 "$DB_USER")
  db-password: $(encode_base64 "$DB_PASSWORD")
  
  # Flask 애플리케이션 설정
  secret-key: $(encode_base64 "$SECRET_KEY")
  
  # 관리자 계정 정보
  admin-username: $(encode_base64 "$ADMIN_USERNAME")
  admin-email: $(encode_base64 "$ADMIN_EMAIL")
  admin-password: $(encode_base64 "$ADMIN_PASSWORD")

---
# MySQL 데이터베이스 Secret (Root + 애플리케이션 사용자)
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secrets
  namespace: db
  labels:
    app: mysql
    component: database
type: Opaque
data:
  # MySQL Root 계정 (관리용)
  root-password: $(encode_base64 "$MYSQL_ROOT_PASSWORD")
  # 애플리케이션 전용 계정 (MYSQL_USER/MYSQL_PASSWORD로 자동 생성됨)
  app-user: $(encode_base64 "$DB_USER")
  app-password: $(encode_base64 "$DB_PASSWORD")
  
---
# ConfigMap for non-sensitive configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: was
  labels:
    app: portfolio
    component: backend
data:
  FLASK_ENV: "production"
  PYTHONUNBUFFERED: "1"
  MAX_CONTENT_LENGTH: "31457280"
  UPLOAD_FOLDER: "/app/uploads"
  MAX_FILE_SIZE_MB: "30"
EOF

echo "✅ k8s/secrets.yaml 파일이 생성되었습니다."

# 권한 설정
chmod 600 k8s/secrets.yaml
echo "🔒 Secret 파일 권한을 600으로 설정했습니다."

echo ""
echo "📋 생성된 설정 요약 (애플리케이션 전용 사용자):"
echo "┌─────────────────────────────────────────┐"
echo "│ MySQL Root 계정 (관리용)                 │"
echo "├─────────────────────────────────────────┤"
echo "│ User: root"
echo "│ Password: [MYSQL_ROOT_PASSWORD]"
echo "│ 용도: 데이터베이스 관리, 백업, 복구"
echo "├─────────────────────────────────────────┤"
echo "│ 애플리케이션 전용 계정 (런타임용)         │"
echo "├─────────────────────────────────────────┤"
echo "│ Host: ${DB_HOST}"
echo "│ Port: ${DB_PORT}"
echo "│ Database: ${DB_NAME}"
echo "│ User: ${DB_USER}"
echo "│ Password: [DB_PASSWORD]"
echo "│ 권한: ${DB_NAME} 데이터베이스만"
echo "├─────────────────────────────────────────┤"
echo "│ 관리자 계정                              │"
echo "├─────────────────────────────────────────┤"
echo "│ Username: ${ADMIN_USERNAME}"
echo "│ Email: ${ADMIN_EMAIL}"
echo "│ Password: [PROTECTED]"
echo "└─────────────────────────────────────────┘"

echo ""
echo "✨ 보안 개선 사항:"
echo "✅ MySQL Root와 애플리케이션 계정 분리"
echo "✅ 애플리케이션은 필요한 권한만 보유"
echo "✅ 최소 권한 원칙 적용"
echo "✅ 데이터베이스 관리와 런타임 분리"

echo ""
echo "🔐 계정별 역할:"
echo "• Root 계정: 데이터베이스 관리, 사용자 생성, 백업"
echo "• ${DB_USER}: 애플리케이션 데이터 읽기/쓰기만"

echo ""
echo "⚠️  보안 알림:"
echo "- .env 파일과 k8s/secrets.yaml은 Git에 커밋하지 마세요"
echo "- 두 비밀번호는 반드시 다르게 설정하세요"
echo "- 프로덕션에서는 더 강력한 비밀번호를 사용하세요"
echo "- 애플리케이션 계정은 ${DB_NAME} 데이터베이스만 접근 가능합니다"
