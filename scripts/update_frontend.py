from brownie import config
import os
import shutil
import yaml
import json


def main():
    update_frontend()


def update_frontend():
    src = "./build"
    dest = config["front_end_path"] + "/chain-info"
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

    with open("brownie-config.yaml", "r") as brownie_config:
        config_dict = yaml.load(brownie_config, Loader=yaml.FullLoader)
        with open(
            config["front_end_path"] + "/brownie-config.json", "w"
        ) as brownie_config_json:
            json.dump(config_dict, brownie_config_json)
