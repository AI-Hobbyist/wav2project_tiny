import librosa
import yaml
import json
import inference
import importlib
import argparse
import logging
import subprocess
from time import time
from inference.msst_infer import MSSeparator
from utils.logger import get_logger
from modules.rmvpe.inference import RMVPE
from utils.slicer2 import Slicer
from build_svp import build_svp
from pathlib import Path
from tqdm import tqdm
from hashlib import md5
from glob import glob
from shutil import move, rmtree

#==============公用函数==============
#创建随机文件名
def random_filename():
    return md5(str(time()).encode()).hexdigest()

#==============人声分离==============
#分离人声伴奏
def vocal_separation_step1(input, output):
    logger = get_logger(console_level=logging.INFO)
    start_time = time()
    separator = MSSeparator(
        model_type='bs_roformer',
        config_path=f'configs/model_bs_roformer_ep_368_sdr_12.9628.yaml',
        model_path=f'models/msst/model_bs_roformer_ep_368_sdr_12.9628.ckpt',
        device='auto',
        device_ids=[0],
        output_format='wav',
        use_tta=False,
        store_dirs=output,
        logger=logger,
        debug=False
    )
    success_files = separator.process_audio(input)
    separator.del_cache()
    logger.info(f"Successfully separated files: {success_files}, total time: {time() - start_time:.2f} seconds.")
    
#去除和声
def vocal_separation_step2(input, output):
    logger = get_logger(console_level=logging.INFO)
    start_time = time()
    separator = MSSeparator(
        model_type='mel_band_roformer',
        config_path='configs/config_mel_band_roformer_karaoke.yaml',
        model_path='models/msst/model_mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt',
        device='auto',
        device_ids=[0],
        output_format='wav',
        use_tta=False,
        store_dirs=output,
        logger=logger,
        debug=False
    )
    success_files = separator.process_audio(input)
    separator.del_cache()
    logger.info(f"Successfully separated files: {success_files}, total time: {time() - start_time:.2f} seconds.")
    
#去除混响
def vocal_separation_step3(input, output):
    logger = get_logger(console_level=logging.INFO)
    start_time = time()
    separator = MSSeparator(
        model_type='bs_roformer',
        config_path='configs/deverb_bs_roformer_8_256dim_8depth.yaml',
        model_path='models/msst/deverb_bs_roformer_8_256dim_8depth.ckpt',
        device='auto',
        device_ids=[0],
        output_format='wav',
        use_tta=False,
        store_dirs=output,
        logger=logger,
        debug=False
    )
    success_files = separator.process_audio(input)
    separator.del_cache()
    logger.info(f"Successfully separated files: {success_files}, total time: {time() - start_time:.2f} seconds.")
    
#去除噪声
def vocal_separation_step4(input, output):
    logger = get_logger(console_level=logging.INFO)
    start_time = time()
    separator = MSSeparator(
        model_type='mel_band_roformer',
        config_path='configs/model_mel_band_roformer_denoise.yaml',
        model_path='models/msst/denoise_mel_band_roformer_aufr33_aggr_sdr_27.9768.ckpt',
        device='auto',
        device_ids=[0],
        output_format='wav',
        use_tta=False,
        store_dirs=output,
        logger=logger,
        debug=False
    )
    success_files = separator.process_audio(input)
    separator.del_cache()
    logger.info(f"Successfully separated files: {success_files}, total time: {time() - start_time:.2f} seconds.")
    
#==============工程生成==============
#加载配置文件
def load_config(config_path: str) -> dict:
    if config_path.endswith('.json'):
        config = json.loads(Path(config_path).read_text(encoding='utf8'))
    elif config_path.endswith('.yaml'):
        config = yaml.safe_load(Path(config_path).read_text(encoding='utf8'))
    else:
        raise ValueError(f'Unsupported config file format: {config_path}')
    return config
config = load_config('configs/some_config.yaml')
sr = config['audio_sample_rate']

#音频切片
def audio_slicer(audio_path: str) -> list:
    waveform, _ = librosa.load(audio_path, sr=sr, mono=True)
    slicer = Slicer(sr=sr, max_sil_kept=1000)
    chunks = slicer.slice(waveform)
    return chunks

#获取midi
def get_midi(chunks: list, model_path: str) -> list:
    infer_cls = inference.task_inference_mapping[config['task_cls']]
    pkg = ".".join(infer_cls.split(".")[:-1])
    cls_name = infer_cls.split(".")[-1]
    infer_cls = getattr(importlib.import_module(pkg), cls_name)
    assert issubclass(infer_cls, inference.BaseInference), \
        f'Inference class {infer_cls} is not a subclass of {inference.BaseInference}.'
    infer_ins = infer_cls(config=config, model_path=model_path)
    midis = infer_ins.infer([c['waveform'] for c in chunks])
    return midis
    
#获取f0
def get_f0(chunks: list) -> list:
    f0 = []
    rmvpe = RMVPE(model_path='models/rmvpe/rmvpe.pt') # hop_size=160
    print("loading RMVPE model")

    for chunk in tqdm(chunks, desc='Extracting F0'):
        f0_data = {
            "offset": chunk['offset'],
            "f0": rmvpe.infer_from_audio(chunk['waveform'], sample_rate=sr) # sample_rate会重采样至16000
        }
        f0.append(f0_data)
    return f0

#音频转svp
def wav2svp(audio_path, tempo, output):
    Path('results').mkdir(parents=True, exist_ok=True)

    chunks = audio_slicer(audio_path)
    midis = get_midi(chunks, 'models/some/model_steps_64000_simplified.ckpt')
    f0 = get_f0(chunks)

    basename = Path(audio_path).name.split('.')[0]
    template = load_config('template.json')

    print("building svp file")
    svp_path = build_svp(template, midis, f0, tempo, basename, output)

    return svp_path

#==============工程转换==============
#svp转ustx
def svp2ustx(svp_path):
    ustx_path = svp_path.replace('.svp', '.ustx')
    command = f'libresvip-cli proj convert "{svp_path}" "{ustx_path}"'
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    input_values = ['n\n', 'n\n', 'y\n', 'n\n', 'n\n', 'n\n', 'n\n', 'plain\n', 'convert\n', 'split\n', 'n\n', 'n\n', 'n\n', 'n\n', 'n\n','non-arpa\n']
    for value in input_values:
        process.stdin.write(value)
        process.stdin.flush()
        
    process.communicate()
    
    
    
#==============主函数==============
def wav2ustx(audio, tempo, enabled_steps, output):
    #初始化
    try:
        rmtree('results')
    except:
        pass
    Path('results').mkdir(parents=True, exist_ok=True)
    Path(output).mkdir(parents=True, exist_ok=True)
    
    base_name = str(Path(audio).name).replace('.wav', '')
    src = audio
    
    
    #执行步骤
    if 'vocal_separation' in enabled_steps:
        Path('results/step1').mkdir(parents=True, exist_ok=True)
        vocal_separation_step1(src, 'results/step1')
        move(f'results/step1/{base_name}_instrumental.wav', f'{output}/{base_name}_instrumental.wav')
        src = f'results/step1/{base_name}_vocals.wav'
        
    if 'harmony_removal' in enabled_steps:
        Path('results/step2').mkdir(parents=True, exist_ok=True)
        vocal_separation_step2(src, 'results/step2')
        audios = glob(f'results/step2/*.wav')
        for au in audios:
            if '_other.wav' in au:
                Path(au).unlink()
            else:
                src = au
        
    if 'deverb' in enabled_steps:
        Path('results/step3').mkdir(parents=True, exist_ok=True)
        vocal_separation_step3(src, 'results/step3')
        audios = glob(f'results/step3/*.wav')
        for au in audios:
            if '_reverb.wav' in au:
                Path(au).unlink()
            else:
                src = au
        
    if 'denoise' in enabled_steps:
        Path('results/step4').mkdir(parents=True, exist_ok=True)
        vocal_separation_step4(src, 'results/step4')
        audios = glob(f'results/step4/*.wav')
        for au in audios:
            if '_other.wav' in au:
                Path(au).unlink()
            else:
                src = au
    
    move(src, f'{output}/{base_name}.wav')
    svp_path = wav2svp(f'{output}/{base_name}.wav', tempo, output)
    svp2ustx(svp_path)
    rmtree('results')
    
#==============命令行==============
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='wav2ustx')
    parser.add_argument('audio', type=str, help='音频文件')
    parser.add_argument('output', type=str, help='输出文件夹')
    parser.add_argument('-t','--tempo', type=int, help='曲速', default=120)
    parser.add_argument('-s','--enabled_steps', type=str, help='启用的步骤，用逗号分隔，可选值：vocal_separation, harmony_removal, deverb, denoise')
    args = parser.parse_args()
    wav2ustx(args.audio, args.tempo, args.enabled_steps.split(','), args.output)