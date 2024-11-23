import subprocess

def svp2other(svp, format):
    if format == 'ustx':
        input_values = ['n\n', 'n\n', 'y\n', 'n\n', 'n\n', 'n\n', 'n\n', 'plain\n', 'convert\n', 'split\n', 'n\n', 'n\n', 'n\n', 'n\n', 'n\n','non-arpa\n']
    elif format == 'ust':
        input_values = ['n\n', 'n\n', 'y\n', 'n\n', 'n\n', 'n\n', 'n\n', 'plain\n', 'convert\n', 'split\n', 'n\n', 'n\n', 'n\n', 'n\n', 'n\n','-1\n','1.2\n','utf-8\n']
    elif format == 'vsqx':
        input_values = ['n\n', 'n\n', 'y\n', 'n\n', 'n\n', 'n\n', 'n\n', 'plain\n', 'convert\n', 'split\n', 'n\n', 'n\n', 'n\n', 'n\n', 'n\n','4\n','y\n','4\n','\n','Tianyi_CHN\n']
    elif format == 'acep':
        input_values = ['n\n', 'n\n', 'y\n', 'n\n', 'n\n', 'n\n', 'n\n', 'plain\n', 'convert\n', 'split\n', 'n\n', 'n\n', 'n\n', 'n\n', 'n\n','然糊糊\n','600\n','both\n','1\n','CHN\n','0.0\n']
    else:
        raise ValueError('Invalid format')
        
    new_path = svp.replace('.svp', f'.{format}')
    command = f'libresvip-cli proj convert "{svp}" "{new_path}"'
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for value in input_values:
        process.stdin.write(value)
        process.stdin.flush()
    process.communicate()