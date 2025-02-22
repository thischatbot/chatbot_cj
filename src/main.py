# 감정 데이터를 저장할 리스트
emotion_history = []

# 사용자 입력받기
name = input("이름을 입력하세요: ")
emotion = input("현재 감정을 입력하세요: ")

#데이터를 딕셔너리로 저장
user_data = {"name" : name, "emotion": emotion}

# 리스트에 추가
emotion_history.append(user_data)

#저장된 데이터 출력
print(emotion_history)