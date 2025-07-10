from common.generate_parameter import Generate


class Parameter:

    @staticmethod
    def register_parameter():
        register_json = {
            "username": "string",
            "password": "4444aaaa",
            "email": "2512265316@qq.com",
            "phone": "13312345678"
        }
        return register_json

    @staticmethod
    def register_parameters():
        register_json = {
            "username": Generate.generate_username(),
            "password": Generate.generate_password(),
            "email": Generate.generate_email(),
            "phone": Generate.generate_phone()
        }
        return register_json

    @staticmethod
    def login_parameter():
        login_json = {
            "username": "string",
            "password": "string",
            "remember_me": False
        }
        return login_json

    @staticmethod
    def login_parameters():
        login_json = {
            "username": Generate.generate_username(),
            "password": Generate.generate_password(),
            "remember_me": False
        }
        return login_json

    @staticmethod
    def update_parameters():
        update_json = {
            "email": Generate.generate_email(),
            "phone": Generate.generate_phone(),
            "avatar": "string",
            "password": Generate.generate_password()
        }
        return update_json

    @staticmethod
    def admin_parameters():
        admin_json = {
            "username": Generate.generate_username(),
            "password": Generate.generate_password(),
            "email": Generate.generate_email(),
            "phone": Generate.generate_phone(),
            "role": "admin"
        }
        return admin_json