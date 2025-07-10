import random
import string

class Generate:
    @staticmethod
    def generate_username() -> str:
        length = random.randint(4,20)
        chars = string.ascii_letters + string.digits  #包含所有Ascll字母，包含所有数字.
        random.choices(chars,k=length)
        user_name ="".join(random.choices(chars,k=length))
        return user_name

    @staticmethod
    def generate_password() -> str:
        letters = string.ascii_letters
        digits = string.digits
        length = random.randint(8, 20)
        char1 = random.choice(letters)
        char2 = random.choice(digits)
        remaining_length = length - 2
        remaining_chars = letters + digits
        password_list = [char1, char2] + random.choices(remaining_chars, k=remaining_length)
        random.shuffle(password_list)
        return "".join(password_list)

    @staticmethod
    def generate_email() -> str:
        length = random.randint(5,10)
        chars = string.digits
        username = "".join(random.choices(chars,k=length))
        domain = random.choice(["@genomic.cn","@qq.com","@168.com","@ecom.com"])
        return f"{username}{domain}"

    @staticmethod
    def generate_phone() -> str:
        prefixes = [
            '130', '131', '132', '133', '134', '135', '136', '137', '138', '139',
            '145', '147', '149',
            '150', '151', '152', '153', '155', '156', '157', '158', '159',
            '166',
            '170', '171', '172', '173', '175', '176', '177', '178',
            '180', '181', '182', '183', '184', '185', '186', '187', '188', '189',
            '191', '198', '199'
        ]

        chars = string.digits
        suffix = "".join(random.choice(chars) for _ in range(8))
        prefix = random.choice(prefixes)
        return f"{prefix}{suffix}"







