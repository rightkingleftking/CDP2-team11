import json
import os
import subprocess
import shutil

from django.shortcuts import render
from django.http import FileResponse


CONCAT_MODE = "CONCAT"

# 서브프로세스 실행을 통한 ffmpeg 실행함수
def ffmpeg(commandline):
    result = subprocess.Popen(commandline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = result.communicate()
    exitcode = result.returncode
    if exitcode != 0:
        print(exitcode, out.decode('utf8'), err.decode('utf8'))
    else:
        print('Completed')


def getText(text, start_time=0, duration=0) :
    if start_time or duration : return f"[0:v]drawtext=text={text}:enable='between(t,{start_time / 1000},{start_time / 1000 + duration / 1000})'"
    else : return f"[0:v]drawtext=text={text}"

def getAlign(Value) :
    if Value == "center":
        return ":x=(w/2-tw/2):y=h*0.9"  # w = 화면너비 / tw = 텍스트너비
    elif Value == "right":
        return ":x=(w-tw-10):y=h*0.9"
    else:
        return ":x=10:y=h*0.9"

def getFontColor(Value) :
    return f":fontcolor=0x{Value[3:]}{Value[1:3]}"

def getFontFamily(Value) :
    FONTLIST = {
        "야놀자 야체 Bold.ttf" : "font/yanolzaBold.ttf",
        "야놀자 야체 Regular.ttf" : "font/yanolzaRegular.ttf"
    }
    if Value in FONTLIST :
        return f":fontfile={FONTLIST[Value]}"
        
    else :
        return ""

def test_view(request):
    if request.method == "GET" : return

    # post로 받아온 파일을 서버 디스크에 write
    abspath = os.path.abspath(request.FILES["file"]._get_name())
    path = open(abspath, 'wb')
    shutil.copyfileobj(request.FILES["file"].file, path)
    path.close()

    CONCAT_FILE_NAME = "CONCAT_RESULT.mp4"

    # json parsing test
    jsonData = json.load(request.FILES["jsonfile"].file)

    if "file2" in request.FILES and request.POST['mode'] == CONCAT_MODE :
        temp_path = os.path.abspath(request.FILES["file2"]._get_name())
        path = open(temp_path, 'wb')
        shutil.copyfileobj(request.FILES["file2"].file, path)
        path.close()

        concat(jsonData, CONCAT_FILE_NAME)
        BASE_INPUT_FILE_NAME = CONCAT_FILE_NAME
    else :
        BASE_INPUT_FILE_NAME = abspath
        
    captionList = jsonData["captionList"]

    CAPTION_ATTR_LIST = ["text", "textAlign", "textColor", "textFontFile", "textFrameImageFile", "resultPlayStartPosition", "resultPlayDuration"]

    for index, caption in enumerate(captionList):
        VIDEO_CAPTION = {

        }

        for CAPTION_ATTR in CAPTION_ATTR_LIST : 
            if CAPTION_ATTR in caption :
                VIDEO_CAPTION[CAPTION_ATTR] = caption[CAPTION_ATTR]

        # PROGRESS : GENERATE OPTIONS
        option = ""
        if "text" in VIDEO_CAPTION :
            if "resultPlayStartPosition" in VIDEO_CAPTION and "resultPlayDuration" in VIDEO_CAPTION: option = getText(VIDEO_CAPTION['text'], VIDEO_CAPTION['resultPlayStartPosition'], VIDEO_CAPTION['resultPlayDuration'])
            else : option = getText(VIDEO_CAPTION['text'])
        
        if "textAlign" in VIDEO_CAPTION :
            option += getAlign(VIDEO_CAPTION['textAlign'])

        if "textColor" in VIDEO_CAPTION :
            option += getFontColor(VIDEO_CAPTION['textColor'])
        
        if "textFontFile" in VIDEO_CAPTION :
            option += getFontFamily(VIDEO_CAPTION['textFontFile'])
        

        if len(option) == 0 :
            result_cmd = f"""ffmpeg -y -i {BASE_INPUT_FILE_NAME} """
        else :
            result_cmd = f"""ffmpeg -y -i {BASE_INPUT_FILE_NAME} -filter_complex "{option}" """

        if BASE_INPUT_FILE_NAME == abspath or BASE_INPUT_FILE_NAME == CONCAT_FILE_NAME :
            BASE_INPUT_FILE_NAME = "OUTPUT_FILE.mp4"
            result_cmd += "OUTPUT_FILE.mp4"
        else :
            BASE_INPUT_FILE_NAME = "_" + BASE_INPUT_FILE_NAME
            result_cmd += BASE_INPUT_FILE_NAME
        
        ffmpeg(result_cmd)
        
    
    # 삭제작업 
    if os.path.exists("result.mp4") : os.remove("result.mp4")
    os.rename(BASE_INPUT_FILE_NAME, "result.mp4")
    os.remove("OUTPUT_FILE.mp4")
    if os.path.exists(CONCAT_FILE_NAME) : os.remove(CONCAT_FILE_NAME)

    os.remove(request.FILES["file"]._get_name())
    if "file2" in request.FILES :
        if os.path.exists(request.FILES["file2"]._get_name()) :
             os.remove(request.FILES["file2"]._get_name())

    for i in range(len(BASE_INPUT_FILE_NAME) - 4) :
        if BASE_INPUT_FILE_NAME[i] != '_' : break
        else : 
            try : 
                os.remove(BASE_INPUT_FILE_NAME[i])
            except :
                pass

    output = open('result.mp4', 'rb')
    response = FileResponse(output)
    return response

def upload_view(request) :
    return render(request, f'{os.getcwd()}\\djangoAPIserver\\templates\\index.html'.replace("\\", "/"))

def concat_view(request) :
    return render(request, f'{os.getcwd()}\\djangoAPIserver\\templates\\concat_test.html'.replace("\\", "/"))


def getClipInfo(index, start, duration, output_index) :
    # trim으로 영상의 구간을 잘라서 헤더에 추가
    result = f"[{index}:v]trim={start / 1000}:{(start + duration) / 1000},setpts=N/FRAME_RATE/TB[v{output_index}];" 
    # Audio도 구간을 똑같이 잘라서 헤더에 추가
    result += f"[{index}:a]atrim={start / 1000}:{(start + duration) / 1000},asetpts=N/SR/TB[a{output_index}];" 

    return result


def concat(JSON_FILE, RESULT_FILE) :
    ############# 초기화 ###############
    jsonData = JSON_FILE

    clipList = jsonData["clipList"]
    CLIP_ATTR_LIST = ["videoFile", "videoPlayStartPosition", "videoPlayDuration"]

    VIDEO_CLIPS = []

    for CLIP in clipList :
        VIDEO_CLIP = {

        }
        for CLIP_ATTR in CLIP_ATTR_LIST : 
            if CLIP_ATTR in CLIP :
                VIDEO_CLIP[CLIP_ATTR] = CLIP[CLIP_ATTR]
    
        VIDEO_CLIPS.append(VIDEO_CLIP)
    ##################################


    # videoFile 목록을 갖고온 뒤 중복제거
    FileNames = list(set([_['videoFile']for _ in VIDEO_CLIPS]))

    # "-i 파일명" 문자열 만들기
    HEADER = "".join(f"-i {_} " for _ in FileNames)

    # filter_complex 옵션이 들어갈 변수
    option = ""
    
    # [v0], [a0]등을 위해 output_index 사용
    output_index = 0

    for VIDEO_CLIP in VIDEO_CLIPS :
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
    result_cmd = "ffmpeg "
    result_cmd += HEADER  
    result_cmd += f"""-filter_complex "{option}" """
    result_cmd += FOOTER

    # Execute
    ffmpeg(result_cmd)