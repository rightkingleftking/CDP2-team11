# coding:utf-8
import sys, json, subprocess, os, re, shutil

from django.shortcuts import render
from django.http import FileResponse


class Queue:
    ll = []

    def __init__(self):
        self.ll = []

    def push(self, data):
        self.ll.append(data)

    def pop(self):
        returnValue = self.ll[0]
        self.ll = self.ll[1:]
        return returnValue


# 서브프로세스 실행을 통한 ffmpeg 실행함수
def ffmpeg(commandline):
    result = subprocess.Popen(commandline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = result.communicate()
    exitcode = result.returncode
    if exitcode != 0:
        print(exitcode, out.decode('utf8'), err.decode('utf8'))
    else:
        print('Completed')


def getText(headers, text, start_time=0, duration=0):
    inputValue = headers.pop()

    result = f"[{inputValue}] drawtext=text={text}"
    if start_time or duration:
        result += f":enable='between(t,{start_time / 1000},{start_time / 1000 + duration / 1000})'"

    return result


def getAlign(Value):
    if Value == "center":
        return ":x=(w/2-tw/2):y=h*0.9"  # w = 화면너비 / tw = 텍스트너비
    elif Value == "right":
        return ":x=(w-tw-10):y=h*0.9"
    else:
        return ":x=10:y=h*0.9"


def getFontColor(Value):
    return f":fontcolor=0x{Value[3:]}{Value[1:3]}"


def getFontFamily(Value):
    FONTLIST = {
        "야놀자 야체 Bold.ttf": "font/yanolzaBold.ttf",
        "야놀자 야체 Regular.ttf": "font/yanolzaRegular.ttf",
        "BASE_FONT": "/Windows/fonts/malgun.ttf"
    }
    if Value in FONTLIST:
        return f":fontfile={FONTLIST[Value]}"

    else:
        return f":fontfile={FONTLIST['BASE_FONT']}"


def getCaption(headers, VIDEO_CAPTION):
    if "text" in VIDEO_CAPTION:
        if "resultPlayStartPosition" in VIDEO_CAPTION and "resultPlayDuration" in VIDEO_CAPTION:
            option = getText(headers, VIDEO_CAPTION['text'], VIDEO_CAPTION['resultPlayStartPosition'],
                             VIDEO_CAPTION['resultPlayDuration'])
        else:
            option = getText(headers, VIDEO_CAPTION['text'])

    if "textAlign" in VIDEO_CAPTION:
        option += getAlign(VIDEO_CAPTION['textAlign'])

    if "textColor" in VIDEO_CAPTION:
        option += getFontColor(VIDEO_CAPTION['textColor'])

    if "textFontFile" in VIDEO_CAPTION:
        option += getFontFamily(VIDEO_CAPTION['textFontFile'])

    retVal = headers.pop()

    return f"{option} [{retVal}]", retVal


def save_the_file(FILE, OUTPUT_FILENAME):
    abspath = "".join(os.path.abspath(FILE._get_name()).split("/")[:-1])
    abspath += OUTPUT_FILENAME

    with open(abspath, 'wb') as path:
        shutil.copyfileobj(FILE.file, path)

    return abspath


def test_view(request):
    if request.method == "GET": return

    jsonData = json.load(request.FILES["jsonfile"].file)
    # post로 받아온 파일을 서버 디스크에 write
    FILE_PATH = save_the_file(request.FILES['file'], jsonData["clipList"][0]["videoFile"])
    BASE_INPUT_FILE_NAME = FILE_PATH

    if "file2" in request.FILES:
        CONCAT_FILE_NAME = "CONCAT_RESULT.mp4"
        save_the_file(request.FILES['file2'], jsonData["clipList"][1]["videoFile"])
        concat(jsonData, CONCAT_FILE_NAME)
        BASE_INPUT_FILE_NAME = CONCAT_FILE_NAME

    captionList = jsonData["captionList"]

    CAPTION_ATTR_LIST = ["text", "textAlign", "textColor", "textFontFile", "textFrameImageFile",
                         "resultPlayStartPosition", "resultPlayDuration"]

    VIDEO_CAPTIONS = []

    # JSON Parsing
    for CAPTION in captionList:
        VIDEO_CAPTION = {

        }

        for CAPTION_ATTR in CAPTION_ATTR_LIST:
            if CAPTION_ATTR in CAPTION:
                VIDEO_CAPTION[CAPTION_ATTR] = CAPTION[CAPTION_ATTR]

        VIDEO_CAPTIONS.append(VIDEO_CAPTION)

    options = ""

    index_count = 1
    headers = Queue()
    # 큐에 input Video, Output Video 삽입
    headers.push("0:v")
    headers.push(f"v{index_count}")

    # Make values for filter_complex
    for VIDEO_CAPTION in VIDEO_CAPTIONS:
        option, retVal = getCaption(headers, VIDEO_CAPTION)
        options += option + ";"

        # 큐 값 조정
        index_count += 1
        headers.push(retVal)
        headers.push(f"v{index_count}")

    # CASE : OPTION NOT FOUND
    if len(options) == 0:
        result_cmd = f"""ffmpeg -y -i {BASE_INPUT_FILE_NAME} """
    else:
        # CASE : Detect OPTION
        options = options[:-1]
        options = f'{options[:options.rfind("[")]} [out]'  # 최종적으로 [out]이라는 변수에 영상부분 저장
        result_cmd = f"""ffmpeg -y -i {BASE_INPUT_FILE_NAME} -filter_complex "{options}" """

        # SET FOOTER
        result_cmd += ' -map "[out]" -map "0:a" '  # 영상은 [out] 속의 값으로, 소리는 0번 비디오 파일의 소리로 지정

    if BASE_INPUT_FILE_NAME == FILE_PATH or BASE_INPUT_FILE_NAME == CONCAT_FILE_NAME:
        BASE_INPUT_FILE_NAME = "OUTPUT_FILE.mp4"

    result_cmd += BASE_INPUT_FILE_NAME  # 출력파일 최종 지정

    # Execute
    ffmpeg(result_cmd)

    output = open(BASE_INPUT_FILE_NAME, 'rb')
    response = FileResponse(output)
    return response


def upload_view(request):
    return render(request, f'{os.getcwd()}\\djangoAPIserver\\templates\\index.html'.replace("\\", "/"))


def concat_view(request):
    return render(request, f'{os.getcwd()}\\djangoAPIserver\\templates\\concat_test.html'.replace("\\", "/"))


def getClipInfo(index, start, duration, output_index):
    # trim으로 영상의 구간을 잘라서 헤더에 추가
    result = f"[{index}:v]trim={start / 1000}:{(start + duration) / 1000},setpts=N/FRAME_RATE/TB[v{output_index}];"
    # Audio도 구간을 똑같이 잘라서 헤더에 추가
    result += f"[{index}:a]atrim={start / 1000}:{(start + duration) / 1000},asetpts=N/SR/TB[a{output_index}];"

    return result


def concat(JSON_FILE, RESULT_FILE):
    ############# 초기화 ###############
    jsonData = JSON_FILE

    clipList = jsonData["clipList"]
    CLIP_ATTR_LIST = ["videoFile", "videoPlayStartPosition", "videoPlayDuration"]

    VIDEO_CLIPS = []

    for CLIP in clipList:
        VIDEO_CLIP = {

        }
        for CLIP_ATTR in CLIP_ATTR_LIST:
            if CLIP_ATTR in CLIP:
                VIDEO_CLIP[CLIP_ATTR] = CLIP[CLIP_ATTR]

        VIDEO_CLIPS.append(VIDEO_CLIP)
    ##################################

    # videoFile 목록을 갖고온 뒤 중복제거
    FileNames = list(set([_['videoFile'] for _ in VIDEO_CLIPS]))

    # "-i 파일명" 문자열 만들기
    HEADER = "".join(f"-i {_} " for _ in FileNames)

    # filter_complex 옵션이 들어갈 변수
    option = ""

    # [v0], [a0]등을 위해 output_index 사용
    output_index = 0

    for VIDEO_CLIP in VIDEO_CLIPS:
        option += getClipInfo(
            FileNames.index(VIDEO_CLIP['videoFile']),
            VIDEO_CLIP['videoPlayStartPosition'],
            VIDEO_CLIP['videoPlayDuration'],
            output_index
        )

        output_index += 1

    # [v0]등 옵션의 개수를 셈, 다만 [a0] 등은 세면 안되기 때문에 2로 나눔.
    LENGTH_OPTION_ELEMENT = int(len(option.split(";")[:-1]) / 2)

    # [v0], [a0] 등을 파싱해오는 함수, 아래와 같이 문자열을 만들기 위해 사용
    # example : [v0][a0][v1][a1]concat
    option += "".join([_[_.rfind("["):] for _ in option.split(";")[:-1]])

    # a=1을 0으로 주면 무음 모드가 가능함.
    option += f"concat=n={LENGTH_OPTION_ELEMENT}:v=1:a=1 [out][a]"

    # 결과 파일 드롭
    FOOTER = f"""-map "[out]" -map "[a]" {RESULT_FILE}"""

    # Command Merge
    result_cmd = "ffmpeg -y "
    result_cmd += HEADER
    result_cmd += f"""-filter_complex "{option}" """
    result_cmd += FOOTER

    # Execute
    ffmpeg(result_cmd)