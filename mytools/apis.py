


def read_gpt_keys(key_file):
    keys = open(key_file).readlines()
    outputs = []
    for k in keys:
        k = k.strip()
        if len(k):
            outputs.append(k)
    return outputs

