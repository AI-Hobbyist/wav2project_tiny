import json
import os
from utils.constant import WEBUI_CONFIG, MSST_MODEL, VR_MODEL
from webui.utils import load_configs, logger

def load_configs(config_path):
    with open(config_path, 'r', encoding="utf-8") as f:
        return json.load(f)

def load_vr_model():
    config = load_configs(WEBUI_CONFIG)
    vr_model_path = config['settings']['uvr_model_dir']
    vr_models = [f for f in os.listdir(vr_model_path) if f.endswith('.pth')]
    return vr_models

def load_msst_model():
    config = load_configs(MSST_MODEL)
    model_list = []
    model_dir = [os.path.join("pretrain", keys) for keys in config.keys()]
    for dirs in model_dir:
        for files in os.listdir(dirs):
            if files.endswith(('.ckpt', '.pth', '.th', '.chpt')):
                model_list.append(files)
    return model_list

def get_msst_model(model_name):
    config = load_configs(MSST_MODEL)
    for keys in config.keys():
        for model in config[keys]:
            if model["name"] == model_name:
                model_path = os.path.join("pretrain", keys, model_name)
                download_link = model["link"]
                return model_path, download_link

def get_uvr_models(model_name):
    config = load_configs(VR_MODEL)
    for key in config.keys():
        if key == model_name:
            model_path = os.path.join("pretrain", "VR_Models", model_name)
            download_link = config[key]["download_link"]
            return model_path, download_link

def download(url, path):
    config = load_configs(WEBUI_CONFIG)
    main_link = config['settings']['download_link']
    try:
        url = url.replace("huggingface.co", main_link)
    except: 
        pass
    try:
        os.system(f"wget {url} -O {path}")
        return 1
    except Exception as e:
        logger.error(f"Download model failed: {e}")
        return 0

def download_model(model_type, model_name):
    msst_config = load_configs(MSST_MODEL)
    msst_models = []
    for keys in msst_config.keys():
        for model in msst_config[keys]:
            msst_models.append(model["name"])
    uvr_config = load_configs(VR_MODEL)
    uvr_models = uvr_config.keys()
    downloaded_msst_models = load_msst_model()
    downloaded_uvr_models = load_vr_model()
    if model_name not in msst_models and model_name not in uvr_models:
        logger.error(f"Model {model_name} not found")
        return 0
    if model_type == "msst":
        if model_name in downloaded_msst_models:
            logger.info(f"Model {model_name} already downloaded")
            return 1
        else:
            model_path, download_link = get_msst_model(model_name)
            if download(download_link, model_path):
                logger.info(f"Model {model_name} downloaded successfully")
                return 1
            else: return 0
    elif model_type == "uvr":
        if model_name in downloaded_uvr_models:
            logger.info(f"Model {model_name} already downloaded")
            return 1
        else:
            model_path, download_link = get_uvr_models(model_name)
            if download(download_link, model_path):
                logger.info(f"Model {model_name} downloaded successfully")
                return 1
            else: return 0