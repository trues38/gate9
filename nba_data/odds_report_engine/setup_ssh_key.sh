#!/bin/bash
# VPS SSH 키 등록 (비밀번호 없이 연결)

echo "🔑 VPS SSH 키 등록 설정..."
echo ""

# 1. 로컬에 SSH 키가 있는지 확인
if [ ! -f ~/.ssh/id_rsa.pub ]; then
    echo "📝 SSH 키가 없습니다. 생성 중..."
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
    echo "✅ SSH 키 생성 완료"
else
    echo "✅ SSH 키 이미 존재"
fi

echo ""
echo "📤 VPS에 공개 키 등록 중..."
echo "   (VPS root 비밀번호 입력 필요)"
echo ""

# 2. VPS에 공개 키 복사
ssh-copy-id root@141.164.35.214

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SSH 키 등록 완료!"
    echo ""
    echo "이제 비밀번호 없이 연결 가능:"
    echo "  ssh root@141.164.35.214"
    echo ""
    echo "SSH 터널도 자동 연결:"
    echo "  ./start_vps_tunnel_auto.sh"
else
    echo ""
    echo "❌ SSH 키 등록 실패"
    echo "   수동으로 비밀번호 입력하려면:"
    echo "   ./start_vps_tunnel.sh"
fi
