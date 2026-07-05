# протокол общения клиент - хост

class P2PProtocol:
    # 1 - хост; 2 - клиент
    CMD_HELLO = "HELLO" #2 запрос на конект  (код комнаты, имя)
    CMD_WELCOME = "WELCOME" #1 ответ на запрос конекта
    CMD_SEND_M = "MESSAGE" #2 отправить сообщение
    CMD_DIST_M = "DISTRIBUTION" #1 пересылка сообщений хостом остальным клиентам
    CMD_PAR_JOIN = "PARTICIPANT_JOIN" #1 уведомляет всех что участник присоединился
    
    @staticmethod
    def encode(cmd, *args):
        message = cmd
        for arg in args:
            message += '|' + str(arg)
        message += '\n'
        return message.encode('utf-8')
    
    @staticmethod
    def decode(data):
        line = data.decode('utf-8').strip()
        parts = line.split('|')
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        return cmd, args