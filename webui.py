import gradio as gr
import subprocess
from wav2project import wav2project, random_filename
from shutil import rmtree
from pathlib import Path

root_dir = Path(__file__).parent
result = "./webui_output"
choices = {
    '分离人声': 'vocal_separation',
    '去除和声': 'harmony_removal',
    '去除混响': 'deverb',
    '去除噪声': 'denoise'
}

def process_steps(selected_steps):
    english_steps = [choices[step] for step in selected_steps]
    return english_steps

def pack_files(src, file_name):
    Path("packed").mkdir(parents=True, exist_ok=True)
    command = f"7z a -tzip packed/{file_name}.zip {src}"
    subprocess.run(command, shell=True)
    rmtree(src)

def convert_audio(audio, tempo, enabled_steps, proj):
    Path(result).mkdir(parents=True, exist_ok=True)
    file_name = random_filename()
    steps = process_steps(enabled_steps)
    wav2project(audio, tempo, steps, result, proj)
    pack_files(result, file_name)
    return f"packed/{file_name}.zip"


def webui(share, server_name, server_port):
    with gr.Blocks() as webui:
        with gr.Row():
            with gr.Tab(label='上传音频'):
                upload_audio = gr.Audio(label='上传音频', type='filepath', sources=['upload', 'microphone'], show_label=False)
        with gr.Row():
            with gr.Tab(label='推理设置'):
                with gr.Row():
                    with gr.Column(scale=4):
                        enabled_steps = gr.CheckboxGroup(label='启用步骤(默认全开，可根据实际情况决定开启哪些)', choices=list(choices.keys()), value=list(choices.keys()))
                    with gr.Column(scale=1):
                        proj = gr.Dropdown(label='输出格式', choices=['ustx', 'ust', 'vsqx', 'acep'], value='ustx')
                    with gr.Column(scale=1):
                        tempo = gr.Number(label='曲速', value=120, minimum=1, maximum=99999, step=1)
        with gr.Row():
            with gr.Tab(label='压缩包下载'):
                output = gr.File(label='输出结果', type='filepath')
                run = gr.Button('一键推理！')
        run.click(convert_audio, inputs=[upload_audio, tempo, enabled_steps, proj], outputs=output)
    
    webui.queue(default_concurrency_limit=1)
    webui.launch(inbrowser=True, share=share, server_name=server_name, server_port=server_port)


if __name__ == '__main__':
    import argparse
    import warnings
    warnings.filterwarnings("ignore")

    args = argparse.ArgumentParser(description='wav2ustx')
    args.add_argument('--share', type=bool, default=False, help='是否分享')
    args.add_argument('--server_name', type=str, default='127.0.0.1', help='绑定地址')
    args.add_argument('--server_port', type=int, default=7860, help='端口')
    args = args.parse_args()
    webui(args.share, args.server_name, args.server_port)