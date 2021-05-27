# aitube/Dockerfile

# python:3-slim 이미지 사용
FROM        python:3-slim

# 배포 서버 업데이트
RUN         apt -y -qq update & apt -y -qq dist-upgrade && apt -y -qq autoremove
# pip 업그레이드
RUN         pip install --upgrade pip

# /tmp 폴더에 requirements.txt 파일 복사
COPY        ./requirements.txt /tmp
# requirements.txt에 있는 라이브러리 설치
RUN         pip install -r /tmp/requirements.txt

# 현재 프로젝트를 /srv/aitube 폴더에 복사
COPY        . /srv/aitube
# Docker 이미지 실행시 경로
WORKDIR     /srv/aitube

# Docker 컨테이너 생성시 default로 실행하는 명령어
CMD         /bin/bash