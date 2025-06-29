import os
import yaml


class YamlLoader():
    @staticmethod
    def load_yaml(file_path):

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件不存在：{file_path}")
        with open(file_path,"r",encoding="utf-8") as f:
            return yaml.safe_load(f)


    @staticmethod
    def get_config():
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir,"config","config.yaml")
        config = YamlLoader.load_yaml(config_path)

        return config


    def get_data(self,data_name):
        data = self.get_config().get("test_data",{}).get(data_name,{})
        return data



