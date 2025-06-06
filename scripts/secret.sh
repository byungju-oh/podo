#!/bin/bash

# Kubernetes Secret 생성 스크립트
# .env 파일에서 환경변수를 읽어 base64 인코딩하여 Secret YAML 생성

set -e

echo "🔐 Kubernetes Secret 생성기"
echo "=================================="

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

# 환경변수 기본값 설정
SECRET_KEY=${SECRET_KEY:-"your-super-secret-key-change-this-in-production"}
DB_HOST=${DB_HOST:-"mysql-service.db.svc.cluster.local"}
DB_PORT=${DB_PORT:-"3306"}
DB_NAME=${DB_NAME:-"portfolio"}
DB_USER=${DB_USER:-"root"}
DB_PASSWORD=${DB_PASSWORD:-"1234"}
ADMIN_USERNAME=${ADMIN_USERNAME:-"admin"}
ADMIN_EMAIL=${ADMIN_EMAIL:-"admin@example.com"}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-"admin123"}

# DATABASE_URL 구성
DATABASE_URL="mysql+pymysql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# 보안 검증
echo ""
echo "🔍 보안 설정 검증..."

# 기본값 사용 경고
warnings=0
if [ "$SECRET_KEY" = "your-super-secret-key-change-this-in-production" ]; then
    echo "⚠️  WARNING: 기본 SECRET_KEY를 사용 중입니다. 프로덕션에서는 변경하세요!"
    warnings=$((warnings + 1))
fi

if [ "$ADMIN_PASSWORD" = "admin123" ]; then
    echo "⚠️  WARNING: 기본 관리자 비밀번호를 사용 중입니다. 보안을 위해 변경하세요!"
    warnings=$((warnings + 1))
fi

if [ "$DB_PASSWORD" = "1234" ]; then
    echo "⚠️  WARNING: 기본 데이터베이스 비밀번호를 사용 중입니다. 변경을 권장합니다!"
    warnings=$((warnings + 1))
fi

if [ $warnings -gt 0 ]; then
    echo ""
    echo "⚠️  $warnings 개의 보안 경고가 있습니다. 프로덕션 배포 전에 해결해주세요."
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
echo "🔑 Kubernetes Secret 파일을 생성합니다..."

# Secret YAML 파일 생성
cat > k8s/secrets.yaml << EOF
# k8s/secrets.yaml
# 이 파일은 generate-secrets.sh 스크립트에 의해 자동 생성됩니다.
# 수동으로 편집하지 마세요.
# 생성 시간: $(date)

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
  # 데이터베이스 연결 정보
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
# MySQL 데이터베이스 Secret
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
  root-password: $(encode_base64 "$DB_PASSWORD")
  
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
  MAX_CONTENT_LENGTH: "104857600"
  UPLOAD_FOLDER: "/app/uploads"
  MAX_FILE_SIZE_MB: "30"
EOF

echo "✅ k8s/secrets.yaml 파일이 생성되었습니다."

# 권한 설정
chmod 600 k8s/secrets.yaml
echo "🔒 Secret 파일 권한을 600으로 설정했습니다."

echo ""
echo "📋 생성된 설정 요약:"
echo "┌─────────────────────────────────────────┐"
echo "│ 데이터베이스 설정                        │"
echo "├─────────────────────────────────────────┤"
echo "│ Host: ${DB_HOST}"
echo "│ Port: ${DB_PORT}"
echo "│ Database: ${DB_NAME}"
echo "│ User: ${DB_USER}"
echo "│ Password: [PROTECTED]"
echo "├─────────────────────────────────────────┤"
echo "│ 관리자 계정                              │"
echo "├─────────────────────────────────────────┤"
echo "│ Username: ${ADMIN_USERNAME}"
echo "│ Email: ${ADMIN_EMAIL}"
echo "│ Password: [PROTECTED]"
echo "├─────────────────────────────────────────┤"
echo "│ 보안 설정                               │"
echo "├─────────────────────────────────────────┤"
echo "│ Secret Key: [PROTECTED]"
echo "│ Flask Env: production"
echo "└─────────────────────────────────────────┘"

# 추가 검증
echo ""
echo "🔍 Secret 내용 검증:"
echo "Database URL: $(echo "$DATABASE_URL" | head -c 30)..."
echo "Admin Username: $ADMIN_USERNAME"

echo ""
echo "⚠️  보안 알림:"
echo "- .env 파일과 k8s/secrets.yaml은 절대 Git에 커밋하지 마세요"
echo "- 프로덕션에서는 더 강력한 비밀번호를 사용하세요"
echo "- Secret 파일 권한은 600으로 유지하세요"

echo ""
echo "🚀 다음 단계:"
echo "   kubectl apply -f k8s/secrets.yaml"

echo ""
echo "✨ Secret 생성이 완료되었습니다!"