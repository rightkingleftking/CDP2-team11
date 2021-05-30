# CDP2-11team
2021ss KNU CDP 11team 
## 인공지능을 이용하여 text 기반 동영상 편집 앱, AiTube 개발
- API서버를 활용한 모바일앱 동영상편집 최적화 프로그램 개발
  - django API server
  - ffmpeg 명령어 최적화 알고리즘
  - docker를 이용해 개발과 배포간의 차이가 없게끔 관리

# 서버
http://221.157.34.231:80/

method = "post"
enctype = "multipart/form-data"

### 원본 비디오 파일
type = "file"
name = "file"

### concat할 비디오 파일 (없으면 보내지 않음)
type = "file"
name = "file2"
(3개 이상의 파일 concat은 5월30일까지 개발예정. n개 이상의 파일의 name은 file{n}으로 처리할 예정)

### 편집히스토리(jsonfile)
type = "file"
name = "jsonfile"


### json 스팩에 명시된 속성값 중 무시되는 값들
- soundList : 음향부분 전부 무시
- captionList["textFrameImageFile"] : 텍스트 배경부분 무시. 5월 30일까지 구현예정
