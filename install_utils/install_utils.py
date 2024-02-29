import yaml


def get_folder_from_yaml(filename, version):
    with open(filename, 'r') as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
        return data["versions"][version]["folder"]


def should_skip_line(line: str) -> bool:
    return line.strip().startswith('#') or line.isspace()
