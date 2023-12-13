import socket  # 소켓 통신을 위한 모듈
import argparse  # 명령행 인자 파싱을 위한 모듈
import sys  # 시스템 관련 기능을 위한 모듈
from struct import pack  # 2진수 데이터 처리를 위한 모듈

# TFTP 기본 설정값 정의
DEFAULT_PORT = 69
BLOCK_SIZE = 512
DEFAULT_TRANSFER_MODE = 'octet'

# TFTP 메시지 타입에 대한 OPCODE 및 MODE 정의
OPCODE = {'RRQ': 1, 'WRQ': 2, 'DATA': 3, 'ACK': 4, 'ERROR': 5}
MODE = {'netascii': 1, 'octet': 2, 'mail': 3}

# TFTP 오류 코드 정의
ERROR_CODE = {
    0: "정의되지 않음, 에러 메시지 참조 (있는 경우).",
    1: "파일을 찾을 수 없음.",
    2: "접근 거부.",
    3: "디스크가 가득 찼거나 할당이 초과되었습니다.",
    4: "잘못된 TFTP 작업.",
    5: "알 수 없는 전송 ID.",
    6: "파일이 이미 존재합니다.",
    7: "해당 사용자가 없습니다."
}

# 서버에 WRQ(Write Request) 메시지를 보내는 함수
def send_wrq(filename, mode, server_address):
    format = f'>h{len(filename)}sB{len(mode)}sB'
    wrq_message = pack(format, OPCODE['WRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(wrq_message, server_address)

# 서버에 RRQ(Read Request) 메시지를 보내는 함수
def send_rrq(filename, mode, server_address):
    format = f'>h{len(filename)}sB{len(mode)}sB'
    rrq_message = pack(format, OPCODE['RRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(rrq_message, server_address)

# ACK 메시지를 서버로 보내는 함수
def send_ack(seq_num, server):
    format = f'>hh'
    ack_message = pack(format, OPCODE['ACK'], seq_num)
    sock.sendto(ack_message, server)

# DATA 메시지를 서버로 보내는 함수
def send_data(seq_num, server, data):
    format = f'>hh{len(data)}s'
    data_message = pack(format, OPCODE['DATA'], seq_num, data)
    sock.sendto(data_message, server)

# 서버로부터 파일을 받는 함수
def receive_file():
    file = open(filename, "wb")  # 쓰기모드로 열기
    seq_number = 0  # 시퀀스 넘버 초기값 설정

    while True:
        data, server = sock.recvfrom(516)  # 516바이트씩 데이터 받음
        opcode = int.from_bytes(data[:2], 'big')  # 받은 코드의 처음 2바이트를 읽어 opcode 확인

        if opcode == OPCODE['DATA']:
            seq_number = int.from_bytes(data[2:4], 'big')  # 시퀀스 넘버 확인
            send_ack(seq_number, server)  # 확인 후 ack메세지 전송

            file_block = data[4:]  # 실제 데이터 추출
            file.write(file_block)

            if len(file_block) < BLOCK_SIZE:  # 받은 데이터의 크기가 BLOCK_SIZE보다 작으면 while문 빠져나옴
                file.close()
                break

        elif opcode == OPCODE['ERROR']:
            error_code = int.from_bytes(data[2:4], byteorder='big')  # 받은 패킷이 오류 코드면 오류메세지 출력하고 while문 빠져나옴
            print(ERROR_CODE[error_code])
            break

        else:  # 다른 종류의 패킷이 도착하면 while문 빠져나옴
            break

        # 파일 전송이 완료되었는지 확인하는 부분
        file_block = data[4:]
        print(file_block.decode())
        file.write(file_block)
        if len(file_block) < BLOCK_SIZE:
            print(len(file_block))
            file.close()
            break

# 파일을 서버에 전송하는 함수
def send_file():
    try:
        file_to_send = open(filename, "rb")  # 전송할 파일을 바이너리 읽기 모드로 오픈

        while True:
            data, server = sock.recvfrom(516)
            opcode = int.from_bytes(data[:2], 'big')

            if opcode == OPCODE['ACK']:
                seq_number = int.from_bytes(data[2:4], 'big') + 1
                line = file_to_send.read(512)  # 데이터 서버로 전송

                if not line:
                    send_data(seq_number, server, b'')  # 데이터 전송 후 더 이상 읽을 데이터가 없으면 b''(빈 바이트)데이터를 전송하고 while문 종료
                    break

                send_data(seq_number, server, line)

                if len(line) < BLOCK_SIZE:
                    file_to_send.close()
                    break

    except FileNotFoundError:
        print("File not found.")
        sys.exit(1)


# 명령행 인수 파싱
parser = argparse.ArgumentParser(description='TFTP client program')
parser.add_argument(dest="host", help="서버 IP 주소", type=str)
parser.add_argument(dest="action", help="파일 put 또는 get", type=str)
parser.add_argument(dest="filename", help="전송할 파일 이름", type=str)
parser.add_argument("-p", "--port", dest="port", action="store", type=int)
args = parser.parse_args()

# 서버 주소 및 포트 설정 +사용자로부터 포트번호가 설정되지 않으면 DEFAULT_PORT 번호를 사용
server_ip = args.host
server_port = args.port if args.port is not None else DEFAULT_PORT
server_address = (server_ip, server_port)

# UDP 소켓 생성 및 타임아웃 설정
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(10)  # 소켓 타임아웃 설정

# rrq_message 전송
mode = DEFAULT_TRANSFER_MODE
filename = args.filename
if args.action =='get':
    send_rrq(filename, mode, server_address)
    receive_file()
    print("success")

elif args.action=='put':
    send_wrq(filename, mode, server_address)
    send_file()
    print("success")
    sock.close()
