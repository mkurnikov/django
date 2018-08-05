import subprocess

from path import Path


if __name__ == '__main__':
    with open('tested_modules.txt', 'r') as tested_modules_file:
        old_tested_modules = set(tested_modules_file.read().split('\n'))

    with open('tested_modules.txt', 'a') as tested_modules_file:
        base_args = ['monkeytype', '--config', 'generate_stubs:CONFIG', 'run', './runtests.py', '--parallel', '1',
                     '--keepdb']
        for node in Path(__file__).parent.listdir():
            if node.isdir():
                node_basename = node.basename()
                if node_basename in old_tested_modules:
                    continue

                print('testing', node_basename)
                command = base_args + [node_basename]
                completed = subprocess.run(command,
                                           stdout=None,
                                           stderr=None,
                                           universal_newlines=True)
                if completed.returncode == 0:
                    tested_modules_file.write(node_basename + '\n')
                    tested_modules_file.flush()

            nodes_to_test = []
